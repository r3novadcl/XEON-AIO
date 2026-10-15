import asyncio
import json
import os
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

load_dotenv()

BASE_DIR   = Path(__file__).parent.parent
UPLOADED   = BASE_DIR / "emojis.uploaded.json"
BOT_TOKEN  = os.getenv("DISCORD_TOKEN", "")
CLIENT_ID  = os.getenv("CLIENT_ID", "")
API_BASE   = "https://discord.com/api/v10"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


async def main():
    print("═" * 60)
    print("  XEON — Emoji Cache Verifier")
    print("═" * 60)

    if not BOT_TOKEN or not CLIENT_ID:
        print("❌ Missing DISCORD_TOKEN or CLIENT_ID in .env — cannot check.")
        return

    cached = load_json(UPLOADED)
    if not cached:
        print("⚠️  emojis.uploaded.json is empty or missing — nothing to verify.")
        return

    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "User-Agent": "XEONBot/1.0 (verify script)",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        url = f"{API_BASE}/applications/{CLIENT_ID}/emojis"
        async with session.get(url) as r:
            if r.status != 200:
                text = await r.text()
                print(f"❌ Failed to fetch Application emoji list (HTTP {r.status}):")
                print(f"   {text}")
                print()
                print("   This usually means:")
                print("   - CLIENT_ID in .env doesn't match this bot token's application, OR")
                print("   - The bot token is invalid/expired")
                return
            data = await r.json()
            live_items = data.get("items", [])

    live_ids = {str(item["id"]): item for item in live_items}
    print(f"Discord currently has {len(live_items)} real Application emoji(s).\n")

    real_count = 0
    ghost_count = 0
    ghosts = []

    for key, entry in cached.items():
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        eid = str(entry["id"])
        if eid in live_ids:
            real_count += 1
        else:
            ghost_count += 1
            ghosts.append((key, entry.get("name"), eid))

    print(f"✅ Real (confirmed on Discord) : {real_count}")
    print(f"❌ Ghost (NOT on Discord)      : {ghost_count}")

    if ghosts:
        print("\n─── GHOST ENTRIES (these will show as plain text, not emoji) ───")
        for key, name, eid in ghosts[:30]:
            print(f"   {key:20} name={name:20} id={eid}")
        if len(ghosts) > 30:
            print(f"   ... and {len(ghosts) - 30} more")

    print("\n" + "═" * 60)
    if ghost_count == len(cached):
        print("  🚨 EVERY cached entry is a ghost.")
        print("  → emojis.uploaded.json does NOT reflect a real upload.")
        print("  → Delete it and re-run:")
        print("      python scripts/upload_application_emojis.py --force")
    elif ghost_count > 0:
        print("  ⚠️  Some entries are ghosts (probably deleted from Discord).")
        print("  → Re-run with --force to re-upload just the missing ones:")
        print("      python scripts/upload_application_emojis.py --force")
    else:
        print("  ✅ Cache is fully valid — every ID is real on Discord.")
        print("  If emojis still don't render, the problem is elsewhere")
        print("  (e.g. bot missing 'Use External Emojis' permission).")
    print("═" * 60)


if __name__ == "__main__":
    asyncio.run(main())
