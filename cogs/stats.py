import discord
from discord.ext import commands
import psutil
import platform
import time
import json
import os

from utils.ui import stats_paged_container, info_container, denied_container
from utils import emojis as E

CONFIG_PATH = "data/stats_config.json"

DEFAULT_CONFIG = {
    "team": {
        "Owner":     [],
        "Developer": [],
        "Staff":     [],
    },
    "partners": [None, None, None, None, None],
}


def _load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH) as f:
        data = json.load(f)
    for k, v in DEFAULT_CONFIG.items():
        data.setdefault(k, v)
    for role in ("Owner", "Developer", "Staff"):
        data["team"].setdefault(role, [])
    while len(data["partners"]) < 5:
        data["partners"].append(None)
    return data


def _save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


class Stats(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.config = _load_config()

    def _uptime(self) -> str:
        s = int(time.time() - self.bot.start_time)
        d, s = divmod(s, 86400)
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        return f"{d}d {h}h {m}m {s}s"

    @staticmethod
    def _fmt(n: int) -> str:
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.1f}K"
        return str(n)

    def _build_bot_info(self, ctx) -> str:
        total_users    = sum(g.member_count for g in self.bot.guilds)
        total_guilds   = len(self.bot.guilds)
        total_channels = sum(len(g.channels) for g in self.bot.guilds)
        uptime         = self._uptime()
        ws_ms          = round(self.bot.latency * 1000)

        proc      = psutil.Process()
        mem_mb    = proc.memory_info().rss / 1024 / 1024
        cpu_pct   = psutil.cpu_percent(interval=0.1)
        py_ver    = platform.python_version()
        dpy_ver   = discord.__version__
        shards    = self.bot.shard_count or 1
        cur_shard = getattr(ctx.guild, "shard_id", 0) if ctx.guild else 0
        total_cmd = len(list(self.bot.walk_commands()))
        os_str    = f"{platform.system()} {platform.release()}"

        body = (
            f"### {E.INFO}  General\n"
            f"> {E.INFO} **Servers :** `{self._fmt(total_guilds)}`\n"
            f"> {E.INFO} **Users :** `{self._fmt(total_users)}`\n"
            f"> {E.INFO} **Channels :** `{self._fmt(total_channels)}`\n"
            f"> {E.INFO} **Commands :** `{total_cmd}`\n"
            f"\n"
            f"### {E.SYSTEM}  System\n"
            f"> {E.CPU} **CPU :** `{cpu_pct}%`\n"
            f"> {E.MEMORY} **RAM :** `{mem_mb:.1f} MB`\n"
            f"> {E.INFO} **OS :** `{os_str}`\n"
            f"> {E.INFO} **Python :** `{py_ver}`\n"
            f"> {E.INFO} **discord.py :** `{dpy_ver}`\n"
            f"\n"
            f"### {E.UPTIME}  Runtime\n"
            f"> {E.PING} **Latency :** `{ws_ms} ms`\n"
            f"> {E.SHARD_OK} **Shard :** `{cur_shard}/{shards}`\n"
            f"> {E.UPTIME} **Uptime :** `{uptime}`"
        )
        return body

    def _build_team_data(self) -> dict:
        out = {}
        for role in ("Owner", "Developer", "Staff"):
            members = self.config["team"].get(role, [])
            normalized = []
            for m in members:
                if len(m) == 2:
                    name, uid = m
                    normalized.append((name, name, uid))
                elif len(m) >= 3:
                    normalized.append((m[0], m[1], m[2]))
            out[role] = normalized
        return out

    async def _build_partners_data(self) -> list:
        partners = []
        for slot in self.config["partners"]:
            if not slot:
                continue
            gid     = slot.get("guild_id")
            name    = slot.get("name", "Unknown Server")
            invite  = slot.get("invite", "")
            members = slot.get("members", 0)

            guild = self.bot.get_guild(gid) if gid else None
            if guild:
                members = guild.member_count
                if not name or name == "Unknown Server":
                    name = guild.name

            partners.append((name, invite, members))
        return partners

    @commands.command(name="stats", aliases=["botstats", "botinfo", "bi"])
    async def stats(self, ctx):
        await ctx.typing()

        bot_info_body = self._build_bot_info(ctx)
        team_data     = self._build_team_data()
        partners_data = await self._build_partners_data()

        view = stats_paged_container(
            author_id     = ctx.author.id,
            bot_name      = self.bot.BOT_NAME,
            bot_avatar    = self.bot.user.display_avatar.url,
            invite_url    = getattr(self.bot, "INVITE_URL", self.bot.SUPPORT_SERVER),
            support_url   = self.bot.SUPPORT_SERVER,
            bot_info_body = bot_info_body,
            team_data     = team_data,
            partners_data = partners_data,
        )
        await ctx.send(view=view)

    @commands.command(name="uptime", aliases=["up"])
    async def uptime(self, ctx):
        kwargs = info_container(
            f"Uptime {E.UPTIME}",
            f"`{self._uptime()}`",
        )
        await ctx.send(**kwargs)

    @commands.command(name="system", aliases=["sys"])
    async def system(self, ctx):
        proc    = psutil.Process()
        mem_mb  = proc.memory_info().rss / 1024 / 1024
        cpu_pct = psutil.cpu_percent(interval=0.5)

        body = (
            f"{E.CPU} **CPU :** `{cpu_pct}%`\n"
            f"{E.MEMORY} **RAM :** `{mem_mb:.1f} MB`\n"
            f"{E.INFO} **OS :** `{platform.system()} {platform.release()}`\n"
            f"{E.INFO} **Python :** `{platform.python_version()}`\n"
            f"{E.INFO} **discord.py :** `{discord.__version__}`"
        )
        kwargs = info_container(f"{E.SYSTEM} System Info", body)
        await ctx.send(**kwargs)

    @commands.group(name="team", invoke_without_command=True)
    @commands.is_owner()
    async def team_grp(self, ctx):
        kwargs = info_container(
            f"{E.INFO} Team Management",
            (
                f"Use:\n"
                f"> `{ctx.prefix}team owner @user` — add to Owner\n"
                f"> `{ctx.prefix}team developer @user` — add to Developer\n"
                f"> `{ctx.prefix}team staff @user` — add to Staff\n"
                f"> `{ctx.prefix}team remove @user [role]` — remove from a role (or all)\n\n"
                f"Note: A user can be in **multiple roles** at the same time."
            ),
        )
        await ctx.send(**kwargs)

    async def _team_add(self, ctx, role: str, user: discord.User):
        display_name = getattr(user, "global_name", None) or user.display_name or user.name
        username     = user.name

        existing = self.config["team"].setdefault(role, [])
        for m in existing:
            uid = m[2] if len(m) >= 3 else m[1]
            if uid == user.id:
                return await ctx.send(
                    **denied_container(f"{user.mention} is already in **{role}**.")
                )

        existing.append([display_name, username, user.id])
        _save_config(self.config)

        kwargs = info_container(
            f"{E.SUCCESS} Team Updated",
            f"Added {user.mention} as **{role}**.",
        )
        await ctx.send(**kwargs)

    @team_grp.command(name="owner")
    @commands.is_owner()
    async def team_owner(self, ctx, user: discord.User):
        await self._team_add(ctx, "Owner", user)

    @team_grp.command(name="developer", aliases=["dev"])
    @commands.is_owner()
    async def team_dev(self, ctx, user: discord.User):
        await self._team_add(ctx, "Developer", user)

    @team_grp.command(name="staff")
    @commands.is_owner()
    async def team_staff(self, ctx, user: discord.User):
        await self._team_add(ctx, "Staff", user)

    @team_grp.command(name="remove", aliases=["rm", "delete"])
    @commands.is_owner()
    async def team_remove(self, ctx, user: discord.User, *, role: str = None):
        if role:
            role = role.capitalize()
            if role not in ("Owner", "Developer", "Staff"):
                return await ctx.send(
                    **denied_container("Role must be `owner`, `developer`, or `staff`.")
                )
            before = len(self.config["team"].get(role, []))
            self.config["team"][role] = [
                m for m in self.config["team"].get(role, [])
                if (m[2] if len(m) >= 3 else m[1]) != user.id
            ]
            if len(self.config["team"][role]) < before:
                _save_config(self.config)
                kwargs = info_container(
                    f"{E.SUCCESS} Team Updated",
                    f"Removed {user.mention} from **{role}**.",
                )
            else:
                kwargs = denied_container(f"{user.mention} is not in **{role}**.")
            return await ctx.send(**kwargs)

        removed_from = []
        for r in ("Owner", "Developer", "Staff"):
            before = len(self.config["team"].get(r, []))
            self.config["team"][r] = [
                m for m in self.config["team"].get(r, [])
                if (m[2] if len(m) >= 3 else m[1]) != user.id
            ]
            if len(self.config["team"][r]) < before:
                removed_from.append(r)
        if removed_from:
            _save_config(self.config)
            kwargs = info_container(
                f"{E.SUCCESS} Team Updated",
                f"Removed {user.mention} from: **{', '.join(removed_from)}**.",
            )
        else:
            kwargs = denied_container(f"{user.mention} is not in the team.")
        await ctx.send(**kwargs)

    @commands.group(name="partner", invoke_without_command=True)
    @commands.is_owner()
    async def partner_grp(self, ctx, place: int = None, guild_id: int = None):
        if place is None or guild_id is None:
            kwargs = info_container(
                f"{E.INFO} Partner Management",
                (
                    f"Use:\n"
                    f"> `{ctx.prefix}partner <1-5> <guild_id>` — set partner\n"
                    f"> `{ctx.prefix}partner remove <1-5>` — remove partner\n"
                    f"> `{ctx.prefix}partner setinvite <1-5> <invite_url>` — set invite link\n"
                    f"> `{ctx.prefix}partner setname <1-5> <name>` — set custom name"
                ),
            )
            return await ctx.send(**kwargs)

        if not (1 <= place <= 5):
            return await ctx.send(**denied_container("Place must be between **1** and **5**."))

        guild = self.bot.get_guild(guild_id)
        name  = guild.name if guild else f"Server {guild_id}"
        members = guild.member_count if guild else 0

        invite_url = ""
        if guild:
            try:
                invites = await guild.invites()
                if invites:
                    invite_url = invites[0].url
                else:
                    sys_ch = guild.system_channel or next(
                        (c for c in guild.text_channels if c.permissions_for(guild.me).create_instant_invite),
                        None
                    )
                    if sys_ch:
                        inv = await sys_ch.create_invite(max_age=0, max_uses=0, reason="Partner link")
                        invite_url = inv.url
            except Exception:
                pass

        self.config["partners"][place - 1] = {
            "guild_id": guild_id,
            "name":     name,
            "invite":   invite_url,
            "members":  members,
        }
        _save_config(self.config)

        kwargs = info_container(
            f"{E.SUCCESS} Partner Set",
            (
                f"**Slot {place}** updated:\n"
                f"> **Name :** {name}\n"
                f"> **Members :** {members}\n"
                f"> **Invite :** {invite_url or '`(not set — use setinvite)`'}"
            ),
        )
        await ctx.send(**kwargs)

    @partner_grp.command(name="remove", aliases=["rm", "delete"])
    @commands.is_owner()
    async def partner_remove(self, ctx, place: int):
        if not (1 <= place <= 5):
            return await ctx.send(**denied_container("Place must be between **1** and **5**."))
        if not self.config["partners"][place - 1]:
            return await ctx.send(**denied_container(f"Slot **{place}** is already empty."))
        self.config["partners"][place - 1] = None
        _save_config(self.config)
        kwargs = info_container(
            f"{E.SUCCESS} Partner Removed",
            f"Cleared **Slot {place}**.",
        )
        await ctx.send(**kwargs)

    @partner_grp.command(name="setinvite", aliases=["invite"])
    @commands.is_owner()
    async def partner_setinvite(self, ctx, place: int, *, invite_url: str):
        if not (1 <= place <= 5):
            return await ctx.send(**denied_container("Place must be between **1** and **5**."))
        if not self.config["partners"][place - 1]:
            return await ctx.send(**denied_container(f"Slot **{place}** is empty. Set a partner first."))
        self.config["partners"][place - 1]["invite"] = invite_url
        _save_config(self.config)
        kwargs = info_container(
            f"{E.SUCCESS} Invite Updated",
            f"Invite for **Slot {place}** set to:\n{invite_url}",
        )
        await ctx.send(**kwargs)

    @partner_grp.command(name="setname", aliases=["name"])
    @commands.is_owner()
    async def partner_setname(self, ctx, place: int, *, name: str):
        if not (1 <= place <= 5):
            return await ctx.send(**denied_container("Place must be between **1** and **5**."))
        if not self.config["partners"][place - 1]:
            return await ctx.send(**denied_container(f"Slot **{place}** is empty. Set a partner first."))
        self.config["partners"][place - 1]["name"] = name
        _save_config(self.config)
        kwargs = info_container(
            f"{E.SUCCESS} Name Updated",
            f"Name for **Slot {place}** set to: **{name}**",
        )
        await ctx.send(**kwargs)


async def setup(bot):
    await bot.add_cog(Stats(bot))
