import discord
from discord.ext import commands, tasks
from discord import ui
import aiosqlite
import random
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone

from utils.category_help import send_category_help


from XEON.emojis import E as _EMGR, FALLBACK_EMOJI
import re as _re

_LOCAL_KEY_MAP = {
    "success": "SUCCESS",
    "error": "ERROR",
    "info": "INFO",
    "gift": "GIFT",
    "gift_new": "GIFT_NEW",
    "tada": "TADA",
    "dot": "DOT",
    "timer": "CLOCK",
    "trophy": "TROPHY",
    "host": "HOST",
    "users": "USERS",
}

def E(key: str) -> discord.PartialEmoji:
    s = _EMGR[_LOCAL_KEY_MAP.get(key, key.upper())]
    m = _re.match(r'<(a)?:([A-Za-z0-9_]+):(\d+)>', s)
    if m:
        return discord.PartialEmoji(name=m.group(2), id=int(m.group(3)), animated=bool(m.group(1)))
    return FALLBACK_EMOJI

def ES(key: str) -> str:
    return _EMGR[_LOCAL_KEY_MAP.get(key, key.upper())]


from XEON.emojis import E as _EMGR, FALLBACK_EMOJI
PARTICIPATE_EMOJI = _EMGR["TADAA"]

DB_DIR = Path("db")
DB_PATH = DB_DIR / "core.db"

DEFAULT_ACCENT = discord.Colour(0x000000)

GIVEAWAY_MANAGERS = set()


def _ensure_db():
    DB_DIR.mkdir(exist_ok=True)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_duration(text: str) -> int | None:
    pattern = re.compile(r"(\d+)\s*([smhdw])", re.IGNORECASE)
    matches = pattern.findall(text.lower())
    if not matches:
        try:
            return int(text) * 60
        except ValueError:
            return None

    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    total = 0
    for value, unit in matches:
        total += int(value) * multipliers[unit.lower()]
    return total if total > 0 else None


async def init_db():
    _ensure_db()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                message_id  INTEGER PRIMARY KEY,
                channel_id  INTEGER NOT NULL,
                guild_id    INTEGER NOT NULL,
                host_id     INTEGER NOT NULL,
                prize       TEXT NOT NULL,
                winners     INTEGER NOT NULL,
                ends_at     TEXT NOT NULL,
                ended       INTEGER NOT NULL DEFAULT 0,
                winner_ids  TEXT
            )
        """)
        await db.commit()


def can_manage(member: discord.Member) -> bool:
    if member.id in GIVEAWAY_MANAGERS:
        return True
    if member.guild_permissions.manage_guild:
        return True
    return False


def _error_container(text: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('error')} {text}"))
    view.add_item(c)
    return view


def _giveaway_active_view(
    prize: str,
    winners_count: int,
    ends_at: datetime,
    host: discord.User | discord.Member,
    participate_emoji_str: str,
) -> ui.LayoutView:
    view = ui.LayoutView(timeout=None)
    c = ui.Container(accent_color=DEFAULT_ACCENT)

    c.add_item(ui.TextDisplay(f"{ES('gift')} **{prize}** {ES('gift')}"))
    c.add_item(ui.Separator())

    end_ts = int(ends_at.timestamp())
    c.add_item(ui.TextDisplay(
        f"{ES('dot')} **Winners:** {winners_count}\n"
        f"{ES('dot')} **Ends:** <t:{end_ts}:R> (<t:{end_ts}:f>)\n"
        f"{ES('dot')} **Hosted by:** {host.mention}"
    ))
    c.add_item(ui.Separator())

    c.add_item(ui.TextDisplay(
        f"{ES('dot')} React with {participate_emoji_str} to participate!"
    ))
    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# Ends at • <t:{end_ts}:t>"))

    view.add_item(c)
    return view


def _giveaway_ended_view(
    prize: str,
    host: discord.User | discord.Member,
    total_participants: int,
    ended_at: datetime,
) -> ui.LayoutView:
    view = ui.LayoutView(timeout=None)
    c = ui.Container(accent_color=DEFAULT_ACCENT)

    c.add_item(ui.TextDisplay(f"{ES('gift')} **{prize}** {ES('gift')}"))
    c.add_item(ui.Separator())

    c.add_item(ui.TextDisplay(
        f"{ES('dot')} **Hosted by:** {host.mention}\n"
        f"{ES('dot')} **Total participant(s):** {total_participants}"
    ))
    c.add_item(ui.Separator(visible=False))

    end_ts = int(ended_at.timestamp())
    c.add_item(ui.TextDisplay(f"-# Ended • <t:{end_ts}:f>"))

    view.add_item(c)
    return view


def _winner_announce_view(
    winners: list[discord.User | discord.Member],
    prize: str,
    host: discord.User | discord.Member,
    giveaway_url: str,
) -> ui.LayoutView:
    view = ui.LayoutView(timeout=None)
    c = ui.Container(accent_color=DEFAULT_ACCENT)

    winner_mentions = ", ".join(w.mention for w in winners)

    c.add_item(ui.TextDisplay(
        f"{ES('tada')} Congrats, {winner_mentions} you have won **{prize}**, "
        f"hosted by {host.mention}"
    ))

    c.add_item(ui.ActionRow(
        ui.Button(
            label="Giveaway Link",
            style=discord.ButtonStyle.link,
            url=giveaway_url,
        ),
    ))

    view.add_item(c)
    return view


def _no_winners_view(prize: str, giveaway_url: str) -> ui.LayoutView:
    view = ui.LayoutView(timeout=None)
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(
        f"{ES('error')} Could not determine a winner for **{prize}** — "
        "not enough valid participants."
    ))
    c.add_item(ui.ActionRow(
        ui.Button(
            label="Giveaway Link",
            style=discord.ButtonStyle.link,
            url=giveaway_url,
        ),
    ))
    view.add_item(c)
    return view


def _giveaway_list_view(entries: list[dict]) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('gift')} **Active Giveaways**"))
    c.add_item(ui.Separator())

    if not entries:
        c.add_item(ui.TextDisplay("-# No active giveaways."))
    else:
        lines = []
        for e in entries:
            lines.append(
                f"{ES('dot')} **{e['prize']}** — "
                f"Ends <t:{e['end_ts']}:R> — "
                f"[Jump]({e['url']})"
            )
        c.add_item(ui.TextDisplay("\n".join(lines)))

    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# Total: {len(entries)}"))
    view.add_item(c)
    return view


class Giveaway(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._participate_str = (
            PARTICIPATE_EMOJI
            if isinstance(PARTICIPATE_EMOJI, str)
            else str(PARTICIPATE_EMOJI)
        )

    async def cog_load(self):
        await init_db()
        self.check_giveaways.start()

    async def cog_unload(self):
        self.check_giveaways.cancel()


    @tasks.loop(seconds=10)
    async def check_giveaways(self):
        try:
            async with aiosqlite.connect(str(DB_PATH)) as db:
                async with db.execute(
                    "SELECT message_id, channel_id, guild_id, host_id, prize, winners, ends_at "
                    "FROM giveaways WHERE ended = 0"
                ) as cursor:
                    rows = await cursor.fetchall()

            now = utcnow()
            for row in rows:
                msg_id, ch_id, guild_id, host_id, prize, winners, ends_at_str = row
                try:
                    ends_at = datetime.fromisoformat(ends_at_str)
                    if ends_at.tzinfo is None:
                        ends_at = ends_at.replace(tzinfo=timezone.utc)
                except Exception:
                    continue

                if ends_at <= now:
                    await self._end_giveaway(msg_id, ch_id, guild_id, host_id, prize, winners)
        except Exception as e:
            print(f"[Giveaway] check loop error: {e}")

    @check_giveaways.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


    async def _end_giveaway(
        self,
        msg_id: int,
        ch_id: int,
        guild_id: int,
        host_id: int,
        prize: str,
        winners_count: int,
    ):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        channel = guild.get_channel(ch_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(msg_id)
        except (discord.NotFound, discord.Forbidden):
            async with aiosqlite.connect(str(DB_PATH)) as db:
                await db.execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (msg_id,))
                await db.commit()
            return

        host = guild.get_member(host_id) or self.bot.get_user(host_id)
        if host is None:
            try:
                host = await self.bot.fetch_user(host_id)
            except Exception:
                host = None
        if host is None:
            return

        participants = []
        for reaction in message.reactions:
            emoji_match = False
            if isinstance(PARTICIPATE_EMOJI, str):
                if str(reaction.emoji) == PARTICIPATE_EMOJI:
                    emoji_match = True
            else:
                if hasattr(reaction.emoji, "id") and reaction.emoji.id == PARTICIPATE_EMOJI.id:
                    emoji_match = True

            if emoji_match:
                async for user in reaction.users():
                    if not user.bot:
                        participants.append(user)
                break

        total = len(participants)

        winners_list = []
        if total > 0:
            actual_count = min(winners_count, total)
            winners_list = random.sample(participants, actual_count)

        try:
            ended_view = _giveaway_ended_view(
                prize=prize,
                host=host,
                total_participants=total,
                ended_at=utcnow(),
            )
            await message.edit(view=ended_view)
        except Exception as e:
            print(f"[Giveaway] failed to edit msg: {e}")

        winner_ids_str = ",".join(str(w.id) for w in winners_list)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "UPDATE giveaways SET ended = 1, winner_ids = ? WHERE message_id = ?",
                (winner_ids_str, msg_id),
            )
            await db.commit()

        giveaway_url = f"https://discord.com/channels/{guild_id}/{ch_id}/{msg_id}"

        try:
            if winners_list:
                await channel.send(
                    view=_winner_announce_view(winners_list, prize, host, giveaway_url),
                    allowed_mentions=discord.AllowedMentions(
                        users=winners_list,
                        roles=False,
                        everyone=False,
                    ),
                )
            else:
                await channel.send(view=_no_winners_view(prize, giveaway_url))
        except Exception as e:
            print(f"[Giveaway] failed to announce: {e}")


    @commands.group(name="giveaway", aliases=["g"], invoke_without_command=True)
    async def giveaway(self, ctx: commands.Context):
        await send_category_help(ctx, "giveaway", self.bot)

    @commands.command(name="gstart")
    async def gstart(
        self,
        ctx: commands.Context,
        duration: str,
        winners: int,
        *,
        prize: str,
    ):
        if not can_manage(ctx.author):
            await ctx.send(view=_error_container("You need **Manage Server** permission."))
            return

        seconds = parse_duration(duration)
        if seconds is None or seconds < 10:
            await ctx.send(view=_error_container(
                "Invalid duration. Use formats like `30s`, `5m`, `2h`, `1d`. Minimum 10s."
            ))
            return

        if winners < 1 or winners > 50:
            await ctx.send(view=_error_container("Winners must be between 1 and 50."))
            return

        ends_at = utcnow() + timedelta(seconds=seconds)

        gw_view = _giveaway_active_view(
            prize=prize,
            winners_count=winners,
            ends_at=ends_at,
            host=ctx.author,
            participate_emoji_str=self._participate_str,
        )

        try:
            msg = await ctx.channel.send(view=gw_view)
        except discord.Forbidden:
            await ctx.send(view=_error_container("I can't send messages here."))
            return

        try:
            await msg.add_reaction(PARTICIPATE_EMOJI)
        except Exception:
            pass

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT INTO giveaways (message_id, channel_id, guild_id, host_id, prize, winners, ends_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (msg.id, ctx.channel.id, ctx.guild.id, ctx.author.id, prize, winners, ends_at.isoformat()),
            )
            await db.commit()

        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name="gend")
    async def gend(self, ctx: commands.Context, message_id: int):
        if not can_manage(ctx.author):
            await ctx.send(view=_error_container("You need **Manage Server** permission."))
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT channel_id, guild_id, host_id, prize, winners, ended "
                "FROM giveaways WHERE message_id = ?",
                (message_id,),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            await ctx.send(view=_error_container(f"No giveaway found with ID `{message_id}`."))
            return

        ch_id, guild_id, host_id, prize, winners, ended = row

        if ended:
            await ctx.send(view=_error_container("That giveaway has already ended."))
            return

        await self._end_giveaway(message_id, ch_id, guild_id, host_id, prize, winners)

        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name="greroll")
    async def greroll(self, ctx: commands.Context, message_id: int):
        if not can_manage(ctx.author):
            await ctx.send(view=_error_container("You need **Manage Server** permission."))
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT channel_id, guild_id, host_id, prize, winners, ended "
                "FROM giveaways WHERE message_id = ?",
                (message_id,),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            await ctx.send(view=_error_container(f"No giveaway found with ID `{message_id}`."))
            return

        ch_id, guild_id, host_id, prize, winners, ended = row

        if not ended:
            await ctx.send(view=_error_container("Giveaway hasn't ended yet."))
            return

        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(ch_id) if guild else None
        if not channel:
            await ctx.send(view=_error_container("Channel not found."))
            return

        try:
            message = await channel.fetch_message(message_id)
        except Exception:
            await ctx.send(view=_error_container("Original giveaway message is gone."))
            return

        host = guild.get_member(host_id) or self.bot.get_user(host_id)
        if not host:
            try:
                host = await self.bot.fetch_user(host_id)
            except Exception:
                host = ctx.author

        participants = []
        for reaction in message.reactions:
            emoji_match = False
            if isinstance(PARTICIPATE_EMOJI, str):
                if str(reaction.emoji) == PARTICIPATE_EMOJI:
                    emoji_match = True
            else:
                if hasattr(reaction.emoji, "id") and reaction.emoji.id == PARTICIPATE_EMOJI.id:
                    emoji_match = True
            if emoji_match:
                async for user in reaction.users():
                    if not user.bot:
                        participants.append(user)
                break

        if not participants:
            await channel.send(view=_no_winners_view(prize, message.jump_url))
            try:
                await ctx.message.delete()
            except Exception:
                pass
            return

        new_winners = random.sample(participants, min(winners, len(participants)))

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "UPDATE giveaways SET winner_ids = ? WHERE message_id = ?",
                (",".join(str(w.id) for w in new_winners), message_id),
            )
            await db.commit()

        await channel.send(
            view=_winner_announce_view(new_winners, prize, host, message.jump_url),
            allowed_mentions=discord.AllowedMentions(
                users=new_winners,
                roles=False,
                everyone=False,
            ),
        )

        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name="glist")
    async def glist(self, ctx: commands.Context):
        if not can_manage(ctx.author):
            await ctx.send(view=_error_container("You need **Manage Server** permission."))
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT message_id, channel_id, prize, ends_at FROM giveaways "
                "WHERE guild_id = ? AND ended = 0",
                (ctx.guild.id,),
            ) as cursor:
                rows = await cursor.fetchall()

        entries = []
        for msg_id, ch_id, prize, ends_at_str in rows:
            try:
                ends_at = datetime.fromisoformat(ends_at_str)
                if ends_at.tzinfo is None:
                    ends_at = ends_at.replace(tzinfo=timezone.utc)
                entries.append({
                    "prize": prize,
                    "end_ts": int(ends_at.timestamp()),
                    "url": f"https://discord.com/channels/{ctx.guild.id}/{ch_id}/{msg_id}",
                })
            except Exception:
                continue

        await ctx.send(view=_giveaway_list_view(entries))

    @commands.command(name="gdelete")
    async def gdelete(self, ctx: commands.Context, message_id: int):
        if not can_manage(ctx.author):
            await ctx.send(view=_error_container("You need **Manage Server** permission."))
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT channel_id FROM giveaways WHERE message_id = ?",
                (message_id,),
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                await ctx.send(view=_error_container(f"No giveaway found with ID `{message_id}`."))
                return

            await db.execute("DELETE FROM giveaways WHERE message_id = ?", (message_id,))
            await db.commit()

        try:
            ch = ctx.guild.get_channel(row[0])
            if ch:
                msg = await ch.fetch_message(message_id)
                await msg.delete()
        except Exception:
            pass

        try:
            await ctx.message.delete()
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
