import discord
from utils.config import OWNER_IDS
from discord.ext import commands, tasks
from discord import ui
import aiosqlite
import time
import aiohttp
import asyncio
from pathlib import Path


from XEON.emojis import E as _EMGR, FALLBACK_EMOJI
import re as _re

_LOCAL_KEY_MAP = {
    "success": "SUCCESS",
    "error": "ERROR",
    "info": "INFO",
    "premium": "PREMIUM",
    "crown": "CROWN",
    "star": "STAR",
    "dot": "DOT",
    "timer": "CLOCK",
    "clock": "CLOCK",
    "avatar": "AVATAR",
    "name": "NAME",
    "banner": "BANNER",
    "reset": "REMOVE",
    "settings": "SETTINGS",
    "server": "SERVER",
    "user": "USER",
    "slot": "SLOT",
    "shield": "SHIELD",
    "support": "SUPPORT",
    "tag": "TICKET",
    "activate": "ACTIVATE",
}

def E(key: str) -> discord.PartialEmoji:
    s = _EMGR[_LOCAL_KEY_MAP.get(key, key.upper())]
    m = _re.match(r'<(a)?:([A-Za-z0-9_]+):(\d+)>', s)
    if m:
        return discord.PartialEmoji(name=m.group(2), id=int(m.group(3)), animated=bool(m.group(1)))
    return FALLBACK_EMOJI

def ES(key: str) -> str:
    return _EMGR[_LOCAL_KEY_MAP.get(key, key.upper())]


ACCENT_COLOR = discord.Colour(0x000000)
BOT_NAME     = "XEON"

DB_DIR  = Path("db")
DB_PATH = DB_DIR / "premium.db"

DURATIONS = [
    ("10 Minutes", "Trial for 10 minutes",  600),
    ("1 Week",     "Premium for 1 week",    604800),
    ("3 Weeks",    "Premium for 3 weeks",   1814400),
    ("1 Month",    "Premium for 1 Month",   2592000),
    ("3 Months",   "Premium for 3 Months",  7776000),
    ("6 Months",   "Premium for 6 Months",  15552000),
    ("1 Year",     "Premium for 1 Year",    31536000),
    ("3 Years",    "Premium for 3 Years",   94608000),
    ("Lifetime",   "Premium Permanently",   0),
]


def _ensure_db():
    DB_DIR.mkdir(exist_ok=True)


def _format_expiry(expire: int) -> str:
    if expire == 0:
        return "**Lifetime** (never expires)"
    return f"<t:{expire}:F>\n(<t:{expire}:R>)"


def _format_duration(seconds: int) -> str:
    if seconds == 0:
        return "Lifetime"
    for label, _, secs in DURATIONS:
        if secs == seconds:
            return label
    if seconds < 3600:
        return f"{seconds // 60} minutes"
    if seconds < 86400:
        return f"{seconds // 3600} hours"
    if seconds < 604800:
        return f"{seconds // 86400} days"
    if seconds < 2592000:
        return f"{seconds // 604800} weeks"
    return f"{seconds // 2592000} months"


def _error_view(text: str) -> ui.LayoutView:
    v = ui.LayoutView()
    c = ui.Container(accent_color=ACCENT_COLOR)
    c.add_item(ui.TextDisplay(f"{ES('error')} {text}"))
    v.add_item(c)
    return v


def _success_view(text: str) -> ui.LayoutView:
    v = ui.LayoutView()
    c = ui.Container(accent_color=ACCENT_COLOR)
    c.add_item(ui.TextDisplay(f"{ES('success')} {text}"))
    v.add_item(c)
    return v


def _info_view(text: str) -> ui.LayoutView:
    v = ui.LayoutView()
    c = ui.Container(accent_color=ACCENT_COLOR)
    c.add_item(ui.TextDisplay(f"{ES('info')} {text}"))
    v.add_item(c)
    return v


def _premium_features_block() -> str:
    return (
        f"{ES('support')} **24/7 Support**\n"
        f"{ES('shield')} **Higher Protection & Security**\n"
        f"{ES('settings')} **Bot Profile Customization** — `custombot`\n"
        f"{ES('tag')} **Bot Nameplate Customization** — `tag`"
    )


def _build_guild_activated_view(guild_name: str, guild_id: int, expire: int) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=ACCENT_COLOR)

    c.add_item(ui.TextDisplay(f"## {ES('star')} Guild Premium Activated"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('server')} **Server:** `{guild_name}`\n"
        f"{ES('dot')} **Server ID:** `{guild_id}`\n"
        f"{ES('timer')} **Expires:** {_format_expiry(expire)}"
    ))

    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(f"{ES('crown')} **Premium Features Unlocked**"))
    c.add_item(ui.TextDisplay(_premium_features_block()))

    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# Powered by {BOT_NAME} Development"))

    view.add_item(c)
    return view


def _build_user_slot_added_view(user: discord.User, seconds: int) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=ACCENT_COLOR)

    c.add_item(ui.TextDisplay(f"## {ES('star')} User Premium Slot Added"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('user')} **User:** {user.mention}\n"
        f"{ES('user')} **User ID:** `{user.id}`\n"
        f"{ES('timer')} **Slot Duration:** `{_format_duration(seconds)}`\n\n"
        f"The user now has **1 new premium slot** they can activate in any server "
        f"using `activate`."
    ))

    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(f"{ES('info')} **How to use:**"))
    c.add_item(ui.TextDisplay(
        f"{ES('dot')} User runs `activate` in any server\n"
        f"{ES('dot')} That server gets premium for the slot duration\n"
        f"{ES('dot')} User can activate their remaining slots in other servers"
    ))

    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# Powered by {BOT_NAME} Development"))

    view.add_item(c)
    return view


def _build_user_activated_view(guild: discord.Guild, seconds: int, expire: int, remaining: int) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=ACCENT_COLOR)

    c.add_item(ui.TextDisplay(f"## {ES('activate')} Premium Activated in This Server"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('server')} **Server:** `{guild.name}`\n"
        f"{ES('timer')} **Duration:** `{_format_duration(seconds)}`\n"
        f"{ES('clock')} **Expires:** {_format_expiry(expire)}\n"
        f"{ES('slot')} **Slots Remaining:** `{remaining}`"
    ))

    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(f"{ES('crown')} **Premium Features Unlocked**"))
    c.add_item(ui.TextDisplay(_premium_features_block()))

    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# Powered by {BOT_NAME} Development"))

    view.add_item(c)
    return view


def _build_status_view(
    guild: discord.Guild,
    user: discord.User | discord.Member,
    guild_expire: int | None,
    cfg: dict | None,
    user_slots: list[tuple[int, int]],
) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=ACCENT_COLOR)

    c.add_item(ui.TextDisplay(f"## {ES('premium')} Premium Status"))
    c.add_item(ui.Separator())

    c.add_item(ui.TextDisplay(f"{ES('server')} **Server Status**"))

    if guild_expire is None:
        c.add_item(ui.TextDisplay(
            f"{ES('error')} `{guild.name}` does **not** have premium."
        ))
    else:
        c.add_item(ui.TextDisplay(
            f"{ES('success')} **Active**\n"
            f"{ES('dot')} **Server:** `{guild.name}`\n"
            f"{ES('timer')} **Expires:** {_format_expiry(guild_expire)}"
        ))

    c.add_item(ui.Separator())

    c.add_item(ui.TextDisplay(f"{ES('user')} **Your Premium Slots**"))

    if not user_slots:
        c.add_item(ui.TextDisplay(
            f"{ES('error')} You have no premium slots.\n"
            f"Contact the bot owner to receive premium."
        ))
    else:
        slots_text = ""
        for i, (dur, added) in enumerate(user_slots, start=1):
            slots_text += (
                f"{ES('slot')} **Slot {i}** — `{_format_duration(dur)}`  "
                f"(added <t:{added}:R>)\n"
            )
        c.add_item(ui.TextDisplay(
            slots_text +
            f"\n{ES('info')} Use `activate` in any server to consume a slot."
        ))

    if guild_expire is not None and cfg and any(cfg.get(k) for k in ("name", "avatar", "banner")):
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(f"{ES('settings')} **CustomBot Config**"))
        c.add_item(ui.TextDisplay(
            f"{ES('name')}   **Nickname:** `{cfg.get('name') or '*(not set)*'}`\n"
            f"{ES('avatar')} **Avatar:** `{(cfg.get('avatar') or '*(not set)*')[:60]}`\n"
            f"{ES('banner')} **Banner:** `{(cfg.get('banner') or '*(not set)*')[:60]}`"
        ))

    view.add_item(c)
    return view


def _build_custombot_view(cog, guild_id: int, cfg: dict | None) -> ui.LayoutView:
    view = CustomBotView(cog, guild_id)
    c = ui.Container(accent_color=ACCENT_COLOR)

    c.add_item(ui.TextDisplay(f"## {ES('settings')} CustomBot Settings"))
    c.add_item(ui.Separator())

    c.add_item(ui.TextDisplay(
        f"Customize your **{BOT_NAME} Prime** appearance for this server.\n"
        f"All changes are server-specific."
    ))
    c.add_item(ui.Separator())

    if cfg:
        cur_name   = cfg.get("name")   or "*(not set)*"
        cur_avatar = cfg.get("avatar") or "*(not set)*"
        cur_banner = cfg.get("banner") or "*(not set)*"
    else:
        cur_name = cur_avatar = cur_banner = "*(not set)*"

    c.add_item(ui.TextDisplay(
        f"{ES('name')}   **Nickname:** `{cur_name[:60]}`\n"
        f"{ES('avatar')} **Avatar:** `{cur_avatar[:60]}`\n"
        f"{ES('banner')} **Banner:** `{cur_banner[:60]}`"
    ))

    c.add_item(ui.Separator())

    row1 = ui.ActionRow()
    row1.add_item(view.btn_avatar)
    row1.add_item(view.btn_name)
    row1.add_item(view.btn_banner)
    c.add_item(row1)

    row2 = ui.ActionRow()
    row2.add_item(view.btn_reset)
    row2.add_item(view.btn_close)
    c.add_item(row2)

    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(
        f"-# Tip: Use direct image links (PNG / JPG / GIF). "
        f"Server needs Boost Level 2 for banners."
    ))

    view.add_item(c)
    return view


class GuildDurationView(ui.LayoutView):
    def __init__(self, cog, target_guild_id: int, target_name: str, author_id: int):
        super().__init__(timeout=120)
        self.cog             = cog
        self.target_guild_id = target_guild_id
        self.target_name     = target_name
        self.author_id       = author_id
        self._build()

    def _build(self):
        c = ui.Container(accent_color=ACCENT_COLOR)
        c.add_item(ui.TextDisplay(f"## {ES('crown')} Select Premium Duration"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"{ES('server')} **Server:** `{self.target_name}`\n"
            f"{ES('dot')} **Server ID:** `{self.target_guild_id}`\n\n"
            f"Choose how long premium should be active."
        ))
        c.add_item(ui.Separator(visible=False))

        options = [
            discord.SelectOption(label=label, description=desc, value=str(secs))
            for label, desc, secs in DURATIONS
        ]

        select = ui.Select(
            placeholder="Select duration...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"prem_gdur_{self.target_guild_id}",
        )
        select.callback = self._on_select
        c.add_item(ui.ActionRow(select))

        cancel_btn = ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="prem_cancel",
        )
        cancel_btn.callback = self._on_cancel
        c.add_item(ui.ActionRow(cancel_btn))

        self.add_item(c)

    async def _check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                view=_error_view("Only the command user can use this!"),
                ephemeral=True,
            )
            return False
        return True

    async def _on_select(self, interaction: discord.Interaction):
        if not await self._check(interaction):
            return
        try:
            secs = int(interaction.data["values"][0])
        except Exception:
            return await interaction.response.edit_message(view=_error_view("Invalid selection."))

        now = int(time.time())
        expire = 0 if secs == 0 else now + secs

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR REPLACE INTO premium (guild_id, expire_at) VALUES (?, ?)",
                (self.target_guild_id, expire),
            )
            await db.commit()

        target_guild = self.cog.bot.get_guild(self.target_guild_id)
        gname = target_guild.name if target_guild else f"ID: {self.target_guild_id}"

        await interaction.response.edit_message(
            view=_build_guild_activated_view(gname, self.target_guild_id, expire)
        )

    async def _on_cancel(self, interaction: discord.Interaction):
        if not await self._check(interaction):
            return
        await interaction.response.edit_message(view=_info_view("Cancelled."))


class UserDurationView(ui.LayoutView):
    def __init__(
        self,
        cog,
        target_user: discord.User,
        slot_count: int,
        author_id: int,
    ):
        super().__init__(timeout=120)
        self.cog         = cog
        self.target_user = target_user
        self.slot_count  = slot_count
        self.author_id   = author_id
        self._build()

    def _build(self):
        c = ui.Container(accent_color=ACCENT_COLOR)
        c.add_item(ui.TextDisplay(f"## {ES('crown')} Grant User Premium Slots"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"{ES('user')} **User:** {self.target_user.mention}\n"
            f"{ES('user')} **User ID:** `{self.target_user.id}`\n"
            f"{ES('slot')} **Slots to add:** `{self.slot_count}`\n\n"
            f"Choose duration for **each slot**.\n"
            f"User can activate each slot in a different server."
        ))
        c.add_item(ui.Separator(visible=False))

        options = [
            discord.SelectOption(label=label, description=desc, value=str(secs))
            for label, desc, secs in DURATIONS
        ]

        select = ui.Select(
            placeholder="Select duration per slot...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"prem_udur_{self.target_user.id}",
        )
        select.callback = self._on_select
        c.add_item(ui.ActionRow(select))

        cancel_btn = ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="prem_cancel_user",
        )
        cancel_btn.callback = self._on_cancel
        c.add_item(ui.ActionRow(cancel_btn))

        self.add_item(c)

    async def _check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                view=_error_view("Only the command user can use this!"),
                ephemeral=True,
            )
            return False
        return True

    async def _on_select(self, interaction: discord.Interaction):
        if not await self._check(interaction):
            return
        try:
            secs = int(interaction.data["values"][0])
        except Exception:
            return await interaction.response.edit_message(view=_error_view("Invalid selection."))

        now = int(time.time())

        async with aiosqlite.connect(str(DB_PATH)) as db:
            for _ in range(self.slot_count):
                await db.execute(
                    "INSERT INTO user_slots (user_id, duration_seconds, added_at) VALUES (?, ?, ?)",
                    (self.target_user.id, secs, now),
                )
            await db.commit()

        await interaction.response.edit_message(
            view=_build_user_slot_added_view(self.target_user, secs)
        )

    async def _on_cancel(self, interaction: discord.Interaction):
        if not await self._check(interaction):
            return
        await interaction.response.edit_message(view=_info_view("Cancelled."))


class CustomBotView(ui.LayoutView):
    def __init__(self, cog, guild_id: int):
        super().__init__(timeout=300)
        self.cog      = cog
        self.guild_id = guild_id

        self.btn_avatar = ui.Button(label="Change Avatar", style=discord.ButtonStyle.primary, custom_id="cb_avatar")
        self.btn_name   = ui.Button(label="Change Name",   style=discord.ButtonStyle.primary, custom_id="cb_name")
        self.btn_banner = ui.Button(label="Change Banner", style=discord.ButtonStyle.primary, custom_id="cb_banner")
        self.btn_reset  = ui.Button(label="Reset All",     style=discord.ButtonStyle.danger,  custom_id="cb_reset")
        self.btn_close  = ui.Button(label="Close",         style=discord.ButtonStyle.secondary, custom_id="cb_close")

        self.btn_avatar.callback = self._on_avatar
        self.btn_name.callback   = self._on_name
        self.btn_banner.callback = self._on_banner
        self.btn_reset.callback  = self._on_reset
        self.btn_close.callback  = self._on_close

    async def _check_perms(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                view=_error_view("You need **Administrator** permission!"),
                ephemeral=True,
            )
            return False
        return True

    async def _wait_input(self, interaction: discord.Interaction, timeout: float = 60.0) -> str | None:
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        try:
            msg = await self.cog.bot.wait_for("message", check=check, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        try:
            await msg.delete()
        except Exception:
            pass
        return msg.content.strip()

    async def _download(self, url: str) -> bytes | None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception:
            pass
        return None

    async def _refresh(self, interaction: discord.Interaction):
        cfg = await self.cog.get_config(self.guild_id)
        new_view = _build_custombot_view(self.cog, self.guild_id, cfg)
        try:
            await interaction.message.edit(view=new_view)
        except Exception:
            pass

    async def _on_avatar(self, interaction: discord.Interaction):
        if not await self._check_perms(interaction):
            return

        await interaction.response.send_message(
            view=_info_view("**Send the avatar image URL** in this channel.\n*Timeout: 60s*"),
            ephemeral=True,
        )

        url = await self._wait_input(interaction)
        if not url:
            return await interaction.edit_original_response(view=_error_view("Timed out!"))
        if not url.startswith(("http://", "https://")):
            return await interaction.edit_original_response(
                view=_error_view("URL must start with `http://` or `https://`")
            )

        data = await self._download(url)
        if not data:
            return await interaction.edit_original_response(
                view=_error_view("Failed to download image from that URL.")
            )

        try:
            await interaction.guild.me.edit(avatar=data)
        except Exception as e:
            return await interaction.edit_original_response(
                view=_error_view(f"Couldn't update avatar: `{e}`")
            )

        await self.cog.set_config(self.guild_id, avatar=url)
        await interaction.edit_original_response(view=_success_view("**Avatar updated!**"))
        await self._refresh(interaction)

    async def _on_name(self, interaction: discord.Interaction):
        if not await self._check_perms(interaction):
            return

        await interaction.response.send_message(
            view=_info_view("**Send the new nickname** in this channel.\n*Timeout: 60s*"),
            ephemeral=True,
        )

        name = await self._wait_input(interaction)
        if not name:
            return await interaction.edit_original_response(view=_error_view("Timed out!"))
        if len(name) > 32:
            return await interaction.edit_original_response(
                view=_error_view("Nickname must be 32 characters or fewer.")
            )

        try:
            await interaction.guild.me.edit(nick=name)
        except Exception as e:
            return await interaction.edit_original_response(
                view=_error_view(f"Couldn't update nickname: `{e}`")
            )

        await self.cog.set_config(self.guild_id, name=name)
        await interaction.edit_original_response(view=_success_view(f"**Nickname set to:** `{name}`"))
        await self._refresh(interaction)

    async def _on_banner(self, interaction: discord.Interaction):
        if not await self._check_perms(interaction):
            return

        if interaction.guild.premium_tier < 2:
            return await interaction.response.send_message(
                view=_error_view("Server needs **Boost Level 2** to set a banner."),
                ephemeral=True,
            )

        await interaction.response.send_message(
            view=_info_view("**Send the banner image URL** in this channel.\n*Timeout: 60s*"),
            ephemeral=True,
        )

        url = await self._wait_input(interaction)
        if not url:
            return await interaction.edit_original_response(view=_error_view("Timed out!"))
        if not url.startswith(("http://", "https://")):
            return await interaction.edit_original_response(
                view=_error_view("URL must start with `http://` or `https://`")
            )

        data = await self._download(url)
        if not data:
            return await interaction.edit_original_response(
                view=_error_view("Failed to download image from that URL.")
            )

        try:
            await interaction.guild.me.edit(banner=data)
        except Exception as e:
            return await interaction.edit_original_response(
                view=_error_view(f"Couldn't update banner: `{e}`")
            )

        await self.cog.set_config(self.guild_id, banner=url)
        await interaction.edit_original_response(view=_success_view("**Banner updated!**"))
        await self._refresh(interaction)

    async def _on_reset(self, interaction: discord.Interaction):
        if not await self._check_perms(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        try:
            await interaction.guild.me.edit(nick=None, avatar=None, banner=None)
        except Exception:
            pass

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("DELETE FROM config WHERE guild_id = ?", (self.guild_id,))
            await db.commit()

        await interaction.followup.send(
            view=_success_view("**Reset successful!** All customizations cleared."),
            ephemeral=True,
        )
        await self._refresh(interaction)

    async def _on_close(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            await interaction.message.delete()
            self.stop()
        except Exception:
            pass


class Premium(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        _ensure_db()
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS premium (
                    guild_id  INTEGER PRIMARY KEY,
                    expire_at INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    guild_id INTEGER PRIMARY KEY,
                    name     TEXT,
                    avatar   TEXT,
                    banner   TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_slots (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id           INTEGER NOT NULL,
                    duration_seconds  INTEGER NOT NULL,
                    added_at          INTEGER NOT NULL
                )
            """)
            await db.commit()

        self.bot.loop.create_task(self.apply_all_configs())
        if not self.check_expiry.is_running():
            self.check_expiry.start()

    def cog_unload(self):
        if self.check_expiry.is_running():
            self.check_expiry.cancel()


    async def is_premium(self, guild_id: int) -> bool:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT expire_at FROM premium WHERE guild_id = ?", (guild_id,)
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return False
        return row[0] == 0 or row[0] > int(time.time())

    async def get_expire(self, guild_id: int) -> int | None:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT expire_at FROM premium WHERE guild_id = ?", (guild_id,)
            ) as cur:
                row = await cur.fetchone()
        return row[0] if row else None


    async def get_config(self, guild_id: int) -> dict | None:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM config WHERE guild_id = ?", (guild_id,)
            ) as cur:
                row = await cur.fetchone()
        return dict(row) if row else None

    async def set_config(self, guild_id: int, **fields):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR IGNORE INTO config (guild_id) VALUES (?)", (guild_id,)
            )
            for col, val in fields.items():
                await db.execute(
                    f"UPDATE config SET {col} = ? WHERE guild_id = ?", (val, guild_id)
                )
            await db.commit()


    async def get_user_slots(self, user_id: int) -> list[tuple[int, int]]:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT duration_seconds, added_at FROM user_slots WHERE user_id = ? ORDER BY added_at ASC",
                (user_id,)
            ) as cur:
                return await cur.fetchall()

    async def consume_user_slot(self, user_id: int) -> tuple[int, int] | None:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT id, duration_seconds, added_at FROM user_slots WHERE user_id = ? ORDER BY added_at ASC LIMIT 1",
                (user_id,)
            ) as cur:
                row = await cur.fetchone()
            if not row:
                return None
            slot_id, duration, added = row
            await db.execute("DELETE FROM user_slots WHERE id = ?", (slot_id,))
            await db.commit()
        return (duration, added)

    async def count_user_slots(self, user_id: int) -> int:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM user_slots WHERE user_id = ?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
        return row[0] if row else 0

    async def remove_all_user_slots(self, user_id: int) -> int:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM user_slots WHERE user_id = ?", (user_id,)
            ) as cur:
                count = (await cur.fetchone())[0]
            await db.execute("DELETE FROM user_slots WHERE user_id = ?", (user_id,))
            await db.commit()
        return count


    async def apply_all_configs(self):
        await self.bot.wait_until_ready()
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT guild_id, name, avatar, banner FROM config") as cur:
                rows = await cur.fetchall()

        async with aiohttp.ClientSession() as session:
            for guild_id, name, avatar, banner in rows:
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue
                try:
                    if name:
                        await guild.me.edit(nick=name)
                    if avatar:
                        try:
                            async with session.get(avatar) as resp:
                                if resp.status == 200:
                                    await guild.me.edit(avatar=await resp.read())
                        except Exception:
                            pass
                    if banner and guild.premium_tier >= 2:
                        try:
                            async with session.get(banner) as resp:
                                if resp.status == 200:
                                    await guild.me.edit(banner=await resp.read())
                        except Exception:
                            pass
                except Exception:
                    pass


    @tasks.loop(minutes=10)
    async def check_expiry(self):
        await self.bot.wait_until_ready()
        now = int(time.time())
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT guild_id, expire_at FROM premium") as cur:
                rows = await cur.fetchall()

        for guild_id, expire in rows:
            if expire == 0:
                continue
            if expire > now:
                continue

            async with aiosqlite.connect(str(DB_PATH)) as db:
                await db.execute("DELETE FROM premium WHERE guild_id = ?", (guild_id,))
                await db.execute("DELETE FROM config WHERE guild_id = ?", (guild_id,))
                await db.commit()

            guild = self.bot.get_guild(guild_id)
            if guild:
                try:
                    await guild.me.edit(nick=None, avatar=None, banner=None)
                except Exception:
                    pass


    @commands.command(name="addprem", aliases=["addpremium"])
    async def addprem(self, ctx: commands.Context, target: str = None, count: int = 1):
        if ctx.author.id not in OWNER_IDS:
            return await ctx.send(view=_error_view("You are not authorized to use this command."))

        if not target:
            return await ctx.send(view=_error_view(
                "Usage:\n"
                "`addprem <guild_id>` — grant premium to a guild\n"
                "`addprem @user [count]` — grant N premium slots to a user"
            ))

        user_id = None
        if ctx.message.mentions:
            user_id = ctx.message.mentions[0].id
        else:
            try:
                parsed_id = int(target.replace("<@", "").replace("!", "").replace(">", ""))
                if self.bot.get_guild(parsed_id):
                    target_guild = self.bot.get_guild(parsed_id)
                    target_name  = target_guild.name if target_guild else f"Unknown ({parsed_id})"
                    view = GuildDurationView(self, parsed_id, target_name, ctx.author.id)
                    return await ctx.send(view=view)
                else:
                    try:
                        user = await self.bot.fetch_user(parsed_id)
                        user_id = user.id
                    except Exception:
                        view = GuildDurationView(self, parsed_id, f"ID: {parsed_id}", ctx.author.id)
                        return await ctx.send(view=view)
            except ValueError:
                return await ctx.send(view=_error_view("Invalid target. Use a guild ID or @user mention."))

        if user_id:
            if count < 1 or count > 100:
                return await ctx.send(view=_error_view("Slot count must be between **1 and 100**."))
            try:
                target_user = await self.bot.fetch_user(user_id)
            except Exception:
                return await ctx.send(view=_error_view("User not found."))

            view = UserDurationView(self, target_user, count, ctx.author.id)
            return await ctx.send(view=view)


    @commands.command(name="removeprem", aliases=["removepremium"])
    async def removeprem(self, ctx: commands.Context, target: str = None):
        if ctx.author.id not in OWNER_IDS:
            return await ctx.send(view=_error_view("You are not authorized to use this command."))

        if not target:
            target_id = ctx.guild.id if ctx.guild else None
            if not target_id:
                return await ctx.send(view=_error_view("Provide a guild ID or user mention."))
            return await self._remove_guild_prem(ctx, target_id)

        if ctx.message.mentions:
            user = ctx.message.mentions[0]
            count = await self.remove_all_user_slots(user.id)
            if count == 0:
                return await ctx.send(view=_error_view(
                    f"{user.mention} has no premium slots to remove."
                ))
            return await ctx.send(view=_success_view(
                f"Removed **{count}** premium slot(s) from {user.mention}."
            ))

        try:
            parsed_id = int(target.replace("<@", "").replace("!", "").replace(">", ""))
        except ValueError:
            return await ctx.send(view=_error_view("Invalid target."))

        if self.bot.get_guild(parsed_id) or True:
            async with aiosqlite.connect(str(DB_PATH)) as db:
                async with db.execute(
                    "SELECT expire_at FROM premium WHERE guild_id = ?", (parsed_id,)
                ) as cur:
                    row = await cur.fetchone()

            if row:
                return await self._remove_guild_prem(ctx, parsed_id)

        count = await self.remove_all_user_slots(parsed_id)
        if count == 0:
            return await ctx.send(view=_error_view(
                f"No premium found for `{parsed_id}` (guild or user)."
            ))
        return await ctx.send(view=_success_view(
            f"Removed **{count}** premium slot(s) from user `{parsed_id}`."
        ))

    async def _remove_guild_prem(self, ctx: commands.Context, target_id: int):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT expire_at FROM premium WHERE guild_id = ?", (target_id,)
            ) as cur:
                row = await cur.fetchone()

            if not row:
                return await ctx.send(view=_error_view(
                    f"Server `{target_id}` does not have premium."
                ))

            await db.execute("DELETE FROM premium WHERE guild_id = ?", (target_id,))
            await db.execute("DELETE FROM config WHERE guild_id = ?", (target_id,))
            await db.commit()

        guild = self.bot.get_guild(target_id)
        gname = guild.name if guild else f"ID: {target_id}"

        if guild:
            try:
                await guild.me.edit(nick=None, avatar=None, banner=None)
            except Exception:
                pass

        await ctx.send(view=_success_view(
            f"**Premium removed** from `{gname}` (`{target_id}`)."
        ))


    @commands.command(name="activate", aliases=["activateprem", "activatepremium"])
    @commands.guild_only()
    async def activate(self, ctx: commands.Context):
        if await self.is_premium(ctx.guild.id):
            expire = await self.get_expire(ctx.guild.id)
            return await ctx.send(view=_info_view(
                f"**{ctx.guild.name}** already has active premium.\n"
                f"{ES('timer')} Expires: {_format_expiry(expire)}"
            ))

        slot_count = await self.count_user_slots(ctx.author.id)
        if slot_count == 0:
            return await ctx.send(view=_error_view(
                "You have **no premium slots** to activate.\n"
                "Contact the bot owner to receive premium."
            ))

        consumed = await self.consume_user_slot(ctx.author.id)
        if not consumed:
            return await ctx.send(view=_error_view("Could not consume slot. Try again."))

        duration_secs, _added = consumed
        now = int(time.time())
        expire = 0 if duration_secs == 0 else now + duration_secs

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR REPLACE INTO premium (guild_id, expire_at) VALUES (?, ?)",
                (ctx.guild.id, expire),
            )
            await db.commit()

        remaining = await self.count_user_slots(ctx.author.id)

        await ctx.send(view=_build_user_activated_view(
            ctx.guild, duration_secs, expire, remaining
        ))


    @commands.command(name="premium", aliases=["premstatus", "premstat"])
    @commands.guild_only()
    async def premium_status(self, ctx: commands.Context):
        expire = await self.get_expire(ctx.guild.id)
        cfg = await self.get_config(ctx.guild.id)

        if expire is not None and not (expire == 0 or expire > int(time.time())):
            expire = None

        slots = await self.get_user_slots(ctx.author.id)

        await ctx.send(view=_build_status_view(
            ctx.guild, ctx.author, expire, cfg, slots
        ))


    @commands.command(name="custombot", aliases=["cb"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def custombot(self, ctx: commands.Context):
        if not await self.is_premium(ctx.guild.id):
            return await ctx.send(view=_error_view(
                f"This server is **not premium**.\n"
                f"Contact the bot owner or use your own premium slot via `activate`."
            ))

        cfg = await self.get_config(ctx.guild.id)
        view = _build_custombot_view(self, ctx.guild.id, cfg)
        await ctx.send(view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Premium(bot))
