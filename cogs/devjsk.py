import discord
from discord.ext import commands
from utils.config import OWNER_IDS
from discord import ui
import asyncio
import sys
import os
import time
import platform
import inspect
import traceback
from pathlib import Path
from io import StringIO


try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False


from XEON.emojis import E as _EMGR, FALLBACK_EMOJI
import re as _re

_LOCAL_KEY_MAP = {
    "success": "SUCCESS",
    "error": "ERROR",
    "reload": "RELOAD",
    "info": "INFO",
    "dot": "DOT",
    "bot": "BOT_ICON",
    "stats": "STATS",
    "ping": "PING",
    "ram": "RAM",
    "cpu": "CPU",
    "timer": "CLOCK",
    "python": "PYTHON",
    "discord": "DISCORD_ICO",
    "code": "CODE",
    "terminal": "TERMINAL",
    "db": "DB",
    "shutdown": "SHUTDOWN",
    "user": "USER",
    "channel": "CHANNEL",
    "settings": "SETTINGS",
    "trash": "TRASH",
    "load": "LOAD",
    "unload": "UNLOAD",
}

def E(key: str) -> discord.PartialEmoji:
    s = _EMGR[_LOCAL_KEY_MAP.get(key, key.upper())]
    m = _re.match(r'<(a)?:([A-Za-z0-9_]+):(\d+)>', s)
    if m:
        return discord.PartialEmoji(name=m.group(2), id=int(m.group(3)), animated=bool(m.group(1)))
    return FALLBACK_EMOJI

def ES(key: str) -> str:
    return _EMGR[_LOCAL_KEY_MAP.get(key, key.upper())]


DEFAULT_ACCENT = discord.Colour(0x000000)

DB_DIR = Path("db")
DB_PATH = DB_DIR / "core.db"


def _ensure_db_dir():
    DB_DIR.mkdir(exist_ok=True)


def is_developer():
    async def predicate(ctx):
        return ctx.author.id in OWNER_IDS
    return commands.check(predicate)


def _err(text: str) -> ui.LayoutView:
    v = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('error')} {text}"))
    v.add_item(c)
    return v


def _ok(text: str) -> ui.LayoutView:
    v = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('success')} {text}"))
    v.add_item(c)
    return v


def _info(title: str, body: str, emoji_key: str = "info") -> ui.LayoutView:
    v = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES(emoji_key)} **{title}**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(body))
    v.add_item(c)
    return v


def _code_view(title: str, code: str, lang: str = "py", emoji_key: str = "code") -> ui.LayoutView:
    v = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES(emoji_key)} **{title}**"))
    c.add_item(ui.Separator())
    truncated = code[:3800]
    if len(code) > 3800:
        truncated += f"\n\n... (truncated, {len(code) - 3800} chars more)"
    c.add_item(ui.TextDisplay(f"```{lang}\n{truncated}\n```"))
    v.add_item(c)
    return v


def _help_menu_view(prefix: str) -> ui.LayoutView:
    v = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('settings')} **DevJsk Command List**"))
    c.add_item(ui.Separator())

    c.add_item(ui.TextDisplay(
        f"**{ES('info')} Info & Status**\n"
        f"{ES('dot')} `{prefix}dev botinfo` — Full bot statistics\n"
        f"{ES('dot')} `{prefix}dev ping` — Latency breakdown\n"
        f"{ES('dot')} `{prefix}dev uptime` — Bot uptime\n"
        f"{ES('dot')} `{prefix}dev sys` — System info\n"
        f"{ES('dot')} `{prefix}dev rtt` — Round-trip latency"
    ))
    c.add_item(ui.Separator(visible=False))

    c.add_item(ui.TextDisplay(
        f"**{ES('settings')} Bot Control**\n"
        f"{ES('dot')} `{prefix}dev restart` — Restart bot\n"
        f"{ES('dot')} `{prefix}dev shutdown` — Shut down bot\n"
        f"{ES('dot')} `{prefix}dev setgame <text>` — Change activity\n"
        f"{ES('dot')} `{prefix}dev setstatus <status>` — Change status"
    ))
    c.add_item(ui.Separator(visible=False))

    c.add_item(ui.TextDisplay(
        f"**{ES('load')} Extensions**\n"
        f"{ES('dot')} `{prefix}dev load <ext>` — Load a cog\n"
        f"{ES('dot')} `{prefix}dev unload <ext>` — Unload a cog\n"
        f"{ES('dot')} `{prefix}dev reload <ext|~>` — Reload cog(s)\n"
        f"{ES('dot')} `{prefix}dev listcogs` — List all cogs"
    ))
    c.add_item(ui.Separator(visible=False))

    c.add_item(ui.TextDisplay(
        f"**{ES('python')} Code & Shell**\n"
        f"{ES('dot')} `{prefix}dev py <code>` — Execute Python\n"
        f"{ES('dot')} `{prefix}dev pyi <expr>` — Inspect expression\n"
        f"{ES('dot')} `{prefix}dev sh <cmd>` — Run shell command"
    ))
    c.add_item(ui.Separator(visible=False))

    c.add_item(ui.TextDisplay(
        f"**{ES('db')} Database**\n"
        f"{ES('dot')} `{prefix}dev sql <query>` — Run SQL on core.db\n"
        f"{ES('dot')} `{prefix}dev dbinfo` — List all DB files"
    ))
    c.add_item(ui.Separator(visible=False))

    c.add_item(ui.TextDisplay(
        f"**{ES('discord')} Guild & User Tools**\n"
        f"{ES('dot')} `{prefix}dev guilds` — List all guilds\n"
        f"{ES('dot')} `{prefix}dev guildinfo <id>` — Guild info\n"
        f"{ES('dot')} `{prefix}dev leaveserver <id>` — Leave guild\n"
        f"{ES('dot')} `{prefix}dev userinfo <id>` — User lookup\n"
        f"{ES('dot')} `{prefix}dev dm <id> <msg>` — DM any user\n"
        f"{ES('dot')} `{prefix}dev announce <msg>` — DM all owners\n"
        f"{ES('dot')} `{prefix}dev blacklist <id>` — Blacklist user\n"
        f"{ES('dot')} `{prefix}dev unblacklist <id>` — Remove blacklist"
    ))
    c.add_item(ui.Separator(visible=False))

    c.add_item(ui.TextDisplay(
        f"**{ES('terminal')} Misc**\n"
        f"{ES('dot')} `{prefix}dev clearcache` — Clear cache\n"
        f"{ES('dot')} `{prefix}dev tasks` — View asyncio tasks\n"
        f"{ES('dot')} `{prefix}dev cancel <id>` — Cancel a task\n"
        f"{ES('dot')} `{prefix}dev source <cmd>` — Show command source\n"
        f"{ES('dot')} `{prefix}dev sync` — Sync slash commands\n"
        f"{ES('dot')} `{prefix}dev sudo @user <cmd>` — Run cmd as user"
    ))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay("-# Owner only • All commands require dev ID"))

    v.add_item(c)
    return v


class DevJsk(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_result = None
        _ensure_db_dir()


    def cleanup_code(self, content: str) -> str:
        if content.startswith("```") and content.endswith("```"):
            content = "\n".join(content.split("\n")[1:-1])
        return content.strip("`\n ")

    async def send_long(self, ctx, title: str, text: str, lang: str = "py", emoji_key: str = "code"):
        chunks = [text[i:i + 3800] for i in range(0, len(text), 3800)]
        for i, chunk in enumerate(chunks, 1):
            t = title if len(chunks) == 1 else f"{title} ({i}/{len(chunks)})"
            await ctx.send(view=_code_view(t, chunk, lang, emoji_key))


    @commands.command(name="devjsk")
    @is_developer()
    async def devjsk(self, ctx):
        await ctx.send(view=_help_menu_view(ctx.prefix))

    @commands.group(name="dev", invoke_without_command=True)
    @is_developer()
    async def dev(self, ctx):
        await ctx.invoke(self.devjsk)


    @dev.command(name="py", aliases=["eval"])
    @is_developer()
    async def dev_py(self, ctx, *, code: str):
        code = self.cleanup_code(code)
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "guild": ctx.guild,
            "channel": ctx.channel,
            "author": ctx.author,
            "message": ctx.message,
            "_": self._last_result,
            "discord": discord,
            "commands": commands,
            "asyncio": asyncio,
        }

        stdout = StringIO()
        to_compile = f"async def __exec():\n" + "\n".join(f"  {l}" for l in code.splitlines())

        try:
            exec(compile(to_compile, "<dev>", "exec"), env)
        except SyntaxError as e:
            return await ctx.send(view=_code_view("Syntax Error", str(e), "py", "error"))

        func = env["__exec"]
        try:
            import contextlib
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            return await self.send_long(ctx, "Exception", f"{value}{traceback.format_exc()}", "py", "error")

        value = stdout.getvalue()
        if ret is not None:
            self._last_result = ret
            result = f"{value}{ret}"
        else:
            result = value or "Executed (no output)"

        await self.send_long(ctx, "Python Output", result, "py", "python")

    @dev.command(name="pyi")
    @is_developer()
    async def dev_pyi(self, ctx, *, code: str):
        code = self.cleanup_code(code)
        env = {"bot": self.bot, "ctx": ctx, "guild": ctx.guild, "_": self._last_result}
        try:
            result = eval(code, env)
            output = (
                f"Type    : {type(result).__name__}\n"
                f"Value   : {result!r}\n"
                f"Module  : {getattr(type(result), '__module__', 'N/A')}\n"
                f"MRO     : {[c.__name__ for c in type(result).__mro__]}"
            )
            await ctx.send(view=_code_view("Inspect", output, "py", "python"))
        except Exception:
            await ctx.send(view=_code_view("Error", traceback.format_exc(), "py", "error"))

    @dev.command(name="sh")
    @is_developer()
    async def dev_sh(self, ctx, *, cmd: str):
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            output = (stdout.decode() + stderr.decode()).strip() or "No output"
            await self.send_long(ctx, f"Shell: {cmd[:40]}", output, "sh", "terminal")
        except asyncio.TimeoutError:
            await ctx.send(view=_err("Command timed out (30s)."))
        except Exception as e:
            await ctx.send(view=_err(f"Error: `{e}`"))


    @dev.command(name="botinfo")
    @is_developer()
    async def dev_botinfo(self, ctx):
        if not HAS_PSUTIL:
            return await ctx.send(view=_err("`psutil` not installed. Run: `pip install psutil`"))

        proc = psutil.Process()
        mem = proc.memory_info().rss / 1024 ** 2
        cpu = psutil.cpu_percent(interval=0.5)
        uptime_s = int(time.time() - proc.create_time())
        h, r = divmod(uptime_s, 3600)
        m, s = divmod(r, 60)

        total_members = sum(g.member_count or 0 for g in self.bot.guilds)
        text_channels = sum(len(g.text_channels) for g in self.bot.guilds)
        voice_channels = sum(len(g.voice_channels) for g in self.bot.guilds)

        v = ui.LayoutView()
        c = ui.Container(accent_color=DEFAULT_ACCENT)

        header = ui.TextDisplay(f"{ES('bot')} **Bot Statistics**")
        if self.bot.user.avatar:
            c.add_item(ui.Section(header, accessory=ui.Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url))))
        else:
            c.add_item(header)

        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"{ES('bot')} **Bot:** `{self.bot.user}`\n"
            f"{ES('dot')} **ID:** `{self.bot.user.id}`"
        ))
        c.add_item(ui.Separator(visible=False))

        c.add_item(ui.TextDisplay(
            f"**{ES('stats')} Stats**\n"
            f"{ES('dot')} **Guilds:** `{len(self.bot.guilds)}`\n"
            f"{ES('dot')} **Members:** `{total_members:,}`\n"
            f"{ES('dot')} **Text Channels:** `{text_channels}`\n"
            f"{ES('dot')} **Voice Channels:** `{voice_channels}`\n"
            f"{ES('dot')} **Commands:** `{len(self.bot.commands)}`\n"
            f"{ES('dot')} **Cogs:** `{len(self.bot.cogs)}`"
        ))
        c.add_item(ui.Separator(visible=False))

        c.add_item(ui.TextDisplay(
            f"**{ES('cpu')} Performance**\n"
            f"{ES('ping')} **Latency:** `{round(self.bot.latency * 1000)}ms`\n"
            f"{ES('timer')} **Uptime:** `{h}h {m}m {s}s`\n"
            f"{ES('ram')} **RAM:** `{mem:.1f} MB`\n"
            f"{ES('cpu')} **CPU:** `{cpu}%`"
        ))
        c.add_item(ui.Separator(visible=False))

        c.add_item(ui.TextDisplay(
            f"**{ES('code')} Versions**\n"
            f"{ES('python')} **Python:** `{sys.version.split()[0]}`\n"
            f"{ES('discord')} **discord.py:** `{discord.__version__}`"
        ))

        v.add_item(c)
        await ctx.send(view=v)

    @dev.command(name="ping")
    @is_developer()
    async def dev_ping(self, ctx):
        ws = round(self.bot.latency * 1000)
        t1 = time.perf_counter()
        msg = await ctx.send(view=_info("Ping", "Measuring...", "ping"))
        rest = round((time.perf_counter() - t1) * 1000)

        v = ui.LayoutView()
        c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('ping')} **Pong!**"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"{ES('dot')} **Websocket:** `{ws}ms`\n"
            f"{ES('dot')} **REST:** `{rest}ms`"
        ))
        v.add_item(c)
        await msg.edit(view=v)

    @dev.command(name="uptime")
    @is_developer()
    async def dev_uptime(self, ctx):
        if not HAS_PSUTIL:
            return await ctx.send(view=_err("`psutil` not installed."))
        proc = psutil.Process()
        uptime_s = int(time.time() - proc.create_time())
        h, r = divmod(uptime_s, 3600)
        m, s = divmod(r, 60)
        d, h = divmod(h, 24)
        await ctx.send(view=_info("Uptime", f"`{d}d {h}h {m}m {s}s`", "timer"))

    @dev.command(name="sys")
    @is_developer()
    async def dev_sys(self, ctx):
        if not HAS_PSUTIL:
            return await ctx.send(view=_err("`psutil` not installed."))

        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        v = ui.LayoutView()
        c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('cpu')} **System Information**"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"{ES('dot')} **OS:** `{platform.system()} {platform.release()}`\n"
            f"{ES('cpu')} **CPU:** `{psutil.cpu_percent()}%` ({psutil.cpu_count()} cores)\n"
            f"{ES('ram')} **RAM:** `{mem.used / 1024 ** 2:.0f}/{mem.total / 1024 ** 2:.0f} MB` ({mem.percent}%)\n"
            f"{ES('db')} **Disk:** `{disk.used / 1024 ** 3:.1f}/{disk.total / 1024 ** 3:.1f} GB` ({disk.percent}%)\n"
            f"{ES('python')} **Python:** `{sys.version.split()[0]}`\n"
            f"{ES('dot')} **PID:** `{os.getpid()}`"
        ))
        v.add_item(c)
        await ctx.send(view=v)

    @dev.command(name="rtt")
    @is_developer()
    async def dev_rtt(self, ctx):
        results = []
        msg = await ctx.send(view=_info("RTT", "Measuring...", "ping"))
        for i in range(5):
            t = time.perf_counter()
            await msg.edit(view=_info("RTT", f"Sample {i + 1}/5...", "ping"))
            results.append(round((time.perf_counter() - t) * 1000))
            await asyncio.sleep(0.3)
        avg = sum(results) / len(results)

        v = ui.LayoutView()
        c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('ping')} **RTT Results**"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"{ES('dot')} **Samples:** `{results}`\n"
            f"{ES('dot')} **Average:** `{avg:.1f}ms`\n"
            f"{ES('dot')} **Min/Max:** `{min(results)}ms` / `{max(results)}ms`"
        ))
        v.add_item(c)
        await msg.edit(view=v)


    @dev.command(name="restart")
    @is_developer()
    async def dev_restart(self, ctx):
        await ctx.send(view=_info("Restarting", f"{ES('reload')} Bot is restarting...", "reload"))
        await self.bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @dev.command(name="shutdown")
    @is_developer()
    async def dev_shutdown(self, ctx):
        await ctx.send(view=_info("Shutting Down", f"{ES('shutdown')} Goodbye.", "shutdown"))
        await self.bot.close()

    @dev.command(name="setgame")
    @is_developer()
    async def dev_setgame(self, ctx, *, text: str):
        await self.bot.change_presence(activity=discord.CustomActivity(name=text))
        await ctx.send(view=_ok(f"Activity set to: `{text}`"))

    @dev.command(name="setstatus")
    @is_developer()
    async def dev_setstatus(self, ctx, status: str):
        statuses = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invis": discord.Status.invisible,
            "invisible": discord.Status.invisible,
        }
        s = statuses.get(status.lower())
        if not s:
            return await ctx.send(view=_err(f"Unknown status. Use: `{', '.join(statuses)}`"))
        await self.bot.change_presence(status=s)
        await ctx.send(view=_ok(f"Status set to `{status}`"))


    @dev.command(name="load")
    @is_developer()
    async def dev_load(self, ctx, *, ext: str):
        try:
            await self.bot.load_extension(ext)
            await ctx.send(view=_ok(f"Loaded `{ext}`"))
        except Exception as e:
            await ctx.send(view=_err(f"`{ext}`: `{e}`"))

    @dev.command(name="unload")
    @is_developer()
    async def dev_unload(self, ctx, *, ext: str):
        try:
            await self.bot.unload_extension(ext)
            await ctx.send(view=_ok(f"Unloaded `{ext}`"))
        except Exception as e:
            await ctx.send(view=_err(f"`{ext}`: `{e}`"))

    @dev.command(name="reload")
    @is_developer()
    async def dev_reload(self, ctx, *, ext: str = "~"):
        if ext == "~":
            loaded = list(self.bot.extensions.keys())
            ok, fail = [], []
            for e in loaded:
                try:
                    await self.bot.reload_extension(e)
                    ok.append(e)
                except Exception as err:
                    fail.append(f"{e}: {err}")

            v = ui.LayoutView()
            c = ui.Container(accent_color=DEFAULT_ACCENT)
            c.add_item(ui.TextDisplay(f"{ES('reload')} **Reload All Cogs**"))
            c.add_item(ui.Separator())
            c.add_item(ui.TextDisplay(f"{ES('success')} **Reloaded:** `{len(ok)}`"))
            if fail:
                c.add_item(ui.Separator(visible=False))
                fail_text = "\n".join(f"{ES('error')} `{f}`" for f in fail[:10])
                c.add_item(ui.TextDisplay(f"**Failed:**\n{fail_text}"))
            v.add_item(c)
            await ctx.send(view=v)
        else:
            try:
                await self.bot.reload_extension(ext)
                await ctx.send(view=_ok(f"{ES('reload')} Reloaded `{ext}`"))
            except Exception as e:
                await ctx.send(view=_err(f"`{ext}`: `{e}`"))

    @dev.command(name="listcogs")
    @is_developer()
    async def dev_listcogs(self, ctx):
        loaded = set(self.bot.extensions.keys())
        files = set(
            f"cogs.{p.stem}"
            for p in Path("cogs").glob("*.py")
            if not p.name.startswith("_")
        )
        unloaded = files - loaded

        v = ui.LayoutView()
        c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('load')} **Cog Status**"))
        c.add_item(ui.Separator())

        if loaded:
            loaded_text = "\n".join(f"{ES('success')} `{e}`" for e in sorted(loaded))
            c.add_item(ui.TextDisplay(f"**Loaded ({len(loaded)}):**\n{loaded_text}"))

        if unloaded:
            c.add_item(ui.Separator(visible=False))
            unloaded_text = "\n".join(f"{ES('error')} `{e}`" for e in sorted(unloaded))
            c.add_item(ui.TextDisplay(f"**Unloaded ({len(unloaded)}):**\n{unloaded_text}"))

        v.add_item(c)
        await ctx.send(view=v)


    @dev.command(name="sql")
    @is_developer()
    async def dev_sql(self, ctx, *, query: str):
        if not HAS_AIOSQLITE:
            return await ctx.send(view=_err("`aiosqlite` not installed."))
        _ensure_db_dir()
        try:
            async with aiosqlite.connect(str(DB_PATH)) as db:
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchmany(20)
                    if cursor.description:
                        headers = [d[0] for d in cursor.description]
                        lines = [" | ".join(headers)]
                        lines += ["-" * len(lines[0])]
                        lines += [" | ".join(str(v) for v in row) for row in rows]
                        result = "\n".join(lines) or "No rows returned."
                    else:
                        await db.commit()
                        result = f"Query OK. Rows affected: {cursor.rowcount}"
            await self.send_long(ctx, "SQL Result", result, "", "db")
        except Exception as e:
            await ctx.send(view=_err(f"SQL Error: `{e}`"))

    @dev.command(name="dbinfo")
    @is_developer()
    async def dev_dbinfo(self, ctx):
        if not DB_DIR.exists():
            return await ctx.send(view=_err("No `db/` directory found."))

        files = sorted(DB_DIR.glob("*.db"))
        if not files:
            return await ctx.send(view=_err("No databases found."))

        v = ui.LayoutView()
        c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('db')} **Databases**"))
        c.add_item(ui.Separator())
        lines = []
        for f in files:
            size = f.stat().st_size / 1024
            lines.append(f"{ES('dot')} `{f.name}` — `{size:.1f} KB`")
        c.add_item(ui.TextDisplay("\n".join(lines)))
        v.add_item(c)
        await ctx.send(view=v)


    @dev.command(name="guilds")
    @is_developer()
    async def dev_guilds(self, ctx):
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        v = ui.LayoutView()
        c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('discord')} **Guilds [{len(guilds)}]**"))
        c.add_item(ui.Separator())

        lines = []
        for g in guilds[:25]:
            lines.append(f"{ES('dot')} `{g.id}` — **{g.name}** ({g.member_count})")
        if len(guilds) > 25:
            lines.append(f"\n-# ... and {len(guilds) - 25} more")
        c.add_item(ui.TextDisplay("\n".join(lines)))

        v.add_item(c)
        await ctx.send(view=v)

    @dev.command(name="guildinfo")
    @is_developer()
    async def dev_guildinfo(self, ctx, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send(view=_err(f"Guild `{guild_id}` not found."))

        v = ui.LayoutView()
        c = ui.Container(accent_color=DEFAULT_ACCENT)

        header = ui.TextDisplay(f"{ES('discord')} **{guild.name}**")
        if guild.icon:
            c.add_item(ui.Section(header, accessory=ui.Thumbnail(
                media=discord.UnfurledMediaItem(url=guild.icon.url))))
        else:
            c.add_item(header)

        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"{ES('dot')} **ID:** `{guild.id}`\n"
            f"{ES('user')} **Owner:** `{guild.owner}` (`{guild.owner_id}`)\n"
            f"{ES('stats')} **Members:** `{guild.member_count}`\n"
            f"{ES('channel')} **Channels:** Text `{len(guild.text_channels)}` | Voice `{len(guild.voice_channels)}`\n"
            f"{ES('dot')} **Roles:** `{len(guild.roles)}`\n"
            f"{ES('dot')} **Boosts:** `{guild.premium_subscription_count}`\n"
            f"{ES('timer')} **Created:** <t:{int(guild.created_at.timestamp())}:R>"
        ))
        v.add_item(c)
        await ctx.send(view=v)

    @dev.command(name="leaveserver")
    @is_developer()
    async def dev_leaveserver(self, ctx, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send(view=_err(f"Guild `{guild_id}` not found."))
        await guild.leave()
        await ctx.send(view=_ok(f"Left guild `{guild.name}` (`{guild_id}`)"))

    @dev.command(name="announce")
    @is_developer()
    async def dev_announce(self, ctx, *, message: str):
        ok, fail = 0, 0
        for guild in self.bot.guilds:
            try:
                if guild.owner:
                    v = ui.LayoutView()
                    c = ui.Container(accent_color=DEFAULT_ACCENT)
                    c.add_item(ui.TextDisplay(f"{ES('info')} **Announcement from {self.bot.user.name}**"))
                    c.add_item(ui.Separator())
                    c.add_item(ui.TextDisplay(message))
                    v.add_item(c)
                    await guild.owner.send(view=v)
                    ok += 1
                    await asyncio.sleep(0.5)
            except Exception:
                fail += 1

        await ctx.send(view=_info("Announcement Sent", f"{ES('success')} Sent to `{ok}` owners\n{ES('error')} Failed: `{fail}`", "info"))


    @dev.command(name="userinfo")
    @is_developer()
    async def dev_userinfo(self, ctx, user_id: int):
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            return await ctx.send(view=_err(f"User `{user_id}` not found."))

        v = ui.LayoutView()
        c = ui.Container(accent_color=DEFAULT_ACCENT)

        header = ui.TextDisplay(f"{ES('user')} **{user}**")
        if user.avatar:
            c.add_item(ui.Section(header, accessory=ui.Thumbnail(
                media=discord.UnfurledMediaItem(url=user.display_avatar.url))))
        else:
            c.add_item(header)

        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            f"{ES('dot')} **ID:** `{user.id}`\n"
            f"{ES('bot')} **Bot:** `{user.bot}`\n"
            f"{ES('timer')} **Created:** <t:{int(user.created_at.timestamp())}:R>"
        ))
        v.add_item(c)
        await ctx.send(view=v)

    @dev.command(name="dm")
    @is_developer()
    async def dev_dm(self, ctx, user_id: int, *, message: str):
        try:
            user = await self.bot.fetch_user(user_id)
            v = ui.LayoutView()
            c = ui.Container(accent_color=DEFAULT_ACCENT)
            c.add_item(ui.TextDisplay(f"{ES('info')} **Message from {self.bot.user.name}**"))
            c.add_item(ui.Separator())
            c.add_item(ui.TextDisplay(message))
            v.add_item(c)
            await user.send(view=v)
            await ctx.send(view=_ok(f"DM sent to `{user}` (`{user_id}`)"))
        except Exception as e:
            await ctx.send(view=_err(f"Failed: `{e}`"))

    @dev.command(name="blacklist")
    @is_developer()
    async def dev_blacklist(self, ctx, user_id: int):
        if not HAS_AIOSQLITE:
            return await ctx.send(view=_err("`aiosqlite` not installed."))
        _ensure_db_dir()
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS blacklisted (user_id INTEGER PRIMARY KEY)")
            await db.execute("INSERT OR IGNORE INTO blacklisted VALUES (?)", (user_id,))
            await db.commit()
        await ctx.send(view=_ok(f"{ES('trash')} User `{user_id}` blacklisted."))

    @dev.command(name="unblacklist")
    @is_developer()
    async def dev_unblacklist(self, ctx, user_id: int):
        if not HAS_AIOSQLITE:
            return await ctx.send(view=_err("`aiosqlite` not installed."))
        _ensure_db_dir()
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("DELETE FROM blacklisted WHERE user_id = ?", (user_id,))
            await db.commit()
        await ctx.send(view=_ok(f"User `{user_id}` removed from blacklist."))


    @dev.command(name="clearcache")
    @is_developer()
    async def dev_clearcache(self, ctx):
        self.bot._connection._messages.clear()
        await ctx.send(view=_ok("Message cache cleared."))

    @dev.command(name="tasks")
    @is_developer()
    async def dev_tasks(self, ctx):
        tasks = asyncio.all_tasks()
        v = ui.LayoutView()
        c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('terminal')} **Active Tasks [{len(tasks)}]**"))
        c.add_item(ui.Separator())

        if not tasks:
            c.add_item(ui.TextDisplay("-# No tasks running."))
        else:
            lines = []
            for i, task in enumerate(list(tasks)[:30], 1):
                name = task.get_name()
                status = ES("success") if task.done() else ES("reload")
                lines.append(f"`{i:02d}` {status} `{name}`")
            c.add_item(ui.TextDisplay("\n".join(lines)))
            if len(tasks) > 30:
                c.add_item(ui.Separator(visible=False))
                c.add_item(ui.TextDisplay(f"-# ... and {len(tasks) - 30} more"))

        v.add_item(c)
        await ctx.send(view=v)

    @dev.command(name="cancel")
    @is_developer()
    async def dev_cancel(self, ctx, task_id: int):
        tasks = list(asyncio.all_tasks())
        if task_id < 1 or task_id > len(tasks):
            return await ctx.send(view=_err(f"Invalid task ID. Use `dev tasks` to list."))
        task = tasks[task_id - 1]
        task.cancel()
        await ctx.send(view=_ok(f"Cancelled task `{task.get_name()}`"))


    @dev.command(name="source")
    @is_developer()
    async def dev_source(self, ctx, *, cmd_name: str):
        cmd = self.bot.get_command(cmd_name)
        if not cmd:
            return await ctx.send(view=_err(f"Command `{cmd_name}` not found."))
        try:
            source = inspect.getsource(cmd.callback)
            await self.send_long(ctx, f"Source: {cmd_name}", source, "py", "code")
        except Exception as e:
            await ctx.send(view=_err(f"Could not get source: `{e}`"))

    @dev.command(name="sync")
    @is_developer()
    async def dev_sync(self, ctx):
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(view=_ok(f"Synced `{len(synced)}` slash commands globally."))
        except Exception as e:
            await ctx.send(view=_err(f"Sync failed: `{e}`"))

    @dev.command(name="sudo")
    @is_developer()
    async def dev_sudo(self, ctx, member: discord.Member, *, cmd: str):
        msg = ctx.message
        msg.author = member
        msg.content = ctx.prefix + cmd
        new_ctx = await self.bot.get_context(msg)
        try:
            await self.bot.invoke(new_ctx)
        except Exception as e:
            await ctx.send(view=_err(f"Sudo failed: `{e}`"))


async def setup(bot: commands.Bot):
    await bot.add_cog(DevJsk(bot))
