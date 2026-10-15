from __future__ import annotations

import json
import os
import re
from typing import Optional

import discord

_BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFINITIONS   = os.path.join(_BASE_DIR, "emojis.json")
_UPLOADED      = os.path.join(_BASE_DIR, "emojis.uploaded.json")

_EMOJI_RE = re.compile(r"^<(a)?:([A-Za-z0-9_]+):(\d+)>$")


def _parse(literal: str) -> Optional[dict]:
    m = _EMOJI_RE.match(literal)
    if not m:
        return None
    return {"animated": bool(m.group(1)), "name": m.group(2), "id": m.group(3)}


def _format(name: str, eid: str, animated: bool) -> str:
    return f"<{'a' if animated else ''}:{name}:{eid}>"


def _load_json(path: str) -> dict:
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[XEON/emojis] Failed to load {os.path.basename(path)}: {exc}")
        return {}


class _EmojiMap:

    def __init__(self):
        self._map: dict[str, str] = {}
        self._load()


    def _load(self):
        definitions = _load_json(_DEFINITIONS)
        uploaded    = _load_json(_UPLOADED)

        source_id_to_upload: dict[str, dict] = {}
        for key, fallback_literal in definitions.items():
            if key.startswith("_") or not isinstance(fallback_literal, str):
                continue
            parsed = _parse(fallback_literal)
            if not parsed:
                continue
            up = uploaded.get(key)
            if up and isinstance(up, dict) and up.get("id") and up.get("name"):
                source_id_to_upload.setdefault(parsed["id"], up)

        result: dict[str, str] = {}

        for key, fallback_literal in definitions.items():
            if key.startswith("_"):
                continue

            up = uploaded.get(key)
            if up and isinstance(up, dict) and up.get("id") and up.get("name"):
                result[key] = _format(up["name"], str(up["id"]), bool(up.get("animated")))
                continue

            parsed = _parse(fallback_literal) if isinstance(fallback_literal, str) else None
            if parsed:
                sibling_up = source_id_to_upload.get(parsed["id"])
                if sibling_up:
                    result[key] = _format(
                        sibling_up["name"], str(sibling_up["id"]), bool(sibling_up.get("animated"))
                    )
                    continue

            if parsed:
                result[key] = _format(parsed["name"], parsed["id"], parsed["animated"])
            elif isinstance(fallback_literal, str):
                result[key] = fallback_literal
            else:
                result[key] = "❔"

        for key, up in uploaded.items():
            if key not in result and isinstance(up, dict) and up.get("id") and up.get("name"):
                result[key] = _format(up["name"], str(up["id"]), bool(up.get("animated")))

        self._map = result


    def reload(self):
        self._load()
        return self

    def get(self, key: str, default: str = "❔") -> str:
        return self._map.get(key, default)

    def keys(self):
        return self._map.keys()

    def items(self):
        return self._map.items()

    def __getattr__(self, key: str) -> str:
        try:
            return self._map[key]
        except KeyError:
            return "❔"

    def __getitem__(self, key: str) -> str:
        return self._map.get(key, "❔")

    def __contains__(self, key: str) -> bool:
        return key in self._map

    def __repr__(self) -> str:
        return f"<EmojiMap keys={len(self._map)}>"


E = _EmojiMap()


FALLBACK_EMOJI = discord.PartialEmoji(name="▫️")


def partial(key: str) -> discord.PartialEmoji:
    m = _EMOJI_RE.match(E[key])
    if m:
        return discord.PartialEmoji(name=m.group(2), id=int(m.group(3)), animated=bool(m.group(1)))
    return FALLBACK_EMOJI
