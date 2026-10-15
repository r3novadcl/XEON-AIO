import discord
from discord.ext import commands
from discord import ui
import aiosqlite
from pathlib import Path


from XEON.emojis import E as _EMGR, FALLBACK_EMOJI
import re as _re

_LOCAL_KEY_MAP = {
    "success": "SUCCESS",
    "error": "ERROR",
    "info": "INFO",
    "dot": "DOT",
    "react": "REACT",
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
DB_PATH = DB_DIR / "autoreact.db"
DEFAULT_ACCENT = discord.Colour(0x000000)


async def init_db():
    DB_DIR.mkdir(exist_ok=True)
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS autoreacts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id  INTEGER NOT NULL,
                trigger   TEXT NOT NULL,
                emoji     TEXT NOT NULL,
                scope     TEXT DEFAULT 'message'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channel_autoreacts (
                guild_id   INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                emoji      TEXT NOT NULL,
                PRIMARY KEY (guild_id, channel_id, emoji)
            )
        """)
        await db.commit()


def _err(t):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('error')} {t}")); v.add_item(c); return v

def _ok(t):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('success')} {t}")); v.add_item(c); return v


def _list_view(rows, channel_rows, guild):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('react')} **Autoreacts**"))
    c.add_item(ui.Separator())

    if rows:
        lines = []
        for i, (rid, trigger, emoji) in enumerate(rows, 1):
            lines.append(f"`{i:02d}.` `{trigger}` → {emoji}")
        c.add_item(ui.TextDisplay(f"**Trigger-based:**\n" + "\n".join(lines)))
    else:
        c.add_item(ui.TextDisplay("-# No trigger-based autoreacts."))

    c.add_item(ui.Separator(visible=False))

    if channel_rows:
        lines = []
        for cid, emoji in channel_rows:
            ch = guild.get_channel(cid)
            lines.append(f"{ES('dot')} {ch.mention if ch else f'<#{cid}>'} → {emoji}")
        c.add_item(ui.TextDisplay(f"**Channel-based:**\n" + "\n".join(lines)))
    else:
        c.add_item(ui.TextDisplay("-# No channel-based autoreacts."))

    v.add_item(c); return v


class Autoreact(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await init_db()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT emoji FROM channel_autoreacts WHERE guild_id=? AND channel_id=?",
                (message.guild.id, message.channel.id),
            ) as cur:
                ch_reacts = await cur.fetchall()

            content = message.content.lower()
            async with db.execute(
                "SELECT trigger, emoji FROM autoreacts WHERE guild_id=?",
                (message.guild.id,),
            ) as cur:
                trigger_reacts = await cur.fetchall()

        for (emoji,) in ch_reacts:
            try:
                await message.add_reaction(emoji)
            except Exception:
                pass

        for trigger, emoji in trigger_reacts:
            if trigger.lower() in content:
                try:
                    await message.add_reaction(emoji)
                except Exception:
                    pass

    @commands.group(name="autoreact", aliases=["arc"], invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def autoreact(self, ctx):
        try:
            from utils.category_help import send_category_help
            if await send_category_help(ctx, "autoreact", self.bot):
                return
        except Exception:
            pass
        v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('info')} **Autoreact Commands**"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"`{ctx.prefix}arc add <trigger> <emoji>` — React when message contains trigger\n"
            f"`{ctx.prefix}arc channel <#ch> <emoji>` — React to all messages in channel\n"
            f"`{ctx.prefix}arc remove <trigger>` — Remove trigger-based autoreact\n"
            f"`{ctx.prefix}arc removechannel <#ch> <emoji>` — Remove channel-based\n"
            f"`{ctx.prefix}arc list` — Show all autoreacts\n"
            f"`{ctx.prefix}arc clear` — Remove all"
        ))
        v.add_item(c); await ctx.send(view=v)

    @autoreact.command(name="add")
    @commands.has_permissions(manage_messages=True)
    async def add(self, ctx, trigger: str, emoji: str):
        try:
            await ctx.message.add_reaction(emoji)
        except Exception:
            await ctx.send(view=_err(f"Invalid emoji: {emoji}"))
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT INTO autoreacts (guild_id, trigger, emoji) VALUES (?,?,?)",
                (ctx.guild.id, trigger, emoji),
            )
            await db.commit()
        await ctx.send(view=_ok(f"Will react with {emoji} when messages contain `{trigger}`"))

    @autoreact.command(name="channel", aliases=["ch"])
    @commands.has_permissions(manage_messages=True)
    async def channel(self, ctx, channel: discord.TextChannel, emoji: str):
        try:
            await ctx.message.add_reaction(emoji)
        except Exception:
            await ctx.send(view=_err(f"Invalid emoji: {emoji}"))
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR IGNORE INTO channel_autoreacts VALUES (?,?,?)",
                (ctx.guild.id, channel.id, emoji),
            )
            await db.commit()
        await ctx.send(view=_ok(f"Will react with {emoji} on all messages in {channel.mention}"))

    @autoreact.command(name="remove", aliases=["rm"])
    @commands.has_permissions(manage_messages=True)
    async def remove(self, ctx, *, trigger: str):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "DELETE FROM autoreacts WHERE guild_id=? AND trigger=?",
                (ctx.guild.id, trigger),
            )
            await db.commit()
        await ctx.send(view=_ok(f"Removed autoreact for `{trigger}`"))

    @autoreact.command(name="removechannel", aliases=["rmch"])
    @commands.has_permissions(manage_messages=True)
    async def remove_channel(self, ctx, channel: discord.TextChannel, emoji: str):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "DELETE FROM channel_autoreacts WHERE guild_id=? AND channel_id=? AND emoji=?",
                (ctx.guild.id, channel.id, emoji),
            )
            await db.commit()
        await ctx.send(view=_ok(f"Removed channel autoreact for {channel.mention}"))

    @autoreact.command(name="list", aliases=["show"])
    @commands.has_permissions(manage_messages=True)
    async def list_(self, ctx):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT id, trigger, emoji FROM autoreacts WHERE guild_id=?",
                (ctx.guild.id,),
            ) as cur:
                rows = await cur.fetchall()
            async with db.execute(
                "SELECT channel_id, emoji FROM channel_autoreacts WHERE guild_id=?",
                (ctx.guild.id,),
            ) as cur:
                ch_rows = await cur.fetchall()
        await ctx.send(view=_list_view(rows, ch_rows, ctx.guild))

    @autoreact.command(name="clear")
    @commands.has_permissions(administrator=True)
    async def clear(self, ctx):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("DELETE FROM autoreacts WHERE guild_id=?", (ctx.guild.id,))
            await db.execute("DELETE FROM channel_autoreacts WHERE guild_id=?", (ctx.guild.id,))
            await db.commit()
        await ctx.send(view=_ok("All autoreacts cleared."))


async def setup(bot):
    await bot.add_cog(Autoreact(bot))
