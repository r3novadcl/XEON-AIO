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
    "role": "ROLE",
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
DB_PATH = DB_DIR / "reactionrole.db"
DEFAULT_ACCENT = discord.Colour(0x000000)


async def init_db():
    DB_DIR.mkdir(exist_ok=True)
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reaction_roles (
                guild_id   INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                emoji      TEXT NOT NULL,
                role_id    INTEGER NOT NULL,
                PRIMARY KEY (message_id, emoji)
            )
        """)
        await db.commit()


def _err(t):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('error')} {t}")); v.add_item(c); return v

def _ok(t):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('success')} {t}")); v.add_item(c); return v


class ReactionRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await init_db()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id or payload.guild_id is None:
            return

        emoji_str = str(payload.emoji)

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji=?",
                (payload.message_id, emoji_str),
            ) as cur:
                row = await cur.fetchone()

        if not row:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = guild.get_role(row[0])
        member = guild.get_member(payload.user_id)
        if role and member and role < guild.me.top_role:
            try:
                await member.add_roles(role, reason="Reaction Role")
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.bot.user.id or payload.guild_id is None:
            return

        emoji_str = str(payload.emoji)

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji=?",
                (payload.message_id, emoji_str),
            ) as cur:
                row = await cur.fetchone()

        if not row:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = guild.get_role(row[0])
        member = guild.get_member(payload.user_id)
        if role and member and role < guild.me.top_role:
            try:
                await member.remove_roles(role, reason="Reaction Role removed")
            except Exception:
                pass

    @commands.group(name="reactionrole", aliases=["rr"], invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def rr(self, ctx):
        try:
            from utils.category_help import send_category_help
            if await send_category_help(ctx, "reactionrole", self.bot):
                return
        except Exception:
            pass
        v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('info')} **Reaction Role Commands**"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"`{ctx.prefix}rr add <message_id> <emoji> <role>` — Bind emoji to role\n"
            f"`{ctx.prefix}rr remove <message_id> <emoji>` — Remove binding\n"
            f"`{ctx.prefix}rr list` — List all reaction roles\n"
            f"`{ctx.prefix}rr clear <message_id>` — Clear all roles on a message"
        ))
        v.add_item(c); await ctx.send(view=v)

    @rr.command(name="add")
    @commands.has_permissions(manage_roles=True)
    async def add(self, ctx, message_id: int, emoji: str, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            await ctx.send(view=_err(f"My top role must be higher than {role.mention}"))
            return

        message = None
        for ch in ctx.guild.text_channels:
            try:
                message = await ch.fetch_message(message_id)
                break
            except Exception:
                continue

        if not message:
            await ctx.send(view=_err(f"Could not find message with ID `{message_id}`"))
            return

        try:
            await message.add_reaction(emoji)
        except Exception:
            await ctx.send(view=_err(f"Invalid emoji: {emoji}"))
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR REPLACE INTO reaction_roles VALUES (?,?,?,?)",
                (ctx.guild.id, message_id, emoji, role.id),
            )
            await db.commit()

        await ctx.send(view=_ok(f"Bound {emoji} to {role.mention} on message `{message_id}`"))

    @rr.command(name="remove", aliases=["rm"])
    @commands.has_permissions(manage_roles=True)
    async def remove(self, ctx, message_id: int, emoji: str):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "DELETE FROM reaction_roles WHERE message_id=? AND emoji=?",
                (message_id, emoji),
            )
            await db.commit()
        await ctx.send(view=_ok(f"Removed {emoji} reaction role from message `{message_id}`"))

    @rr.command(name="list", aliases=["show"])
    @commands.has_permissions(manage_roles=True)
    async def list_(self, ctx):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT message_id, emoji, role_id FROM reaction_roles WHERE guild_id=?",
                (ctx.guild.id,),
            ) as cur:
                rows = await cur.fetchall()

        v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('role')} **Reaction Roles [{len(rows)}]**"))
        c.add_item(ui.Separator())
        if not rows:
            c.add_item(ui.TextDisplay("-# No reaction roles configured."))
        else:
            lines = []
            for mid, emoji, rid in rows:
                role = ctx.guild.get_role(rid)
                lines.append(f"{ES('dot')} `{mid}` {emoji} → {role.mention if role else f'`{rid}`'}")
            c.add_item(ui.TextDisplay("\n".join(lines)))
        v.add_item(c)
        await ctx.send(view=v)

    @rr.command(name="clear")
    @commands.has_permissions(manage_roles=True)
    async def clear(self, ctx, message_id: int):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "DELETE FROM reaction_roles WHERE message_id=?", (message_id,)
            )
            await db.commit()
        await ctx.send(view=_ok(f"Cleared all reaction roles on message `{message_id}`"))


async def setup(bot):
    await bot.add_cog(ReactionRole(bot))
