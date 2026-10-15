import asyncio
import json
import os
import re
import sys
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

load_dotenv()

BASE_DIR      = Path(__file__).parent.parent
DEFINITIONS   = BASE_DIR / "emojis.json"
UPLOADED      = BASE_DIR / "emojis.uploaded.json"

BOT_TOKEN  = os.getenv("DISCORD_TOKEN", "")
CLIENT_ID  = os.getenv("CLIENT_ID", "")
API_BASE   = "https://discord.com/api/v10"
FORCE      = "--force" in sys.argv

_EMOJI_RE = re.compile(r"^<(a)?:([A-Za-z0-9_]+):(\d+)>$")


def parse_emoji(literal: str) -> dict | None:
    m = _EMOJI_RE.match(literal)
    if not m:
        return None
    return {"animated": bool(m.group(1)), "name": m.group(2), "id": m.group(3)}


def load_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[Upload] Cannot read {path.name}: {e}")
        return {}


def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


async def fetch_existing(session: aiohttp.ClientSession) -> dict[str, dict]:
    url = f"{API_BASE}/applications/{CLIENT_ID}/emojis"
    async with session.get(url) as r:
        if r.status != 200:
            text = await r.text()
            print(f"[Upload] Failed to fetch existing emojis ({r.status}): {text}")
            return {}
        data = await r.json()
        items = data.get("items", [])
        return {item["name"]: item for item in items}


async def download_as_data_uri(session: aiohttp.ClientSession, emoji_id: str, animated: bool) -> str | None:
    ext = "gif" if animated else "png"
    url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
    async with session.get(url) as r:
        if r.status != 200:
            print(f"[Upload] CDN download failed for {emoji_id}: HTTP {r.status}")
            return None
        raw    = await r.read()
        mime   = "image/gif" if animated else "image/png"
        import base64
        b64    = base64.b64encode(raw).decode()
        return f"data:{mime};base64,{b64}"


async def upload_emoji(session: aiohttp.ClientSession, name: str, data_uri: str) -> dict | None:
    url  = f"{API_BASE}/applications/{CLIENT_ID}/emojis"
    body = {"name": name, "image": data_uri}
    headers = {"Content-Type": "application/json"}
    async with session.post(url, json=body, headers=headers) as r:
        if r.status not in (200, 201):
            text = await r.text()
            print(f"[Upload] Upload failed for '{name}' ({r.status}): {text}")
            return None
        return await r.json()


async def run():
    print("═" * 55)
    print("  XEON — Application Emoji Uploader")
    print("═" * 55)

    if not BOT_TOKEN:
        print("[Upload] ERROR: DISCORD_TOKEN not set in .env")
        sys.exit(1)
    if not CLIENT_ID:
        print("[Upload] ERROR: CLIENT_ID not set in .env")
        sys.exit(1)

    definitions = load_json(DEFINITIONS)
    uploaded    = load_json(UPLOADED)

    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "User-Agent":    "XEONBot/1.0 (upload script)",
    }

    async with aiohttp.ClientSession(headers=headers) as session:

        existing = await fetch_existing(session)
        print(f"[Upload] Found {len(existing)} existing application emoji(s).")

        seen_source: dict[str, dict] = {}
        uploaded_count = skipped = failed = reused = 0

        for key, literal in definitions.items():
            if key.startswith("_"):
                continue

            parsed = parse_emoji(literal) if isinstance(literal, str) else None
            if not parsed:
                skipped += 1
                continue

            if not FORCE and uploaded.get(key, {}).get("id"):
                skipped += 1
                continue

            if parsed["id"] in seen_source:
                uploaded[key] = seen_source[parsed["id"]]
                reused += 1
                continue

            if parsed["name"] in existing:
                ex = existing[parsed["name"]]
                result = {
                    "name":     ex["name"],
                    "id":       ex["id"],
                    "animated": bool(ex.get("animated", False)),
                }
                uploaded[key]              = result
                seen_source[parsed["id"]]  = result
                reused += 1
                continue

            print(f"[Upload] Uploading {key} ({parsed['name']})…")
            data_uri = await download_as_data_uri(session, parsed["id"], parsed["animated"])
            if not data_uri:
                failed += 1
                continue

            created = await upload_emoji(session, parsed["name"], data_uri)
            if not created:
                failed += 1
                continue

            result = {
                "name":     created["name"],
                "id":       created["id"],
                "animated": bool(created.get("animated", False)),
            }
            uploaded[key]              = result
            seen_source[parsed["id"]]  = result
            existing[created["name"]]  = created
            uploaded_count += 1

            await asyncio.sleep(0.75)

    save_json(UPLOADED, uploaded)

    print("─" * 55)
    print(f"  Uploaded : {uploaded_count}")
    print(f"  Reused   : {reused}")
    print(f"  Skipped  : {skipped}")
    print(f"  Failed   : {failed}")
    print(f"  Saved    → {UPLOADED.relative_to(BASE_DIR)}")

    if failed:
        print("\n  ⚠  Some emojis failed. Bot will use original IDs as fallback.")
    else:
        print("\n  ✅  All emojis uploaded! Restart the bot to use new IDs.")
    print("═" * 55)


if __name__ == "__main__":
    asyncio.run(run())
