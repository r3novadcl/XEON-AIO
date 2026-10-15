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
    "human": "HUMAN",
    "bot": "BOT_ICON",
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
DB_PATH = DB_DIR / "autorole.db"
DEFAULT_ACCENT = discord.Colour(0x000000)


def _ensure_db(): DB_DIR.mkdir(exist_ok=True)


async def init_db():
    _ensure_db()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS autoroles (
                guild_id INTEGER NOT NULL,
                role_id  INTEGER NOT NULL,
                type     TEXT NOT NULL CHECK(type IN ('human','bot')),
                PRIMARY KEY (guild_id, role_id, type)
            )
        """)
        await db.commit()


async def _add(gid, rid, kind):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute(
            "SELECT 1 FROM autoroles WHERE guild_id=? AND role_id=? AND type=?",
            (gid, rid, kind),
        ) as cur:
            if await cur.fetchone():
                return False
        await db.execute(
            "INSERT INTO autoroles VALUES (?,?,?)", (gid, rid, kind)
        )
        await db.commit()
    return True


async def _remove(gid, rid, kind):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute(
            "DELETE FROM autoroles WHERE guild_id=? AND role_id=? AND type=?",
            (gid, rid, kind),
        ) as cur:
            pass
        await db.commit()
    return True


async def _list(gid, kind):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute(
            "SELECT role_id FROM autoroles WHERE guild_id=? AND type=?",
            (gid, kind),
        ) as cur:
            return [r[0] for r in await cur.fetchall()]


def _err(t):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('error')} {t}")); v.add_item(c); return v

def _ok(t):
    v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('success')} {t}")); v.add_item(c); return v


def _list_view(kind, roles, guild):
    label = "Bot" if kind == "bot" else "Human"
    icon = ES("bot") if kind == "bot" else ES("human")
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{icon} **{label} Autoroles [{len(roles)}]**"))
    c.add_item(ui.Separator())
    if not roles:
        c.add_item(ui.TextDisplay(f"-# No {kind} autoroles configured."))
    else:
        lines = []
        for i, rid in enumerate(roles, 1):
            r = guild.get_role(rid)
            lines.append(f"`{i:02d}.` {r.mention if r else f'<Deleted Role {rid}>'}")
        c.add_item(ui.TextDisplay("\n".join(lines)))
    view.add_item(c); return view


class Autorole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await init_db()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        kind = "bot" if member.bot else "human"
        role_ids = await _list(member.guild.id, kind)
        for rid in role_ids:
            role = member.guild.get_role(rid)
            if role and role < member.guild.me.top_role:
                try:
                    await member.add_roles(role, reason=f"Autorole ({kind})")
                except Exception:
                    pass

    @commands.group(name="autorole", aliases=["autoroles"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def autorole(self, ctx):
        try:
            from utils.category_help import send_category_help
            if await send_category_help(ctx, "autorole", self.bot):
                return
        except Exception:
            pass
        v = ui.LayoutView(); c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('info')} **Autorole Commands**"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"`{ctx.prefix}autorole humans add <role>` — Add human autorole\n"
            f"`{ctx.prefix}autorole humans remove <role>` — Remove human autorole\n"
            f"`{ctx.prefix}autorole humans list` — List human autoroles\n"
            f"`{ctx.prefix}autorole bots add <role>` — Add bot autorole\n"
            f"`{ctx.prefix}autorole bots remove <role>` — Remove bot autorole\n"
            f"`{ctx.prefix}autorole bots list` — List bot autoroles"
        ))
        v.add_item(c); await ctx.send(view=v)

    @autorole.group(name="humans", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def humans(self, ctx):
        await ctx.send(view=_list_view("human", await _list(ctx.guild.id, "human"), ctx.guild))

    @humans.command(name="add")
    @commands.has_permissions(administrator=True)
    async def humans_add(self, ctx, role: discord.Role):
        ok = await _add(ctx.guild.id, role.id, "human")
        if ok:
            await ctx.send(view=_ok(f"Added {role.mention} to **human** autoroles."))
        else:
            await ctx.send(view=_err(f"{role.mention} is already a human autorole."))

    @humans.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def humans_remove(self, ctx, role: discord.Role):
        await _remove(ctx.guild.id, role.id, "human")
        await ctx.send(view=_ok(f"Removed {role.mention} from human autoroles."))

    @humans.command(name="list", aliases=["show"])
    @commands.has_permissions(administrator=True)
    async def humans_list(self, ctx):
        await ctx.send(view=_list_view("human", await _list(ctx.guild.id, "human"), ctx.guild))

    @autorole.group(name="bots", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def bots(self, ctx):
        await ctx.send(view=_list_view("bot", await _list(ctx.guild.id, "bot"), ctx.guild))

    @bots.command(name="add")
    @commands.has_permissions(administrator=True)
    async def bots_add(self, ctx, role: discord.Role):
        ok = await _add(ctx.guild.id, role.id, "bot")
        if ok:
            await ctx.send(view=_ok(f"Added {role.mention} to **bot** autoroles."))
        else:
            await ctx.send(view=_err(f"{role.mention} is already a bot autorole."))

    @bots.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def bots_remove(self, ctx, role: discord.Role):
        await _remove(ctx.guild.id, role.id, "bot")
        await ctx.send(view=_ok(f"Removed {role.mention} from bot autoroles."))

    @bots.command(name="list", aliases=["show"])
    @commands.has_permissions(administrator=True)
    async def bots_list(self, ctx):
        await ctx.send(view=_list_view("bot", await _list(ctx.guild.id, "bot"), ctx.guild))


async def setup(bot):
    await bot.add_cog(Autorole(bot))
