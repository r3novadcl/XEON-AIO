import discord
from discord.ext import commands
from utils.config import OWNER_IDS, SUPPORT_SERVER as SUPPORT_SERVER_URL
from discord.ui import (
    LayoutView, Container, Section, TextDisplay, Separator,
    Thumbnail, ActionRow, Button, Select
)
import aiosqlite
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


ACCENT_COLOR = 0x000000

DB_PATH = "db/anti.db"

SECURITY_ROLE_NAME = "Unbypassable Security [X+]"

MIN_MEMBER_COUNT = 2

from XEON.emojis import E as _EMGR

_KEY_MAP = {
    "CHECK": "SUCCESS", "CROSS": "ERROR", "ENABLED": "ENABLED",
    "DISABLED": "DISABLED", "GEARS": "LOADING", "INFO": "INFO",
    "SHIELD": "SECURITY", "ARROW": "ARROW", "WARN": "WARNING",
    "LOCK": "LOCK", "RECOVERY": "LOADING", "LOG": "ARROW",
    "WHITELIST": "ARROW", "TIMER": "ARROW", "LOADING": "LOADING",
    "USER": "USER", "BOT": "ARROW", "ROLE": "ROLE",
}

def E(key: str) -> str:
    return _EMGR[_KEY_MAP.get(key, key)]

FILTER_META = {
    "ban":        "Ban",
    "kick":       "Kick",
    "prune":      "Prune",
    "memup":      "Member Update",
    "rlcr":       "Role Create",
    "rldl":       "Role Delete",
    "rlup":       "Role Update",
    "chcr":       "Channel Create",
    "chdl":       "Channel Delete",
    "chup":       "Channel Update",
    "webhookcr":  "Webhook Create",
    "webhookdl":  "Webhook Delete",
    "webhookup":  "Webhook Update",
    "botadd":     "Bot Add",
    "serverup":   "Guild Update",
    "meneve":     "Mention Spam",
}

FILTERS_ROW1 = ["ban", "kick", "prune", "memup", "rlcr", "rldl", "rlup", "chcr"]
FILTERS_ROW2 = ["chdl", "chup", "webhookcr", "webhookdl", "webhookup", "botadd", "serverup", "meneve"]

PUNISHMENTS = ["ban", "kick", "stripstaff"]
DEFAULT_PUNISHMENT = "ban"


def _toggle_emoji(state: bool) -> str:
    return E("ENABLED") if state else E("DISABLED")


def _build_filter_text(enabled_map: dict) -> str:
    def line(key):
        return f"{E('ARROW')} **{FILTER_META[key]} :** {_toggle_emoji(enabled_map.get(key, False))}"
    block1 = "\n".join(line(k) for k in FILTERS_ROW1)
    block2 = "\n".join(line(k) for k in FILTERS_ROW2)
    return f"**Filters [1]:**\n{block1}\n\n**Filters [2]:**\n{block2}"


def _build_wl_text(target_mention: str, target_name: str, state_map: dict, count: int, target_type: str) -> str:
    def line(k):
        return f"{E('ARROW')} **{FILTER_META[k]} :** {_toggle_emoji(state_map.get(k, False))}"
    r1 = "\n".join(line(k) for k in FILTERS_ROW1)
    r2 = "\n".join(line(k) for k in FILTERS_ROW2)

    if target_type == "role":
        intro = (
            f"*Manage **{target_mention}'s** role whitelist for the **Antinuke Filter** "
            f"to make all role members immune*"
        )
    elif target_type == "bot":
        intro = (
            f"*Manage **{target_mention}'s** bot whitelist for the **Antinuke Filter** "
            f"to make this bot immune*"
        )
    else:
        intro = (
            f"*Manage **{target_mention}'s** whitelist for the **Antinuke Filter** "
            f"to make them immune*"
        )

    return (
        f"{intro}\n\n"
        f"**Whitelisted Filters [1] :**\n{r1}\n\n"
        f"**Whitelisted Filters [2] :**\n{r2}"
    )


class DBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.db = None
        return cls._instance

    async def connect(self):
        if self.db is None:
            Path("db").mkdir(exist_ok=True)
            self.db = await aiosqlite.connect(DB_PATH)
            await self._setup_tables()
        return self.db

    async def _setup_tables(self):
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS antinuke (
                guild_id INTEGER PRIMARY KEY,
                status   BOOLEAN DEFAULT FALSE
            )
        """)

        filter_cols = " ".join(f"{k} BOOLEAN DEFAULT FALSE," for k in FILTER_META)
        await self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS antinuke_filters (
                guild_id INTEGER PRIMARY KEY,
                {filter_cols.rstrip(',')}
            )
        """)

        punish_cols = " ".join(f"{k} TEXT DEFAULT '{DEFAULT_PUNISHMENT}'," for k in FILTER_META)
        await self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS antinuke_punishments (
                guild_id INTEGER PRIMARY KEY,
                {punish_cols.rstrip(',')}
            )
        """)

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS extraowners (
                guild_id INTEGER,
                owner_id INTEGER,
                PRIMARY KEY (guild_id, owner_id)
            )
        """)

        wl_cols = " ".join(f"{k} BOOLEAN DEFAULT FALSE," for k in FILTER_META)
        await self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS antinuke_whitelist (
                guild_id    INTEGER,
                user_id     INTEGER,
                target_type TEXT DEFAULT 'user',
                {wl_cols}
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        async with self.db.execute(
            "PRAGMA table_info(antinuke_whitelist)"
        ) as cur:
            existing_cols = [row[1] for row in await cur.fetchall()]

        if "target_type" not in existing_cols:
            try:
                await self.db.execute(
                    "ALTER TABLE antinuke_whitelist "
                    "ADD COLUMN target_type TEXT DEFAULT 'user'"
                )
                print("[AntiNuke DB] Migrated: added 'target_type' column.")
            except Exception as e:
                print(f"[AntiNuke DB] Migration error: {e}")

        role_wl_cols = " ".join(f"{k} BOOLEAN DEFAULT FALSE," for k in FILTER_META)
        await self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS antinuke_role_whitelist (
                guild_id INTEGER,
                role_id  INTEGER,
                {role_wl_cols}
                PRIMARY KEY (guild_id, role_id)
            )
        """)

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS antinuke_logs (
                guild_id   INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """)

        await self.db.commit()


async def is_authorized(db, guild: discord.Guild, user_id: int) -> bool:
    if user_id in OWNER_IDS:
        return True
    if user_id == guild.owner_id:
        return True
    async with db.execute(
        "SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?",
        (guild.id, user_id)
    ) as cur:
        return bool(await cur.fetchone())


async def is_whitelisted(
    db,
    guild_id: int,
    user_id: int,
    filter_key: str,
    role_ids: list = None
) -> bool:
    async with db.execute(
        f"SELECT {filter_key} FROM antinuke_whitelist "
        f"WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    ) as cur:
        row = await cur.fetchone()
    if row and row[0]:
        return True

    if role_ids:
        for role_id in role_ids:
            async with db.execute(
                f"SELECT {filter_key} FROM antinuke_role_whitelist "
                f"WHERE guild_id = ? AND role_id = ?",
                (guild_id, role_id)
            ) as cur:
                row = await cur.fetchone()
            if row and row[0]:
                return True

    return False


async def is_filter_enabled(db, guild_id: int, filter_key: str) -> bool:
    async with db.execute(
        "SELECT status FROM antinuke WHERE guild_id = ?", (guild_id,)
    ) as cur:
        row = await cur.fetchone()
    if not row or not row[0]:
        return False
    async with db.execute(
        f"SELECT {filter_key} FROM antinuke_filters WHERE guild_id = ?", (guild_id,)
    ) as cur:
        row = await cur.fetchone()
    return bool(row and row[0])


async def get_punishment(db, guild_id: int, filter_key: str) -> str:
    async with db.execute(
        f"SELECT {filter_key} FROM antinuke_punishments WHERE guild_id = ?", (guild_id,)
    ) as cur:
        row = await cur.fetchone()
    return (row[0] if row and row[0] else DEFAULT_PUNISHMENT)


async def get_log_channel(db, guild: discord.Guild):
    async with db.execute(
        "SELECT channel_id FROM antinuke_logs WHERE guild_id = ?", (guild.id,)
    ) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    return guild.get_channel(row[0])


def build_container(
    bot: commands.Bot,
    title: str,
    body: str,
    footer: str = None,
    thumbnail_url: str = None
) -> Container:
    thumb_url = thumbnail_url or bot.user.display_avatar.url
    section = Section(
        TextDisplay(f"# {title}\n{body}"),
        accessory=Thumbnail(
            media=discord.UnfurledMediaItem(url=thumb_url),
            description="Antinuke Panel"
        )
    )
    components = [section, Separator()]
    if footer:
        components.append(TextDisplay(f"-# {footer}"))
    return Container(*components, accent_color=ACCENT_COLOR)


def build_simple_container(text: str, footer: str = None) -> Container:
    components = [TextDisplay(text)]
    if footer:
        components.append(Separator())
        components.append(TextDisplay(f"-# {footer}"))
    return Container(*components, accent_color=ACCENT_COLOR)


class FilterEnableSelect(Select):
    def __init__(self, db, guild_id: int, enabled_map: dict):
        self.db = db
        self.guild_id = guild_id
        self.enabled_map = dict(enabled_map)

        options = [
            discord.SelectOption(
                label=FILTER_META[k],
                description=f"Toggle the {FILTER_META[k].lower()} filter.",
                value=k,
                default=enabled_map.get(k, False)
            )
            for k in FILTER_META
        ]
        super().__init__(
            placeholder="Select filters to enable…",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id="enable_filters_select"
        )

    async def callback(self, interaction: discord.Interaction):
        selected = set(self.values)
        for key in FILTER_META:
            self.enabled_map[key] = key in selected

        cols = list(FILTER_META.keys())
        placeholders = ", ".join(["?"] * (len(cols) + 1))
        await self.db.execute(
            f"INSERT OR REPLACE INTO antinuke_filters (guild_id, {', '.join(cols)}) "
            f"VALUES ({placeholders})",
            [self.guild_id] + [self.enabled_map[k] for k in cols]
        )
        await self.db.commit()

        view: "FilterEnableLayoutView" = self.view
        view.refresh(self.enabled_map)
        await interaction.response.edit_message(view=view)


class FilterEnableLayoutView(LayoutView):
    def __init__(self, bot, db, guild_id: int, enabled_map: dict, author_id: int):
        super().__init__(timeout=120)
        self.bot = bot
        self.db = db
        self.guild_id = guild_id
        self.author_id = author_id
        self.enabled_map = dict(enabled_map)
        self._build()

    def _build(self):
        self.clear_items()

        section = Section(
            TextDisplay(
                f"# {E('SHIELD')}  Enable Antinuke Filters\n"
                f"*Select the filters you want active. Changes save automatically.*\n\n"
                + _build_filter_text(self.enabled_map)
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Filter Panel"
            )
        )

        select = FilterEnableSelect(self.db, self.guild_id, self.enabled_map)

        save_btn = Button(
            label="Save & Done",
            style=discord.ButtonStyle.success,
            custom_id="filter_save_done"
        )
        save_btn.callback = self._save_done

        container = Container(
            section,
            Separator(),
            ActionRow(select),
            ActionRow(save_btn),
            Separator(),
            TextDisplay("-# Antinuke Filter Configuration"),
            accent_color=ACCENT_COLOR
        )
        self.add_item(container)

    def refresh(self, new_map):
        self.enabled_map = dict(new_map)
        self._build()

    async def _save_done(self, interaction: discord.Interaction):
        self.stop()
        done_container = build_simple_container(
            f"{E('CHECK')} **Antinuke filters saved successfully!**",
            footer="Settings have been updated"
        )
        new_view = LayoutView(timeout=None)
        new_view.add_item(done_container)
        await interaction.response.edit_message(view=new_view)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id and interaction.user.id not in OWNER_IDS:
            denied = build_simple_container(
                f"{E('CROSS')} You cannot interact with this panel."
            )
            v = LayoutView(timeout=None)
            v.add_item(denied)
            await interaction.response.send_message(view=v, ephemeral=True)
            return False
        return True


class WhitelistFilterSelect(Select):
    def __init__(
        self,
        db,
        guild_id: int,
        target_id: int,
        state_map: dict,
        mode: str = "user_bot"
    ):
        self.db = db
        self.guild_id = guild_id
        self.target_id = target_id
        self.state_map = dict(state_map)
        self.mode = mode

        options = [
            discord.SelectOption(
                label=FILTER_META[k],
                description=f"Toggle {FILTER_META[k].lower()} whitelist.",
                value=k,
                default=state_map.get(k, False)
            )
            for k in FILTER_META
        ]
        super().__init__(
            placeholder="Select filters to whitelist…",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id="wl_filter_select"
        )

    async def callback(self, interaction: discord.Interaction):
        selected = set(self.values)
        for k in FILTER_META:
            self.state_map[k] = k in selected

        if self.mode == "role":
            cols = ", ".join(f"{k} = ?" for k in FILTER_META)
            vals = [self.state_map[k] for k in FILTER_META]
            await self.db.execute(
                f"UPDATE antinuke_role_whitelist SET {cols} "
                f"WHERE guild_id = ? AND role_id = ?",
                vals + [self.guild_id, self.target_id]
            )
        else:
            cols = ", ".join(f"{k} = ?" for k in FILTER_META)
            vals = [self.state_map[k] for k in FILTER_META]
            await self.db.execute(
                f"UPDATE antinuke_whitelist SET {cols} "
                f"WHERE guild_id = ? AND user_id = ?",
                vals + [self.guild_id, self.target_id]
            )

        await self.db.commit()

        view: "WhitelistLayoutView" = self.view
        view.refresh(self.state_map)
        await interaction.response.edit_message(view=view)


class WhitelistLayoutView(LayoutView):
    def __init__(
        self,
        bot,
        db,
        guild_id: int,
        target,
        target_type: str,
        state_map: dict,
        author_id: int
    ):
        super().__init__(timeout=120)
        self.bot = bot
        self.db = db
        self.guild_id = guild_id
        self.target = target
        self.target_type = target_type
        self.author_id = author_id
        self.state_map = dict(state_map)
        self._build()

    def _get_mode(self) -> str:
        return "role" if self.target_type == "role" else "user_bot"

    def _get_avatar(self) -> str:
        if self.target_type == "role":
            return self.bot.user.display_avatar.url
        return self.target.display_avatar.url

    def _get_footer(self) -> str:
        if self.target_type == "role":
            return f"Role Whitelist • {self.target.name}"
        tag = "Bot" if self.target_type == "bot" else "User"
        return f"{tag} Whitelist • {self.target}"

    def _build(self):
        self.clear_items()
        count = sum(1 for v in self.state_map.values() if v)

        body = _build_wl_text(
            target_mention=self.target.mention,
            target_name=str(self.target),
            state_map=self.state_map,
            count=count,
            target_type=self.target_type
        )

        section = Section(
            TextDisplay(f"# {E('SHIELD')}  Antinuke Whitelist\n{body}"),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self._get_avatar()),
                description="Whitelist Panel"
            )
        )

        select = WhitelistFilterSelect(
            self.db,
            self.guild_id,
            self.target.id,
            self.state_map,
            mode=self._get_mode()
        )

        all_on_btn = Button(
            label="Enable All",
            style=discord.ButtonStyle.success,
            custom_id="wl_all_on"
        )
        all_on_btn.callback = self._all_on

        all_off_btn = Button(
            label="Disable All",
            style=discord.ButtonStyle.danger,
            custom_id="wl_all_off"
        )
        all_off_btn.callback = self._all_off

        container = Container(
            section,
            Separator(),
            ActionRow(select),
            ActionRow(all_on_btn, all_off_btn),
            Separator(),
            TextDisplay(f"-# {self._get_footer()}"),
            accent_color=ACCENT_COLOR
        )
        self.add_item(container)

    def refresh(self, new_map):
        self.state_map = dict(new_map)
        self._build()

    async def _bulk_update(self, interaction: discord.Interaction, value: bool):
        for k in FILTER_META:
            self.state_map[k] = value

        cols = ", ".join(f"{k} = ?" for k in FILTER_META)
        vals = [value] * len(FILTER_META)

        if self.target_type == "role":
            await self.db.execute(
                f"UPDATE antinuke_role_whitelist SET {cols} "
                f"WHERE guild_id = ? AND role_id = ?",
                vals + [self.guild_id, self.target.id]
            )
        else:
            await self.db.execute(
                f"UPDATE antinuke_whitelist SET {cols} "
                f"WHERE guild_id = ? AND user_id = ?",
                vals + [self.guild_id, self.target.id]
            )

        await self.db.commit()
        self.refresh(self.state_map)
        await interaction.response.edit_message(view=self)

    async def _all_on(self, interaction: discord.Interaction):
        await self._bulk_update(interaction, True)

    async def _all_off(self, interaction: discord.Interaction):
        await self._bulk_update(interaction, False)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            interaction.user.id != self.author_id
            and interaction.user.id not in OWNER_IDS
        ):
            denied = build_simple_container(
                f"{E('CROSS')} You cannot interact with this panel."
            )
            v = LayoutView(timeout=None)
            v.add_item(denied)
            await interaction.response.send_message(view=v, ephemeral=True)
            return False
        return True


class ConfirmLayoutView(LayoutView):
    def __init__(self, bot, ctx, title: str, body: str):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx
        self.value = None

        section = Section(
            TextDisplay(f"# {title}\n{body}"),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=bot.user.display_avatar.url),
                description="Confirmation"
            )
        )

        confirm_btn = Button(
            label="Confirm",
            style=discord.ButtonStyle.success,
            custom_id="confirm_yes"
        )
        confirm_btn.callback = self._confirm

        cancel_btn = Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="confirm_no"
        )
        cancel_btn.callback = self._cancel

        container = Container(
            section,
            Separator(),
            ActionRow(confirm_btn, cancel_btn),
            Separator(),
            TextDisplay("-# This action requires confirmation"),
            accent_color=ACCENT_COLOR
        )
        self.add_item(container)

    async def _confirm(self, interaction: discord.Interaction):
        self.value = True
        self.stop()
        await interaction.response.defer()

    async def _cancel(self, interaction: discord.Interaction):
        self.value = False
        self.stop()
        await interaction.response.defer()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author and interaction.user.id not in OWNER_IDS:
            denied = build_simple_container(
                f"{E('CROSS')} You cannot interact with this."
            )
            v = LayoutView(timeout=None)
            v.add_item(denied)
            await interaction.response.send_message(view=v, ephemeral=True)
            return False
        return True


class MainPanelView(LayoutView):
    def __init__(self, bot, active: bool):
        super().__init__(timeout=None)
        self.bot = bot
        self.active = active

    def build(self, filter_map: dict, prefix: str):
        self.clear_items()

        body = (
            f"*Your server's Antinuke is one of the most advanced protection systems "
            f"available. Use `{prefix}antinuke wizard` for recommended settings, or "
            f"configure manually below.*\n\n"
            + _build_filter_text(filter_map)
        )

        section = Section(
            TextDisplay(f"# {E('SHIELD')}  Setup Antinuke!\n{body}"),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Antinuke Panel"
            )
        )

        configure_btn = Button(
            label="Configure Filters",
            style=discord.ButtonStyle.secondary,
            custom_id="open_filter_select",
            disabled=not self.active
        )
        done_btn = Button(
            label="Setup Done",
            style=discord.ButtonStyle.success,
            custom_id="setup_done_btn",
            disabled=not self.active
        )
        support_btn = Button(
            label="Support Server",
            style=discord.ButtonStyle.link,
            url=SUPPORT_SERVER_URL
        )

        status_text = (
            f"Status: {'Enabled' if self.active else 'Disabled'} • "
            f"{prefix}antinuke enable/disable • {prefix}antinuke help"
        )

        container = Container(
            section,
            Separator(),
            ActionRow(configure_btn, done_btn, support_btn),
            Separator(),
            TextDisplay(f"-# {status_text}"),
            accent_color=ACCENT_COLOR
        )
        self.add_item(container)
        return self


class AntiNukeCore(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db_manager = DBManager()
        self.db = None
        self.bot.loop.create_task(self._init())

    async def _init(self):
        self.db = await self.db_manager.connect()

    async def _access_denied(self, ctx):
        container = build_simple_container(
            f"# {E('LOCK')} Access Restricted\n"
            f"> Only the **Server Owner** or **Extra Owners** can run this command.",
            footer=ctx.guild.name
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    async def _get_status(self, guild_id: int) -> bool:
        async with self.db.execute(
            "SELECT status FROM antinuke WHERE guild_id = ?", (guild_id,)
        ) as cur:
            row = await cur.fetchone()
        return bool(row and row[0])

    async def _get_filter_map(self, guild_id: int) -> dict:
        async with self.db.execute(
            "SELECT * FROM antinuke_filters WHERE guild_id = ?", (guild_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return {k: False for k in FILTER_META}
            cols = [d[0] for d in cur.description]
        return {k: bool(row[cols.index(k)]) for k in FILTER_META if k in cols}

    async def _get_wl_state(self, guild_id: int, user_id: int) -> dict:
        async with self.db.execute(
            "SELECT * FROM antinuke_whitelist WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return {k: False for k in FILTER_META}
            cols = [d[0] for d in cur.description]
        return {k: bool(row[cols.index(k)]) for k in FILTER_META if k in cols}

    async def _get_role_wl_state(self, guild_id: int, role_id: int) -> dict:
        async with self.db.execute(
            "SELECT * FROM antinuke_role_whitelist WHERE guild_id = ? AND role_id = ?",
            (guild_id, role_id)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return {k: False for k in FILTER_META}
            cols = [d[0] for d in cur.description]
        return {k: bool(row[cols.index(k)]) for k in FILTER_META if k in cols}


    @commands.group(
        name="antinuke",
        aliases=["security", "anti", "an", "antiraid", "sec"],
        invoke_without_command=True
    )
    @commands.guild_only()
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def antinuke(self, ctx):
        if not await is_authorized(self.db, ctx.guild, ctx.author.id):
            return await self._access_denied(ctx)

        active = await self._get_status(ctx.guild.id)
        filter_map = await self._get_filter_map(ctx.guild.id)

        view = MainPanelView(self.bot, active).build(filter_map, ctx.prefix)
        await ctx.send(view=view)

    @antinuke.command(name="help", aliases=["commands", "cmds"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def antinuke_help(self, ctx):
        try:
            from utils.category_help import send_category_help
            sent = await send_category_help(ctx, "security", self.bot)
            if not sent:
                container = build_simple_container(
                    f"{E('CROSS')} Could not load security help category."
                )
                v = LayoutView(timeout=None)
                v.add_item(container)
                await ctx.send(view=v)
        except ImportError:
            container = build_simple_container(
                f"{E('CROSS')} Help system not available."
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            await ctx.send(view=v)

    @antinuke.command(name="enable")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def antinuke_enable(self, ctx):
        if not await is_authorized(self.db, ctx.guild, ctx.author.id):
            return await self._access_denied(ctx)

        pre = ctx.prefix
        guild = ctx.guild
        me = guild.me

        if await self._get_status(guild.id):
            filter_map = await self._get_filter_map(guild.id)
            container = build_container(
                self.bot,
                title=f"{E('SHIELD')}  Antinuke Already Active",
                body=(
                    f"*Antinuke is already running on **{guild.name}**.*\n\n"
                    + _build_filter_text(filter_map)
                ),
                footer=f"To disable use {pre}antinuke disable"
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        steps_done: list[tuple[bool, str]] = []
        progress_view = LayoutView(timeout=None)
        progress_container = build_simple_container(
            f"# {E('GEARS')}  Initializing Antinuke…",
            footer="Setting up your server protection"
        )
        progress_view.add_item(progress_container)
        msg = await ctx.send(view=progress_view)

        async def step(text: str, ok: bool = True):
            steps_done.append((ok, text))
            lines = "\n".join(
                f"{E('CHECK') if s else E('CROSS')} {t}" for s, t in steps_done
            )
            new_view = LayoutView(timeout=None)
            new_view.add_item(build_simple_container(
                f"# {E('GEARS')}  Initializing Antinuke…\n{lines}",
                footer="Setup in progress"
            ))
            try:
                await msg.edit(view=new_view)
            except discord.HTTPException:
                pass
            await asyncio.sleep(0.8)

        await step("Starting quick setup!")

        if not me.guild_permissions.administrator:
            return await step(
                "Setup failed — I need **Administrator** permission.", ok=False
            )
        await step("Verified bot permissions.")

        old_roles = [r for r in guild.roles if r.name == SECURITY_ROLE_NAME]
        if old_roles:
            for old in old_roles:
                try:
                    await old.delete(reason="Antinuke re-setup")
                    await asyncio.sleep(0.3)
                except (discord.Forbidden, discord.HTTPException):
                    pass
            await step(f"Removed {len(old_roles)} existing **{SECURITY_ROLE_NAME}** role(s).")
        else:
            await step("No existing security role found — fresh install.")

        await step(f"Crafting the **{SECURITY_ROLE_NAME}** role…")
        try:
            security_role = await guild.create_role(
                name=SECURITY_ROLE_NAME,
                color=discord.Color(ACCENT_COLOR),
                permissions=discord.Permissions(administrator=True),
                hoist=False, mentionable=False,
                reason=f"Antinuke setup — {SECURITY_ROLE_NAME}"
            )
        except discord.Forbidden:
            return await step(
                "Setup failed — missing permission to create roles.", ok=False
            )
        except discord.HTTPException as e:
            return await step(f"Setup failed — Discord error: {e}", ok=False)

        await asyncio.sleep(0.5)
        try:
            me = await guild.fetch_member(guild.me.id)
        except Exception:
            me = guild.me

        best_position = max(me.top_role.position - 1, 1)
        try:
            await guild.edit_role_positions(
                positions={security_role: best_position},
                reason="Antinuke — positioning security role"
            )
            await step(
                f"Positioned **{SECURITY_ROLE_NAME}** at slot **{best_position}**."
            )
        except (discord.Forbidden, discord.HTTPException) as e:
            await step(f"Couldn't auto-position the role ({e}).", ok=False)

        try:
            await me.add_roles(security_role, reason="Antinuke — assigning security role")
            await step(f"Assigned **{SECURITY_ROLE_NAME}** to myself.")
        except (discord.Forbidden, discord.HTTPException):
            await step("Couldn't assign role — please do it manually.", ok=False)

        await self.db.execute(
            "INSERT OR REPLACE INTO antinuke (guild_id, status) VALUES (?, ?)",
            (guild.id, True)
        )
        await self.db.commit()
        await step("Configuration saved to database.")
        await step("All antinuke modules activated — server is now protected!")

        await asyncio.sleep(1)
        try:
            await msg.delete()
        except discord.HTTPException:
            pass

        filter_map = await self._get_filter_map(guild.id)
        view = MainPanelView(self.bot, True).build(filter_map, pre)
        await ctx.send(view=view)

    @antinuke.command(name="disable")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def antinuke_disable(self, ctx):
        if not await is_authorized(self.db, ctx.guild, ctx.author.id):
            return await self._access_denied(ctx)

        if not await self._get_status(ctx.guild.id):
            container = build_simple_container(
                f"# {E('CROSS')} Antinuke Not Enabled\n"
                f"> Antinuke is not enabled on **{ctx.guild.name}**.\n"
                f"> Status: {E('DISABLED')}\n"
                f"> Use `{ctx.prefix}antinuke enable` to activate.",
                footer=ctx.guild.name
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        view = ConfirmLayoutView(
            self.bot, ctx,
            title=f"{E('WARN')} Confirm Disable",
            body=(
                f"Are you sure you want to disable antinuke on **{ctx.guild.name}**?\n"
                f"> This will **clear all filter settings**."
            )
        )
        msg = await ctx.send(view=view)
        await view.wait()

        if not view.value:
            cancel_view = LayoutView(timeout=None)
            cancel_view.add_item(build_simple_container(
                f"{E('CROSS')} **Action cancelled.**"
            ))
            return await msg.edit(view=cancel_view)

        await self.db.execute(
            "DELETE FROM antinuke WHERE guild_id = ?", (ctx.guild.id,)
        )
        await self.db.execute(
            "DELETE FROM antinuke_filters WHERE guild_id = ?", (ctx.guild.id,)
        )
        await self.db.commit()

        done_view = LayoutView(timeout=None)
        done_view.add_item(build_simple_container(
            f"# {E('CHECK')} Antinuke Disabled\n"
            f"> Disabled for **{ctx.guild.name}**.\n"
            f"> Status: {E('DISABLED')}\n"
            f"> Re-enable with `{ctx.prefix}antinuke enable`",
            footer=ctx.guild.name
        ))
        await msg.edit(view=done_view)

    @antinuke.command(name="filters", aliases=["filter"])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def antinuke_filters(self, ctx):
        if not await is_authorized(self.db, ctx.guild, ctx.author.id):
            return await self._access_denied(ctx)

        if not await self._get_status(ctx.guild.id):
            container = build_simple_container(
                f"{E('CROSS')} Antinuke is not enabled. "
                f"Use `{ctx.prefix}antinuke enable` first."
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        filter_map = await self._get_filter_map(ctx.guild.id)
        view = FilterEnableLayoutView(
            self.bot, self.db, ctx.guild.id, filter_map, ctx.author.id
        )
        await ctx.send(view=view)

    @antinuke.command(name="wizard")
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def antinuke_wizard(self, ctx):
        if not await is_authorized(self.db, ctx.guild, ctx.author.id):
            return await self._access_denied(ctx)

        all_on = {k: True for k in FILTER_META}
        all_on["prune"] = False
        all_on["botadd"] = False

        cols = list(FILTER_META.keys())
        await self.db.execute(
            f"INSERT OR REPLACE INTO antinuke_filters (guild_id, {', '.join(cols)}) "
            f"VALUES ({', '.join(['?'] * (len(cols) + 1))})",
            [ctx.guild.id] + [all_on[k] for k in cols]
        )
        await self.db.execute(
            "INSERT OR REPLACE INTO antinuke (guild_id, status) VALUES (?, ?)",
            (ctx.guild.id, True)
        )
        await self.db.commit()

        container = build_container(
            self.bot,
            title=f"{E('SHIELD')}  Antinuke Wizard Complete!",
            body=(
                f"{E('CHECK')} Applied recommended settings for **{ctx.guild.name}**.\n\n"
                + _build_filter_text(all_on)
            ),
            footer=f"Fine-tune with {ctx.prefix}antinuke filters"
        )
        v = LayoutView(timeout=None)
        v.add_item(container)
        await ctx.send(view=v)

    @antinuke.command(name="logs", aliases=["log"])
    @commands.guild_only()
    async def antinuke_logs(self, ctx, channel: discord.TextChannel = None):
        if not await is_authorized(self.db, ctx.guild, ctx.author.id):
            return await self._access_denied(ctx)

        if not channel:
            await self.db.execute(
                "DELETE FROM antinuke_logs WHERE guild_id = ?", (ctx.guild.id,)
            )
            await self.db.commit()
            container = build_simple_container(
                f"{E('CHECK')} Antinuke logs channel has been **reset**."
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        await self.db.execute(
            "INSERT OR REPLACE INTO antinuke_logs (guild_id, channel_id) VALUES (?, ?)",
            (ctx.guild.id, channel.id)
        )
        await self.db.commit()
        container = build_simple_container(
            f"{E('CHECK')} Antinuke logs will now be sent to {channel.mention}"
        )
        v = LayoutView(timeout=None)
        v.add_item(container)
        await ctx.send(view=v)


    @antinuke.command(name="wl", aliases=["whitelist"])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def antinuke_wl(self, ctx, target: str = None):
        if not await is_authorized(self.db, ctx.guild, ctx.author.id):
            return await self._access_denied(ctx)

        if not await self._get_status(ctx.guild.id):
            container = build_simple_container(
                f"{E('CROSS')} Antinuke is not enabled. "
                f"Use `{ctx.prefix}antinuke enable` first."
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        if not target:
            container = build_container(
                self.bot,
                title=f"{E('SHIELD')}  Antinuke Whitelist",
                body=(
                    f"Whitelist a **user**, **bot**, or **role** — "
                    f"they will be immune from antinuke actions.\n\n"
                    f"**Usage:**\n"
                    f"{E('ARROW')} `{ctx.prefix}antinuke wl @user`\n"
                    f"{E('ARROW')} `{ctx.prefix}antinuke wl @bot`\n"
                    f"{E('ARROW')} `{ctx.prefix}antinuke wl @role`\n\n"
                    f"**Remove:** `{ctx.prefix}antinuke unwl @user/@role`\n"
                    f"**View:** `{ctx.prefix}antinuke wlist`"
                ),
                footer="Whitelist management"
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        resolved = await self._resolve_wl_target(ctx, target)
        if resolved is None:
            container = build_simple_container(
                f"{E('CROSS')} Could not find that user, bot, or role.\n"
                f"> Make sure you mention them or provide a valid ID."
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        resolved_obj, target_type = resolved

        if target_type in ("user", "bot"):
            if resolved_obj.id == ctx.guild.owner_id:
                container = build_simple_container(
                    f"{E('CROSS')} The server owner is always whitelisted."
                )
                v = LayoutView(timeout=None)
                v.add_item(container)
                return await ctx.send(view=v)

        if target_type == "role":
            if resolved_obj.id == ctx.guild.default_role.id:
                container = build_simple_container(
                    f"{E('CROSS')} **@everyone** role cannot be whitelisted."
                )
                v = LayoutView(timeout=None)
                v.add_item(container)
                return await ctx.send(view=v)

        if target_type == "role":
            await self.db.execute(
                "INSERT OR IGNORE INTO antinuke_role_whitelist "
                "(guild_id, role_id) VALUES (?, ?)",
                (ctx.guild.id, resolved_obj.id)
            )
            await self.db.commit()
            state_map = await self._get_role_wl_state(ctx.guild.id, resolved_obj.id)
        else:
            await self.db.execute(
                "INSERT OR IGNORE INTO antinuke_whitelist "
                "(guild_id, user_id, target_type) VALUES (?, ?, ?)",
                (ctx.guild.id, resolved_obj.id, target_type)
            )
            await self.db.commit()
            state_map = await self._get_wl_state(ctx.guild.id, resolved_obj.id)

        view = WhitelistLayoutView(
            bot=self.bot,
            db=self.db,
            guild_id=ctx.guild.id,
            target=resolved_obj,
            target_type=target_type,
            state_map=state_map,
            author_id=ctx.author.id
        )
        await ctx.send(view=view)

    async def _resolve_wl_target(self, ctx, raw: str):
        guild = ctx.guild

        cleaned = raw.strip("<>@&#!")
        try:
            target_id = int(cleaned)
        except ValueError:
            target_id = None

        if raw.startswith("<@&") and target_id:
            role = guild.get_role(target_id)
            if role:
                return (role, "role")
            return None

        if target_id:
            role = guild.get_role(target_id)
            if role:
                return (role, "role")

        if target_id:
            member = guild.get_member(target_id)
            if member:
                t = "bot" if member.bot else "user"
                return (member, t)

            try:
                member = await guild.fetch_member(target_id)
                t = "bot" if member.bot else "user"
                return (member, t)
            except discord.NotFound:
                pass

            try:
                user = await ctx.bot.fetch_user(target_id)
                t = "bot" if user.bot else "user"
                return (user, t)
            except discord.NotFound:
                pass

        try:
            member = await commands.MemberConverter().convert(ctx, raw)
            t = "bot" if member.bot else "user"
            return (member, t)
        except commands.BadArgument:
            pass

        try:
            role = await commands.RoleConverter().convert(ctx, raw)
            return (role, "role")
        except commands.BadArgument:
            pass

        return None

    @antinuke.command(name="unwl", aliases=["unwhitelist"])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def antinuke_unwl(self, ctx, target: str = None):
        if not await is_authorized(self.db, ctx.guild, ctx.author.id):
            return await self._access_denied(ctx)

        if not target:
            container = build_simple_container(
                f"{E('CROSS')} Please mention a user, bot, or role to unwhitelist.\n"
                f"> Usage: `{ctx.prefix}antinuke unwl @target`"
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        resolved = await self._resolve_wl_target(ctx, target)
        if resolved is None:
            container = build_simple_container(
                f"{E('CROSS')} Could not find that user, bot, or role."
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        resolved_obj, target_type = resolved

        if target_type == "role":
            async with self.db.execute(
                "SELECT role_id FROM antinuke_role_whitelist "
                "WHERE guild_id = ? AND role_id = ?",
                (ctx.guild.id, resolved_obj.id)
            ) as cur:
                row = await cur.fetchone()

            if not row:
                container = build_simple_container(
                    f"{E('CROSS')} **{resolved_obj.mention}** is not whitelisted."
                )
                v = LayoutView(timeout=None)
                v.add_item(container)
                return await ctx.send(view=v)

            await self.db.execute(
                "DELETE FROM antinuke_role_whitelist "
                "WHERE guild_id = ? AND role_id = ?",
                (ctx.guild.id, resolved_obj.id)
            )
            await self.db.commit()

            container = build_simple_container(
                f"{E('CHECK')} Removed role **{resolved_obj.mention}** from whitelist."
            )
        else:
            async with self.db.execute(
                "SELECT user_id FROM antinuke_whitelist "
                "WHERE guild_id = ? AND user_id = ?",
                (ctx.guild.id, resolved_obj.id)
            ) as cur:
                row = await cur.fetchone()

            if not row:
                container = build_simple_container(
                    f"{E('CROSS')} **{resolved_obj.mention}** is not whitelisted."
                )
                v = LayoutView(timeout=None)
                v.add_item(container)
                return await ctx.send(view=v)

            await self.db.execute(
                "DELETE FROM antinuke_whitelist "
                "WHERE guild_id = ? AND user_id = ?",
                (ctx.guild.id, resolved_obj.id)
            )
            await self.db.commit()

            tag = "Bot" if target_type == "bot" else "User"
            container = build_simple_container(
                f"{E('CHECK')} Removed {tag} **{resolved_obj.mention}** from whitelist."
            )

        v = LayoutView(timeout=None)
        v.add_item(container)
        await ctx.send(view=v)

    @antinuke.command(name="wlist", aliases=["whitelisted"])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def antinuke_wlist(self, ctx):
        if not await is_authorized(self.db, ctx.guild, ctx.author.id):
            return await self._access_denied(ctx)

        async with self.db.execute(
            "SELECT user_id, target_type FROM antinuke_whitelist WHERE guild_id = ?",
            (ctx.guild.id,)
        ) as cur:
            user_rows = await cur.fetchall()

        async with self.db.execute(
            "SELECT role_id FROM antinuke_role_whitelist WHERE guild_id = ?",
            (ctx.guild.id,)
        ) as cur:
            role_rows = await cur.fetchall()

        if not user_rows and not role_rows:
            container = build_simple_container(
                f"{E('CROSS')} No whitelisted users, bots, or roles found."
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        lines = []

        if user_rows:
            lines.append("**Users & Bots:**")
            for (uid, ttype) in user_rows:
                member = ctx.guild.get_member(uid) or self.bot.get_user(uid)
                ttype = ttype or "user"

                if ttype == "bot":
                    tag_emoji = E("BOT")
                    tag_label = "Bot"
                else:
                    tag_emoji = E("USER")
                    tag_label = "User"

                if member:
                    lines.append(
                        f"{E('ARROW')} {member.mention} • {tag_emoji} {tag_label} • `{uid}`"
                    )
                else:
                    lines.append(
                        f"{E('ARROW')} `{uid}` • {tag_emoji} {tag_label} *(left server)*"
                    )

        if role_rows:
            if lines:
                lines.append("")
            lines.append("**Roles:**")
            for (rid,) in role_rows:
                role = ctx.guild.get_role(rid)
                if role:
                    lines.append(
                        f"{E('ARROW')} {role.mention} • {E('ROLE')} Role • `{rid}`"
                    )
                else:
                    lines.append(
                        f"{E('ARROW')} `{rid}` • {E('ROLE')} Role *(deleted)*"
                    )

        total = len(user_rows) + len(role_rows)
        container = build_container(
            self.bot,
            title=f"{E('SHIELD')}  Whitelist",
            body="\n".join(lines),
            footer=f"{ctx.guild.name} • {total} whitelisted"
        )
        v = LayoutView(timeout=None)
        v.add_item(container)
        await ctx.send(view=v)

    @antinuke.command(name="wlreset")
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def antinuke_wlreset(self, ctx):
        if not await is_authorized(self.db, ctx.guild, ctx.author.id):
            return await self._access_denied(ctx)

        view = ConfirmLayoutView(
            self.bot, ctx,
            title=f"{E('WARN')} Confirm Whitelist Reset",
            body=(
                "This will remove **ALL** whitelisted users, bots, and roles.\n"
                "Are you sure?"
            )
        )
        msg = await ctx.send(view=view)
        await view.wait()

        if not view.value:
            cancel_view = LayoutView(timeout=None)
            cancel_view.add_item(build_simple_container(f"{E('CROSS')} Cancelled."))
            return await msg.edit(view=cancel_view)

        await self.db.execute(
            "DELETE FROM antinuke_whitelist WHERE guild_id = ?", (ctx.guild.id,)
        )
        await self.db.execute(
            "DELETE FROM antinuke_role_whitelist WHERE guild_id = ?", (ctx.guild.id,)
        )
        await self.db.commit()

        done_view = LayoutView(timeout=None)
        done_view.add_item(build_simple_container(
            f"{E('CHECK')} Cleared **all** whitelisted entries for **{ctx.guild.name}**."
        ))
        await msg.edit(view=done_view)


    @commands.command(name="extraowner", aliases=["owner", "eo"])
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def extraowner(self, ctx, option: str = None, user: discord.Member = None):
        guild_id = ctx.guild.id

        if ctx.guild.member_count < MIN_MEMBER_COUNT:
            container = build_simple_container(
                f"{E('CROSS')} Your server doesn't meet the minimum member criteria."
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        if ctx.author.id != ctx.guild.owner_id and ctx.author.id not in OWNER_IDS:
            container = build_simple_container(
                f"# {E('CROSS')} Access Denied\n"
                f"Only the **Server Owner** can run this command."
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        if option is None:
            pre = ctx.prefix
            container = build_container(
                self.bot,
                title=f"{E('SHIELD')} Extra Owner Configuration",
                body=(
                    "Extra owners can adjust server antinuke settings & manage whitelist. "
                    "Careful consideration is essential before assigning this role.\n\n"
                    f"**Set:** `{pre}extraowner set @user`\n"
                    f"**Reset:** `{pre}extraowner reset @user`\n"
                    f"**View:** `{pre}extraowner view`\n"
                    f"**Clear All:** `{pre}extraowner clear`"
                ),
                footer="Extra Owner Management"
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        if option.lower() == "set":
            if user is None or user.bot:
                container = build_simple_container(
                    f"# {E('CROSS')} Error\n"
                    f"Please provide a valid human user mention."
                )
                v = LayoutView(timeout=None)
                v.add_item(container)
                return await ctx.send(view=v)

            view = ConfirmLayoutView(
                self.bot, ctx,
                title=f"{E('WARN')} Confirm Action",
                body=f"Set {user.mention} as an **Extra Owner**?"
            )
            msg = await ctx.reply(view=view)
            await view.wait()

            if view.value is None:
                timeout_view = LayoutView(timeout=None)
                timeout_view.add_item(build_simple_container(
                    f"{E('TIMER')} Confirmation timed out."
                ))
                return await msg.edit(view=timeout_view)

            if not view.value:
                cancel_view = LayoutView(timeout=None)
                cancel_view.add_item(build_simple_container(f"{E('CROSS')} Cancelled."))
                return await msg.edit(view=cancel_view)

            await self.db.execute(
                "INSERT OR REPLACE INTO extraowners (guild_id, owner_id) VALUES (?, ?)",
                (guild_id, user.id)
            )
            await self.db.commit()

            done_view = LayoutView(timeout=None)
            done_view.add_item(build_simple_container(
                f"# {E('CHECK')} Success\n"
                f"Added {user.mention} as **Extra Owner**."
            ))
            return await msg.edit(view=done_view)

        elif option.lower() == "reset":
            if not user:
                container = build_simple_container(
                    f"{E('CROSS')} Please mention which extra owner to remove."
                )
                v = LayoutView(timeout=None)
                v.add_item(container)
                return await ctx.send(view=v)

            async with self.db.execute(
                "SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?",
                (guild_id, user.id)
            ) as cur:
                row = await cur.fetchone()

            if not row:
                container = build_simple_container(
                    f"{E('CROSS')} {user.mention} is not an extra owner."
                )
                v = LayoutView(timeout=None)
                v.add_item(container)
                return await ctx.send(view=v)

            await self.db.execute(
                "DELETE FROM extraowners WHERE guild_id = ? AND owner_id = ?",
                (guild_id, user.id)
            )
            await self.db.commit()

            container = build_simple_container(
                f"# {E('CHECK')} Success\n"
                f"Removed {user.mention} from extra owners."
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        elif option.lower() == "view":
            async with self.db.execute(
                "SELECT owner_id FROM extraowners WHERE guild_id = ?", (guild_id,)
            ) as cur:
                rows = await cur.fetchall()

            if not rows:
                container = build_simple_container(
                    f"{E('CROSS')} No extra owners assigned."
                )
                v = LayoutView(timeout=None)
                v.add_item(container)
                return await ctx.send(view=v)

            owners = "\n".join(
                f"{E('ARROW')} <@{r[0]}> (`{r[0]}`)" for r in rows
            )
            container = build_container(
                self.bot,
                title=f"{E('SHIELD')} Extra Owners",
                body=owners,
                footer=f"{ctx.guild.name} • {len(rows)} owner(s)"
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)

        elif option.lower() == "clear":
            view = ConfirmLayoutView(
                self.bot, ctx,
                title=f"{E('WARN')} Confirm Clear",
                body="Remove **ALL** extra owners from this server?"
            )
            msg = await ctx.reply(view=view)
            await view.wait()

            if not view.value:
                cancel_view = LayoutView(timeout=None)
                cancel_view.add_item(build_simple_container(f"{E('CROSS')} Cancelled."))
                return await msg.edit(view=cancel_view)

            await self.db.execute(
                "DELETE FROM extraowners WHERE guild_id = ?", (guild_id,)
            )
            await self.db.commit()

            done_view = LayoutView(timeout=None)
            done_view.add_item(build_simple_container(
                f"# {E('CHECK')} Cleared\nAll extra owners removed."
            ))
            return await msg.edit(view=done_view)

        else:
            container = build_simple_container(
                f"{E('CROSS')} Invalid option. Use: `set`, `reset`, `view`, `clear`"
            )
            v = LayoutView(timeout=None)
            v.add_item(container)
            return await ctx.send(view=v)


    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        cid = interaction.data.get("custom_id", "")

        if cid == "open_filter_select":
            if not await is_authorized(
                self.db, interaction.guild, interaction.user.id
            ):
                denied = build_simple_container(
                    f"{E('CROSS')} Only the server owner or extra owners can do this."
                )
                v = LayoutView(timeout=None)
                v.add_item(denied)
                return await interaction.response.send_message(view=v, ephemeral=True)

            filter_map = await self._get_filter_map(interaction.guild.id)
            view = FilterEnableLayoutView(
                self.bot, self.db,
                interaction.guild.id, filter_map, interaction.user.id
            )
            await interaction.response.send_message(view=view, ephemeral=True)

        elif cid == "setup_done_btn":
            done_view = LayoutView(timeout=None)
            done_view.add_item(build_simple_container(
                f"{E('CHECK')} Antinuke setup is complete! Your server is now protected."
            ))
            await interaction.response.send_message(view=done_view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AntiNukeCore(bot))
