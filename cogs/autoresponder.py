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
    "reply": "REPLY",
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
DB_PATH = DB_DIR / "autoresponder.db"
DEFAULT_ACCENT = discord.Colour(0x000000)


async def init_db():
    DB_DIR.mkdir(exist_ok=True)
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS autoresponses (
                guild_id  INTEGER NOT NULL,
                trigger   TEXT NOT NULL,
                response  TEXT NOT NULL,
                match_type TEXT DEFAULT 'exact',
                PRIMARY KEY (guild_id, trigger)
            )
        """)
        await db.commit()


def _err(t):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('error')} {t}")); v.add_item(c); return v

def _ok(t):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('success')} {t}")); v.add_item(c); return v


def _list_view(triggers, prefix):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('reply')} **Autoresponses [{len(triggers)}]**"))
    c.add_item(ui.Separator())
    if not triggers:
        c.add_item(ui.TextDisplay(f"-# No autoresponses set. Use `{prefix}ar add <trigger> | <response>`"))
    else:
        lines = []
        for i, (t, r, mt) in enumerate(triggers, 1):
            lines.append(f"`{i:02d}.` `{t}` → `{r[:60]}{'...' if len(r) > 60 else ''}` *(`{mt}`)*")
        c.add_item(ui.TextDisplay("\n".join(lines)))
    v.add_item(c); return v


class Autoresponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await init_db()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        content = message.content.strip().lower()
        if not content:
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT trigger, response, match_type FROM autoresponses WHERE guild_id=?",
                (message.guild.id,),
            ) as cur:
                rows = await cur.fetchall()

        for trigger, response, match_type in rows:
            t = trigger.lower()
            matched = False
            if match_type == "exact" and content == t:
                matched = True
            elif match_type == "contains" and t in content:
                matched = True
            elif match_type == "startswith" and content.startswith(t):
                matched = True

            if matched:
                response = (response
                    .replace("{user}", message.author.mention)
                    .replace("{user_name}", message.author.name)
                    .replace("{server}", message.guild.name)
                    .replace("{channel}", message.channel.mention))
                try:
                    await message.channel.send(response)
                except Exception:
                    pass
                break

    @commands.group(name="autoresponder", aliases=["ar", "autoresponse"], invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def autoresponder(self, ctx):
        try:
            from utils.category_help import send_category_help
            if await send_category_help(ctx, "autoresponder", self.bot):
                return
        except Exception:
            pass
        v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('info')} **Autoresponder Commands**"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"`{ctx.prefix}ar add <trigger> | <response>` — Add (exact match)\n"
            f"`{ctx.prefix}ar addcontains <trigger> | <response>` — Triggers if msg contains text\n"
            f"`{ctx.prefix}ar addstart <trigger> | <response>` — Triggers on startswith\n"
            f"`{ctx.prefix}ar remove <trigger>` — Remove an autoresponse\n"
            f"`{ctx.prefix}ar list` — List all autoresponses\n"
            f"`{ctx.prefix}ar clear` — Remove all autoresponses\n\n"
            f"-# Variables: `{{user}}`, `{{user_name}}`, `{{server}}`, `{{channel}}`"
        ))
        v.add_item(c); await ctx.send(view=v)

    async def _add(self, ctx, args, match_type):
        if "|" not in args:
            await ctx.send(view=_err("Format: `trigger | response`"))
            return
        trigger, _, response = args.partition("|")
        trigger, response = trigger.strip(), response.strip()
        if not trigger or not response:
            await ctx.send(view=_err("Both trigger and response are required."))
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR REPLACE INTO autoresponses VALUES (?,?,?,?)",
                (ctx.guild.id, trigger, response, match_type),
            )
            await db.commit()
        await ctx.send(view=_ok(f"Added autoresponse `{trigger}` → `{response[:60]}` (`{match_type}`)"))

    @autoresponder.command(name="add")
    @commands.has_permissions(manage_messages=True)
    async def add(self, ctx, *, args: str):
        await self._add(ctx, args, "exact")

    @autoresponder.command(name="addcontains")
    @commands.has_permissions(manage_messages=True)
    async def addcontains(self, ctx, *, args: str):
        await self._add(ctx, args, "contains")

    @autoresponder.command(name="addstart")
    @commands.has_permissions(manage_messages=True)
    async def addstart(self, ctx, *, args: str):
        await self._add(ctx, args, "startswith")

    @autoresponder.command(name="remove", aliases=["rm", "delete"])
    @commands.has_permissions(manage_messages=True)
    async def remove(self, ctx, *, trigger: str):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "DELETE FROM autoresponses WHERE guild_id=? AND trigger=?",
                (ctx.guild.id, trigger),
            )
            await db.commit()
        await ctx.send(view=_ok(f"Removed autoresponse `{trigger}`"))

    @autoresponder.command(name="list", aliases=["show"])
    @commands.has_permissions(manage_messages=True)
    async def list_(self, ctx):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT trigger, response, match_type FROM autoresponses WHERE guild_id=?",
                (ctx.guild.id,),
            ) as cur:
                rows = await cur.fetchall()
        await ctx.send(view=_list_view(rows, ctx.prefix))

    @autoresponder.command(name="clear")
    @commands.has_permissions(administrator=True)
    async def clear(self, ctx):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("DELETE FROM autoresponses WHERE guild_id=?", (ctx.guild.id,))
            await db.commit()
        await ctx.send(view=_ok("All autoresponses cleared."))


async def setup(bot):
    await bot.add_cog(Autoresponder(bot))
