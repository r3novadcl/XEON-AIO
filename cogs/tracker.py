import discord
from discord.ext import commands
from discord import ui
import aiosqlite
from pathlib import Path
from datetime import datetime, timezone


from XEON.emojis import E as _EMGR, FALLBACK_EMOJI
import re as _re

_LOCAL_KEY_MAP = {
    "success": "SUCCESS",
    "error": "ERROR",
    "info": "INFO",
    "dot": "DOT",
    "msg": "MSG",
    "invite": "INVITE_ICO",
    "user": "USER",
    "stats": "STATS",
    "trash": "TRASH",
    "block": "BLOCK",
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
DB_PATH = DB_DIR / "tracker.db"
DEFAULT_ACCENT = discord.Colour(0x000000)


def _ensure_db(): DB_DIR.mkdir(exist_ok=True)
def utcnow(): return datetime.now(timezone.utc)


async def init_db():
    _ensure_db()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                guild_id  INTEGER NOT NULL,
                user_id   INTEGER NOT NULL,
                count     INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_messages (
                guild_id INTEGER NOT NULL,
                user_id  INTEGER NOT NULL,
                count    INTEGER DEFAULT 0,
                date     TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id, date)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blacklisted_channels (
                guild_id   INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, channel_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invite_cache (
                guild_id   INTEGER NOT NULL,
                code       TEXT NOT NULL,
                inviter_id INTEGER,
                uses       INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, code)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invites (
                guild_id   INTEGER NOT NULL,
                inviter_id INTEGER NOT NULL,
                invited_id INTEGER NOT NULL,
                joined_at  TEXT NOT NULL,
                fake       INTEGER DEFAULT 0,
                left       INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, invited_id)
            )
        """)
        await db.commit()


def _err(text):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('error')} {text}")); v.add_item(c); return v

def _ok(text):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('success')} {text}")); v.add_item(c); return v


def _msg_view(member, total, today, avg):
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    header = ui.TextDisplay(f"{ES('msg')} **Message Tracker**")
    if member.avatar:
        c.add_item(ui.Section(header, accessory=ui.Thumbnail(
            media=discord.UnfurledMediaItem(url=member.display_avatar.url))))
    else:
        c.add_item(header)
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('user')} **User:** {member.mention}\n"
        f"{ES('dot')} **Total Messages:** `{total}`\n"
        f"{ES('dot')} **Today's Messages:** `{today}`\n"
        f"{ES('dot')} **Avg. Daily:** `{avg:.2f}`"
    ))
    view.add_item(c); return view


def _invites_view(member, total, fake, today_inv, invited_users):
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    header = ui.TextDisplay(f"{ES('invite')} **Invite Tracker**")
    if member.avatar:
        c.add_item(ui.Section(header, accessory=ui.Thumbnail(
            media=discord.UnfurledMediaItem(url=member.display_avatar.url))))
    else:
        c.add_item(header)
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('user')} **User:** {member.mention}\n"
        f"{ES('dot')} **Total Invites:** `{total}`\n"
        f"{ES('dot')} **Fake Invites:** `{fake}`\n"
        f"{ES('dot')} **Today's Invites:** `{today_inv}`"
    ))
    if invited_users:
        c.add_item(ui.Separator(visible=False))
        c.add_item(ui.TextDisplay(f"-# Recently invited: {invited_users}"))
    view.add_item(c); return view


def _blacklist_view(guild, channels):
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('block')} **Blacklisted Channels**"))
    c.add_item(ui.Separator())
    if not channels:
        c.add_item(ui.TextDisplay("-# No channels are blacklisted."))
    else:
        lines = [f"{ES('dot')} <#{cid}>" for cid in channels]
        c.add_item(ui.TextDisplay("\n".join(lines)))
    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# Total: {len(channels)}"))
    view.add_item(c); return view


def _overview_view(bot, total_users, total_msgs, today_total, blacklist_count):
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    header = ui.TextDisplay(f"{ES('stats')} **Tracker Overview**")
    if bot.user and bot.user.avatar:
        c.add_item(ui.Section(header, accessory=ui.Thumbnail(
            media=discord.UnfurledMediaItem(url=bot.user.display_avatar.url))))
    else:
        c.add_item(header)
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        f"{ES('user')} **Tracked Users:** `{total_users}`\n"
        f"{ES('msg')} **Total Messages:** `{total_msgs}`\n"
        f"{ES('dot')} **Today's Messages:** `{today_total}`\n"
        f"{ES('block')} **Blacklisted Channels:** `{blacklist_count}`"
    ))
    view.add_item(c); return view


class Tracker(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {}

    async def cog_load(self):
        await init_db()

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                invs = await guild.invites()
                self.invite_cache[guild.id] = {i.code: i.uses for i in invs}
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if invite.guild.id not in self.invite_cache:
            self.invite_cache[invite.guild.id] = {}
        self.invite_cache[invite.guild.id][invite.code] = invite.uses

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT 1 FROM blacklisted_channels WHERE guild_id=? AND channel_id=?",
                (message.guild.id, message.channel.id),
            ) as cur:
                if await cur.fetchone():
                    return

            await db.execute(
                "INSERT INTO messages (guild_id, user_id, count) VALUES (?,?,1) "
                "ON CONFLICT(guild_id, user_id) DO UPDATE SET count = count + 1",
                (message.guild.id, message.author.id),
            )

            today = utcnow().date().isoformat()
            await db.execute(
                "INSERT INTO daily_messages (guild_id, user_id, count, date) VALUES (?,?,1,?) "
                "ON CONFLICT(guild_id, user_id, date) DO UPDATE SET count = count + 1",
                (message.guild.id, message.author.id, today),
            )
            await db.commit()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot or not member.guild:
            return

        try:
            new_invs = await member.guild.invites()
        except Exception:
            return

        old = self.invite_cache.get(member.guild.id, {})
        inviter = None
        used_code = None

        for inv in new_invs:
            if inv.uses > old.get(inv.code, 0):
                inviter = inv.inviter
                used_code = inv.code
                break

        self.invite_cache[member.guild.id] = {i.code: i.uses for i in new_invs}

        if not inviter:
            return

        fake = 1 if (utcnow() - member.created_at).days < 7 else 0

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR REPLACE INTO invites (guild_id, inviter_id, invited_id, joined_at, fake, left) "
                "VALUES (?,?,?,?,?,0)",
                (member.guild.id, inviter.id, member.id, utcnow().isoformat(), fake),
            )
            await db.commit()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "UPDATE invites SET left=1 WHERE guild_id=? AND invited_id=?",
                (member.guild.id, member.id),
            )
            await db.commit()


    @commands.command(name="messages", aliases=["msg", "msgs", "m"])
    @commands.guild_only()
    async def messages(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT count FROM messages WHERE guild_id=? AND user_id=?",
                (ctx.guild.id, member.id),
            ) as cur:
                row = await cur.fetchone()
                total = row[0] if row else 0

            today = utcnow().date().isoformat()
            async with db.execute(
                "SELECT count FROM daily_messages WHERE guild_id=? AND user_id=? AND date=?",
                (ctx.guild.id, member.id, today),
            ) as cur:
                row = await cur.fetchone()
                today_count = row[0] if row else 0

        if member.joined_at:
            days = max(1, (utcnow().date() - member.joined_at.date()).days)
        else:
            days = 1
        avg = total / days

        await ctx.send(view=_msg_view(member, total, today_count, avg))

    @commands.command(name="addmessages", aliases=["addmsg"])
    @commands.has_permissions(manage_guild=True)
    async def addmessages(self, ctx, member: discord.Member, count: int):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT INTO messages (guild_id, user_id, count) VALUES (?,?,?) "
                "ON CONFLICT(guild_id, user_id) DO UPDATE SET count = count + ?",
                (ctx.guild.id, member.id, count, count),
            )
            await db.commit()
        await ctx.send(view=_ok(f"Added `{count}` messages to {member.mention}"))

    @commands.command(name="removemessages", aliases=["rmmsg"])
    @commands.has_permissions(manage_guild=True)
    async def removemessages(self, ctx, member: discord.Member, count: int):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "UPDATE messages SET count = MAX(0, count - ?) WHERE guild_id=? AND user_id=?",
                (count, ctx.guild.id, member.id),
            )
            await db.commit()
        await ctx.send(view=_ok(f"Removed `{count}` messages from {member.mention}"))

    @commands.command(name="resetmessages", aliases=["clearmsg"])
    @commands.has_permissions(administrator=True)
    async def resetmessages(self, ctx, member: discord.Member = None):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            if member is None:
                await db.execute("DELETE FROM messages WHERE guild_id=?", (ctx.guild.id,))
                await db.execute("DELETE FROM daily_messages WHERE guild_id=?", (ctx.guild.id,))
                await db.commit()
                await ctx.send(view=_ok("All messages reset for this server."))
            else:
                await db.execute(
                    "DELETE FROM messages WHERE guild_id=? AND user_id=?",
                    (ctx.guild.id, member.id),
                )
                await db.execute(
                    "DELETE FROM daily_messages WHERE guild_id=? AND user_id=?",
                    (ctx.guild.id, member.id),
                )
                await db.commit()
                await ctx.send(view=_ok(f"Reset messages for {member.mention}"))

    @commands.command(name="blacklistchannel", aliases=["blch"])
    @commands.has_permissions(manage_channels=True)
    async def blacklistchannel(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR IGNORE INTO blacklisted_channels (guild_id, channel_id) VALUES (?,?)",
                (ctx.guild.id, channel.id),
            )
            await db.commit()
        await ctx.send(view=_ok(f"Channel {channel.mention} blacklisted from tracking."))

    @commands.command(name="unblacklistchannel", aliases=["ublch"])
    @commands.has_permissions(manage_channels=True)
    async def unblacklistchannel(self, ctx, channel: discord.TextChannel = None):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            if channel is None:
                channel = ctx.channel
            await db.execute(
                "DELETE FROM blacklisted_channels WHERE guild_id=? AND channel_id=?",
                (ctx.guild.id, channel.id),
            )
            await db.commit()
        await ctx.send(view=_ok(f"Channel {channel.mention} removed from blacklist."))

    @commands.command(name="blacklistedchannels", aliases=["blch_list"])
    @commands.has_permissions(manage_channels=True)
    async def blacklisted_channels(self, ctx):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT channel_id FROM blacklisted_channels WHERE guild_id=?",
                (ctx.guild.id,),
            ) as cur:
                rows = await cur.fetchall()
        await ctx.send(view=_blacklist_view(ctx.guild, [r[0] for r in rows]))

    @commands.command(name="invites", aliases=["i"])
    @commands.guild_only()
    async def invites(self, ctx, member: discord.Member = None):
        member = member or ctx.author

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT invited_id, fake, joined_at FROM invites WHERE guild_id=? AND inviter_id=?",
                (ctx.guild.id, member.id),
            ) as cur:
                rows = await cur.fetchall()

        total = len(rows)
        fake = sum(1 for r in rows if r[1])
        today = utcnow().date()
        today_inv = sum(1 for r in rows if datetime.fromisoformat(r[2]).date() == today)

        invited_users_names = []
        for r in rows[-5:]:
            u = ctx.guild.get_member(r[0])
            if u:
                invited_users_names.append(u.name)
        invited_str = ", ".join(invited_users_names) if invited_users_names else None

        await ctx.send(view=_invites_view(member, total, fake, today_inv, invited_str))

    @commands.command(name="tracker")
    @commands.guild_only()
    async def tracker(self, ctx):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT COUNT(*), COALESCE(SUM(count), 0) FROM messages WHERE guild_id=?",
                (ctx.guild.id,),
            ) as cur:
                users, total = await cur.fetchone()

            today = utcnow().date().isoformat()
            async with db.execute(
                "SELECT COALESCE(SUM(count), 0) FROM daily_messages WHERE guild_id=? AND date=?",
                (ctx.guild.id, today),
            ) as cur:
                today_total = (await cur.fetchone())[0]

            async with db.execute(
                "SELECT COUNT(*) FROM blacklisted_channels WHERE guild_id=?",
                (ctx.guild.id,),
            ) as cur:
                bl = (await cur.fetchone())[0]

        await ctx.send(view=_overview_view(self.bot, users or 0, total or 0, today_total or 0, bl or 0))


async def setup(bot):
    await bot.add_cog(Tracker(bot))
