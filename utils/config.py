import os

from dotenv import load_dotenv

load_dotenv()


def _ids(raw: str) -> frozenset[int]:
    return frozenset(int(x) for x in raw.replace(";", ",").split(",") if x.strip().isdigit())


def _int(raw: str) -> int:
    return int(raw) if raw.strip().isdigit() else 0


BOT_NAME = "XEON"
DEFAULT_PREFIX = os.getenv("BOT_PREFIX", "&")

OWNER_IDS = _ids(os.getenv("OWNER_IDS", ""))
CLIENT_ID = os.getenv("CLIENT_ID", "").strip()

SUPPORT_SERVER = os.getenv("SUPPORT_SERVER", "https://discord.gg/epKhYP6Y74")
WEBSITE = os.getenv("WEBSITE") or SUPPORT_SERVER
STATUS_PAGE = os.getenv("STATUS_PAGE") or SUPPORT_SERVER

INVITE_URL = os.getenv("INVITE_URL") or (
    f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}"
    "&permissions=8&integration_type=0&scope=bot+applications.commands"
    if CLIENT_ID
    else SUPPORT_SERVER
)

NOPREFIX_LOG_CHANNEL_ID = _int(os.getenv("NOPREFIX_LOG_CHANNEL_ID", ""))
NOPREFIX_CLAIM_CHANNEL_ID = _int(os.getenv("NOPREFIX_CLAIM_CHANNEL_ID", ""))

WEBHOOK_COMMANDS = os.getenv("WEBHOOK_COMMANDS", "")
WEBHOOK_GUILD_JOIN = os.getenv("WEBHOOK_GUILD_JOIN", "")
WEBHOOK_GUILD_LEAVE = os.getenv("WEBHOOK_GUILD_LEAVE", "")
WEBHOOK_ERRORS = os.getenv("WEBHOOK_ERRORS", "")
WEBHOOK_READY = os.getenv("WEBHOOK_READY", "")
