import discord
from discord.ext import commands
from utils.config import OWNER_IDS, NOPREFIX_LOG_CHANNEL_ID as LOG_CHANNEL_ID, NOPREFIX_CLAIM_CHANNEL_ID as CLAIM_CHANNEL_ID
from discord import ui
import asyncio
import aiosqlite
from pathlib import Path
from datetime import datetime, timedelta, timezone


from XEON.emojis import E as _EMGR, FALLBACK_EMOJI
import re as _re

_LOCAL_KEY_MAP = {
    "success": "SUCCESS",
    "error": "ERROR",
    "info": "INFO",
    "timer": "CLOCK",
    "user": "USER",
    "plan": "PLAN",
    "dev": "DEV",
    "clock": "CLOCK",
    "list": "LIST",
    "remove": "REMOVE",
    "add": "ADD",
    "check": "CHECK_ICO",
    "gift": "GIFT",
}

def E(key: str) -> discord.PartialEmoji:
    s = _EMGR[_LOCAL_KEY_MAP.get(key, key.upper())]
    m = _re.match(r'<(a)?:([A-Za-z0-9_]+):(\d+)>', s)
    if m:
        return discord.PartialEmoji(name=m.group(2), id=int(m.group(3)), animated=bool(m.group(1)))
    return FALLBACK_EMOJI

def ES(key: str) -> str:
    return _EMGR[_LOCAL_KEY_MAP.get(key, key.upper())]


DB_DIR = Path("db")
DB_PATH = DB_DIR / "core.db"

DEFAULT_ACCENT = discord.Colour(0x000000)
LIFETIME_SENTINEL = "9999-12-31T23:59:59"

PLANS = {
    "3 Days":   {"days": 3},
    "1 Week":   {"days": 7},
    "1 Month":  {"days": 30},
    "3 Months": {"days": 90},
    "Lifetime": {"days": None},
}

FREE_TRIAL_PLAN = "1 Week"
FREE_TRIAL_DAYS = 7


def _ensure_db():
    DB_DIR.mkdir(exist_ok=True)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utcnow().isoformat()


def parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_lifetime(plan: str) -> bool:
    return plan == "Lifetime"


def is_dev(user_id: int) -> bool:
    return user_id in OWNER_IDS


async def safe_fetch_channel(bot, cid):
    try:
        return await bot.fetch_channel(cid)
    except Exception:
        return None


async def safe_send(channel, **kwargs):
    try:
        return await channel.send(**kwargs)
    except Exception:
        return None


async def init_db():
    _ensure_db()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS noprefix (
                user_id   INTEGER PRIMARY KEY,
                plan      TEXT NOT NULL,
                added_by  INTEGER NOT NULL,
                added_at  TEXT NOT NULL,
                expires   TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS noprefix_claims (
                user_id    INTEGER PRIMARY KEY,
                claimed_at TEXT NOT NULL
            )
        """)
        await db.commit()


def _error_container(text: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('error')} {text}"))
    view.add_item(c)
    return view


def _success_container(text: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('success')} {text}"))
    view.add_item(c)
    return view


def _info_container(title: str, description: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('info')} **{title}**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(description))
    view.add_item(c)
    return view


def _np_help_container() -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('info')} **NoPrefix Commands**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('add')} `np add @user` — Add NoPrefix to a user\n"
        f"{ES('remove')} `np remove @user` — Remove NoPrefix\n"
        f"{ES('list')} `np list` — Show all active NoPrefix users\n"
        f"{ES('check')} `np check @user` — Check user's status\n"
        f"{ES('gift')} `np setup` — Post the Free Trial claim panel"
    ))
    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay("-# Developer only"))
    view.add_item(c)
    return view


def _np_status_container(
    target: discord.Member | discord.User,
    plan: str,
    remaining: str,
    expires_display: str,
    adder_text: str,
    added_at: str,
) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)

    header_text = ui.TextDisplay(f"{ES('info')} **NoPrefix Status**")
    if target.avatar:
        section = ui.Section(
            header_text,
            accessory=ui.Thumbnail(
                media=discord.UnfurledMediaItem(url=target.display_avatar.url)
            ),
        )
        c.add_item(section)
    else:
        c.add_item(header_text)

    c.add_item(ui.Separator())

    c.add_item(ui.TextDisplay(
        f"{ES('user')} **User:** {target.mention} (`{target.id}`)\n"
        f"{ES('plan')} **Plan:** {plan}\n"
        f"{ES('timer')} **Remaining:** {remaining}\n"
        f"{ES('clock')} **Expires:** {expires_display}\n"
        f"{ES('dev')} **Added by:** {adder_text}\n"
        f"-# Added at: {added_at}"
    ))

    view.add_item(c)
    return view


def _np_list_container(entries: list[dict]) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('list')} **Active NoPrefix Users**"))
    c.add_item(ui.Separator())

    if not entries:
        c.add_item(ui.TextDisplay("-# No active NoPrefix users."))
    else:
        lines = []
        for entry in entries:
            lines.append(
                f"{ES('user')} {entry['name']} — **{entry['plan']}** — {entry['remaining']}"
            )
        c.add_item(ui.TextDisplay("\n".join(lines)))

    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# Total: {len(entries)} user{'s' if len(entries) != 1 else ''}"))
    view.add_item(c)
    return view


def _np_added_container(
    target: discord.Member | discord.User,
    plan: str,
    expires_display: str,
) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('success')} **NoPrefix Added**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('user')} **User:** {target.mention}\n"
        f"{ES('plan')} **Plan:** {plan}\n"
        f"{ES('clock')} **Expires:** {expires_display}"
    ))
    view.add_item(c)
    return view


def _np_removed_container(target: discord.Member | discord.User, plan: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('success')} **NoPrefix Removed**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('user')} **User:** {target.mention}\n"
        f"{ES('plan')} **Previous plan:** {plan}"
    ))
    view.add_item(c)
    return view


def _np_dm_granted(plan: str, days_text: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('success')} **NoPrefix Granted**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"You were given **{plan}** NoPrefix for **{days_text}**."
    ))
    view.add_item(c)
    return view


def _np_dm_removed(plan: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('error')} **NoPrefix Removed**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(f"Your **{plan}** NoPrefix has been removed."))
    view.add_item(c)
    return view


def _np_dm_expired(plan: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('timer')} **NoPrefix Expired**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(f"Your **{plan}** NoPrefix has expired."))
    view.add_item(c)
    return view


def _np_log_added(target, plan, expires_display, invoker) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('add')} **NoPrefix Added**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('user')} **User:** {target} (`{target.id}`)\n"
        f"{ES('plan')} **Plan:** {plan}\n"
        f"{ES('clock')} **Expires:** {expires_display}\n"
        f"{ES('dev')} **Added by:** {invoker} (`{invoker.id}`)"
    ))
    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# {iso_now()[:19]}"))
    view.add_item(c)
    return view


def _np_log_removed(target, plan, invoker) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('remove')} **NoPrefix Removed**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('user')} **User:** {target} (`{target.id}`)\n"
        f"{ES('plan')} **Plan:** {plan}\n"
        f"{ES('dev')} **Removed by:** {invoker} (`{invoker.id}`)"
    ))
    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# {iso_now()[:19]}"))
    view.add_item(c)
    return view


def _np_log_expired(uid, user, plan) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('timer')} **NoPrefix Expired**"))
    c.add_item(ui.Separator())
    user_line = (f"{ES('user')} **User:** {user} (`{uid}`)"
                 if user else f"{ES('user')} **User:** `{uid}`")
    c.add_item(ui.TextDisplay(f"{user_line}\n{ES('plan')} **Plan:** {plan}"))
    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# {iso_now()[:19]}"))
    view.add_item(c)
    return view


def _np_log_claimed(target, expires_display) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('gift')} **Free Trial Claimed**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('user')} **User:** {target} (`{target.id}`)\n"
        f"{ES('plan')} **Plan:** {FREE_TRIAL_PLAN} (Free Trial)\n"
        f"{ES('clock')} **Expires:** {expires_display}"
    ))
    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# {iso_now()[:19]}"))
    view.add_item(c)
    return view


def _claim_panel_view() -> "ClaimNoPrefixView":
    return ClaimNoPrefixView()


class ClaimNoPrefixView(ui.LayoutView):

    def __init__(self):
        super().__init__(timeout=None)

        c = ui.Container(accent_color=DEFAULT_ACCENT)

        c.add_item(ui.TextDisplay("## › Get No-Prefix Access (Free Trial)"))
        c.add_item(ui.Separator(visible=True))
        c.add_item(ui.TextDisplay(
            "Claim your free no-prefix access for **7 days** — type commands "
            "without any prefix."
        ))
        c.add_item(ui.Separator(visible=False))
        c.add_item(ui.TextDisplay(
            "- You can claim this **once**\n"
            "- Access expires after **7 days**"
        ))
        c.add_item(ui.Separator(visible=False))

        btn = ui.Button(
            label="› Claim No-Prefix (7 days)",
            style=discord.ButtonStyle.secondary,
            custom_id="np_claim_free_trial_btn",
        )
        btn.callback = self.on_claim
        c.add_item(ui.ActionRow(btn))

        self.add_item(c)

    async def on_claim(self, interaction: discord.Interaction):
        user = interaction.user

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT claimed_at FROM noprefix_claims WHERE user_id = ?",
                (user.id,),
            ) as cur:
                already = await cur.fetchone()

        if already:
            await interaction.response.send_message(
                view=_error_container(
                    "You have already claimed your **free trial**. "
                    "This offer is **one-time only** per user."
                ),
                ephemeral=True,
            )
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT plan, expires FROM noprefix WHERE user_id = ?",
                (user.id,),
            ) as cur:
                active = await cur.fetchone()

        if active:
            plan, expires_str = active
            still_active = True
            if not is_lifetime(plan) and expires_str != LIFETIME_SENTINEL:
                try:
                    still_active = parse_iso(expires_str) > utcnow()
                except Exception:
                    still_active = False

            if still_active:
                await interaction.response.send_message(
                    view=_error_container(
                        f"You already have an **active {plan}** NoPrefix plan. "
                        "Free trial cannot be claimed."
                    ),
                    ephemeral=True,
                )
                return

        expires_dt = utcnow() + timedelta(days=FREE_TRIAL_DAYS)
        expires_str = expires_dt.isoformat()
        expires_display = expires_dt.strftime("%Y-%m-%d %H:%M UTC")

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR REPLACE INTO noprefix "
                "(user_id, plan, added_by, added_at, expires) VALUES (?, ?, ?, ?, ?)",
                (user.id, FREE_TRIAL_PLAN, user.id, iso_now(), expires_str),
            )
            await db.execute(
                "INSERT OR REPLACE INTO noprefix_claims (user_id, claimed_at) VALUES (?, ?)",
                (user.id, iso_now()),
            )
            await db.commit()

        await interaction.response.send_message(
            view=_success_container(
                f"**Free Trial Claimed!**\n"
                f"You now have **7 days** of NoPrefix access.\n"
                f"Expires: `{expires_display}`"
            ),
            ephemeral=True,
        )

        try:
            await user.send(view=_np_dm_granted(FREE_TRIAL_PLAN, f"{FREE_TRIAL_DAYS} days (Free Trial)"))
        except Exception:
            pass

        bot = interaction.client
        log_ch = bot.get_channel(LOG_CHANNEL_ID) or await safe_fetch_channel(bot, LOG_CHANNEL_ID)
        if log_ch:
            await safe_send(log_ch, view=_np_log_claimed(user, expires_display))


class PlanSelect(ui.Select):
    def __init__(self, bot: commands.Bot, target: discord.Member | discord.User, invoker: discord.Member):
        options = []
        for plan, info in PLANS.items():
            desc = "Never expires" if info["days"] is None else f"{info['days']} days"
            options.append(discord.SelectOption(label=plan, description=desc))

        super().__init__(
            placeholder="Choose a NoPrefix plan...",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.bot = bot
        self.target = target
        self.invoker = invoker

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.invoker.id:
            await interaction.response.send_message(
                view=_error_container(f"Only {self.invoker.mention} can use this."),
                ephemeral=True,
            )
            return

        chosen = self.values[0]
        info = PLANS[chosen]

        if info["days"] is None:
            expires_str = LIFETIME_SENTINEL
            expires_display = "Never"
            days_text = "forever (Lifetime)"
        else:
            expires_dt = utcnow() + timedelta(days=info["days"])
            expires_str = expires_dt.isoformat()
            expires_display = expires_dt.strftime("%Y-%m-%d %H:%M UTC")
            days_text = f"{info['days']} days"

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR REPLACE INTO noprefix (user_id, plan, added_by, added_at, expires) VALUES (?, ?, ?, ?, ?)",
                (self.target.id, chosen, self.invoker.id, iso_now(), expires_str),
            )
            await db.commit()

        try:
            await self.target.send(view=_np_dm_granted(chosen, days_text))
        except Exception:
            pass

        log_ch = self.bot.get_channel(LOG_CHANNEL_ID) or await safe_fetch_channel(self.bot, LOG_CHANNEL_ID)
        if log_ch:
            await safe_send(log_ch, view=_np_log_added(self.target, chosen, expires_display, self.invoker))

        await interaction.response.edit_message(
            content=None,
            view=_np_added_container(self.target, chosen, expires_display),
        )


class PlanSelectView(ui.LayoutView):
    def __init__(self, bot, target, invoker):
        super().__init__(timeout=60)
        self.invoker = invoker

        c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('add')} **Select NoPrefix Plan**"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(f"Choose a plan for {target.mention}"))
        c.add_item(ui.Separator(visible=False))

        select = PlanSelect(bot, target, invoker)
        row = ui.ActionRow(select)
        c.add_item(row)

        c.add_item(ui.Separator(visible=False))
        c.add_item(ui.TextDisplay("-# 60 seconds to select"))

        self.add_item(c)


class NoPrefix(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._expiry_task: asyncio.Task | None = None

    async def cog_load(self):
        await init_db()
        self.bot.add_view(ClaimNoPrefixView())
        self._expiry_task = self.bot.loop.create_task(self._expiry_loop())

    async def cog_unload(self):
        if self._expiry_task:
            self._expiry_task.cancel()
            self._expiry_task = None


    async def _expiry_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self._check_expired()
            except Exception:
                pass
            await asyncio.sleep(60)

    async def _check_expired(self):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT user_id, plan, expires FROM noprefix") as cursor:
                rows = await cursor.fetchall()

        now = utcnow()
        for uid, plan, expires_str in rows:
            if is_lifetime(plan) or expires_str == LIFETIME_SENTINEL:
                continue

            try:
                expires = parse_iso(expires_str)
            except Exception:
                async with aiosqlite.connect(str(DB_PATH)) as db:
                    await db.execute("DELETE FROM noprefix WHERE user_id = ?", (uid,))
                    await db.commit()
                continue

            if expires <= now:
                async with aiosqlite.connect(str(DB_PATH)) as db:
                    await db.execute("DELETE FROM noprefix WHERE user_id = ?", (uid,))
                    await db.commit()

                user = self.bot.get_user(uid)
                if user:
                    try:
                        await user.send(view=_np_dm_expired(plan))
                    except Exception:
                        pass

                log_ch = self.bot.get_channel(LOG_CHANNEL_ID) or await safe_fetch_channel(self.bot, LOG_CHANNEL_ID)
                if log_ch:
                    await safe_send(log_ch, view=_np_log_expired(uid, user, plan))


    def _looks_like_command(self, content: str) -> bool:
        if not content:
            return False

        first_word = content.split(maxsplit=1)[0].lower()

        if not first_word:
            return False

        cmd = self.bot.get_command(first_word)
        if cmd is not None:
            return True

        return False


    @commands.group(name="np", aliases=["noprefix"], invoke_without_command=True)
    async def np(self, ctx: commands.Context):
        if not is_dev(ctx.author.id):
            await ctx.send(view=_error_container("You are not a developer."))
            return
        await ctx.send(view=_np_help_container())

    @np.command(name="add")
    async def np_add(self, ctx: commands.Context, target: discord.Member = None):
        if not is_dev(ctx.author.id):
            await ctx.send(view=_error_container("You are not a developer."))
            return
        if target is None:
            await ctx.send(view=_error_container("Provide a user. Example: `np add @User`"))
            return

        plan_view = PlanSelectView(self.bot, target, ctx.author)
        await ctx.send(view=plan_view)

    @np.command(name="remove")
    async def np_remove(self, ctx: commands.Context, target: discord.Member = None):
        if not is_dev(ctx.author.id):
            await ctx.send(view=_error_container("You are not a developer."))
            return
        if target is None:
            await ctx.send(view=_error_container("Provide a user. Example: `np remove @User`"))
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT plan FROM noprefix WHERE user_id = ?", (target.id,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                await ctx.send(view=_error_container(f"{target.mention} does not have NoPrefix."))
                return

            await db.execute("DELETE FROM noprefix WHERE user_id = ?", (target.id,))
            await db.commit()

        plan = row[0]

        try:
            await target.send(view=_np_dm_removed(plan))
        except Exception:
            pass

        await ctx.send(view=_np_removed_container(target, plan))

        log_ch = self.bot.get_channel(LOG_CHANNEL_ID) or await safe_fetch_channel(self.bot, LOG_CHANNEL_ID)
        if log_ch:
            await safe_send(log_ch, view=_np_log_removed(target, plan, ctx.author))

    @np.command(name="list")
    async def np_list(self, ctx: commands.Context):
        if not is_dev(ctx.author.id):
            await ctx.send(view=_error_container("You are not a developer."))
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT user_id, plan, expires FROM noprefix") as cursor:
                rows = await cursor.fetchall()

        entries = []
        for uid, plan, expires_str in rows:
            user_obj = self.bot.get_user(uid)
            name = user_obj.mention if user_obj else f"`{uid}`"

            if is_lifetime(plan) or expires_str == LIFETIME_SENTINEL:
                rem_text = "Lifetime"
            else:
                try:
                    remaining = (parse_iso(expires_str) - utcnow()).days
                    rem_text = f"{remaining}d left"
                except Exception:
                    rem_text = "Unknown"

            entries.append({"name": name, "plan": plan, "remaining": rem_text})

        await ctx.send(view=_np_list_container(entries))

    @np.command(name="check")
    async def np_check(self, ctx: commands.Context, target: discord.Member = None):
        if not is_dev(ctx.author.id):
            await ctx.send(view=_error_container("You are not a developer."))
            return

        if target is None:
            target = ctx.author

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT plan, added_by, added_at, expires FROM noprefix WHERE user_id = ?",
                (target.id,),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            await ctx.send(view=_error_container(f"{target.mention} does not have NoPrefix."))
            return

        plan, added_by, added_at, expires_str = row

        if is_lifetime(plan) or expires_str == LIFETIME_SENTINEL:
            expires_display = "Never"
            remaining = "Lifetime"
        else:
            try:
                expires_dt = parse_iso(expires_str)
                expires_display = expires_dt.strftime("%Y-%m-%d %H:%M UTC")
                remaining = f"{(expires_dt - utcnow()).days} days"
            except Exception:
                expires_display = "Unknown"
                remaining = "Unknown"

        adder = self.bot.get_user(added_by)
        adder_text = f"{adder} (`{added_by}`)" if adder else f"`{added_by}`"

        await ctx.send(view=_np_status_container(
            target=target,
            plan=plan,
            remaining=remaining,
            expires_display=expires_display,
            adder_text=adder_text,
            added_at=added_at[:19],
        ))

    @np.command(name="setup")
    async def np_setup(self, ctx: commands.Context):
        if not is_dev(ctx.author.id):
            await ctx.send(view=_error_container("You are not a developer."))
            return

        channel = self.bot.get_channel(CLAIM_CHANNEL_ID) or await safe_fetch_channel(self.bot, CLAIM_CHANNEL_ID)
        if channel is None:
            await ctx.send(view=_error_container(
                f"Could not find claim channel `{CLAIM_CHANNEL_ID}`."
            ))
            return

        sent = await safe_send(channel, view=_claim_panel_view())
        if sent is None:
            await ctx.send(view=_error_container(
                f"Failed to send panel in {channel.mention}. Check permissions."
            ))
            return

        await ctx.send(view=_success_container(
            f"Free Trial panel posted in {channel.mention}."
        ))


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        content = message.content.strip()
        if not content:
            return

        try:
            prefix = await self.bot.get_prefix(message)
            if isinstance(prefix, (list, tuple)):
                prefixes = [p for p in prefix if p and not p.startswith("<@")]
            else:
                prefixes = [prefix] if prefix else []
        except Exception:
            prefixes = ["&"]

        for p in prefixes:
            if isinstance(p, str) and content.startswith(p):
                return

        if not self._looks_like_command(content):
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT plan, expires FROM noprefix WHERE user_id = ?",
                (message.author.id,),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return

        plan, expires_str = row

        if not is_lifetime(plan) and expires_str != LIFETIME_SENTINEL:
            try:
                if parse_iso(expires_str) <= utcnow():
                    async with aiosqlite.connect(str(DB_PATH)) as db:
                        await db.execute("DELETE FROM noprefix WHERE user_id = ?", (message.author.id,))
                        await db.commit()
                    try:
                        await message.author.send(view=_np_dm_expired(plan))
                    except Exception:
                        pass
                    return
            except Exception:
                return

        chosen_prefix = prefixes[0] if prefixes else "&"
        message.content = f"{chosen_prefix}{content}"
        await self.bot.process_commands(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(NoPrefix(bot))
