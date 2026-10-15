import discord
from discord.ext import commands
from discord.ui import (
    LayoutView, Container, Section, TextDisplay,
    Separator, Thumbnail
)
import asyncio
import time
from collections import defaultdict

from .antinuke_core import (
    ACCENT_COLOR, OWNER_IDS, E, DBManager,
    is_whitelisted, is_filter_enabled,
    get_punishment, get_log_channel, SECURITY_ROLE_NAME
)


async def execute_punishment(
    guild: discord.Guild,
    offender: discord.Member,
    punishment: str,
    reason: str
):
    try:
        if punishment == "ban":
            await guild.ban(offender, reason=f"[Antinuke] {reason}", delete_message_days=0)
        elif punishment == "kick":
            await offender.kick(reason=f"[Antinuke] {reason}")
        elif punishment == "stripstaff":
            dangerous = discord.Permissions(
                administrator=True, ban_members=True, kick_members=True,
                manage_guild=True, manage_roles=True, manage_channels=True,
                manage_webhooks=True, mention_everyone=True,
                manage_messages=True, manage_threads=True
            )
            roles_to_remove = [
                r for r in offender.roles
                if r != guild.default_role and (
                    r.permissions.value & dangerous.value
                )
            ]
            for role in roles_to_remove:
                try:
                    await offender.remove_roles(role, reason=f"[Antinuke StripStaff] {reason}")
                    await asyncio.sleep(0.3)
                except (discord.Forbidden, discord.HTTPException):
                    pass
    except (discord.Forbidden, discord.HTTPException):
        pass


async def send_log(bot, guild, action: str, offender, reason: str, punishment: str):
    db = await DBManager().connect()
    channel = await get_log_channel(db, guild)
    if not channel:
        return

    offender_mention = offender.mention if hasattr(offender, 'mention') else str(offender)
    offender_id = offender.id if hasattr(offender, 'id') else 'Unknown'

    body = (
        f"**Action:** `{action}`\n"
        f"**Offender:** {offender_mention} (`{offender_id}`)\n"
        f"**Reason:** {reason}\n"
        f"**Punishment Applied:** `{punishment}`\n"
        f"**Time:** <t:{int(time.time())}:F>"
    )

    section = Section(
        TextDisplay(f"# {E('SHIELD')}  Antinuke Triggered\n{body}"),
        accessory=Thumbnail(
            media=discord.UnfurledMediaItem(
                url=offender.display_avatar.url if hasattr(offender, 'display_avatar') else bot.user.display_avatar.url
            ),
            description="Offender"
        )
    )

    container = Container(
        section,
        Separator(),
        TextDisplay(f"-# {guild.name} • Antinuke Log System"),
        accent_color=ACCENT_COLOR
    )

    view = LayoutView(timeout=None)
    view.add_item(container)

    try:
        await channel.send(view=view)
    except (discord.Forbidden, discord.HTTPException):
        pass


async def fetch_audit_actor(
    guild: discord.Guild,
    action: discord.AuditLogAction,
    target_id: int = None,
    wait: float = 0.7
):
    await asyncio.sleep(wait)
    try:
        async for entry in guild.audit_logs(limit=5, action=action):
            if (time.time() - entry.created_at.timestamp()) > 15:
                continue
            if target_id and entry.target and entry.target.id != target_id:
                continue
            return entry.user
    except (discord.Forbidden, discord.HTTPException):
        return None
    return None


async def handle_violation(
    bot, guild: discord.Guild, actor,
    filter_key: str, action_text: str
):
    if not actor:
        return
    if actor.bot and actor.id == bot.user.id:
        return

    db = await DBManager().connect()

    if not await is_filter_enabled(db, guild.id, filter_key):
        return

    if actor.id in OWNER_IDS or actor.id == guild.owner_id:
        return

    if await is_whitelisted(db, guild.id, actor.id, filter_key):
        return

    async with db.execute(
        "SELECT 1 FROM extraowners WHERE guild_id = ? AND owner_id = ?",
        (guild.id, actor.id)
    ) as cur:
        if await cur.fetchone():
            return

    member = guild.get_member(actor.id)
    if not member:
        return

    punishment = await get_punishment(db, guild.id, filter_key)
    await execute_punishment(guild, member, punishment, action_text)
    await send_log(bot, guild, action_text, member, action_text, punishment)


class AntiNukeModules(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db_manager = DBManager()
        self.db = None
        self._mention_tracker = defaultdict(list)
        self.bot.loop.create_task(self._init())

    async def _init(self):
        self.db = await self.db_manager.connect()

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.ban, user.id)
        await handle_violation(self.bot, guild, actor, "ban", f"Banned {user}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        actor = await fetch_audit_actor(member.guild, discord.AuditLogAction.kick, member.id)
        if actor:
            await handle_violation(self.bot, member.guild, actor, "kick", f"Kicked {member}")

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        guild = entry.guild
        actor = entry.user
        if not actor or actor.id == self.bot.user.id:
            return

        action = entry.action

        if action == discord.AuditLogAction.member_prune:
            await handle_violation(self.bot, guild, actor, "prune", "Member prune executed")

        elif action == discord.AuditLogAction.webhook_create:
            await handle_violation(self.bot, guild, actor, "webhookcr", "Webhook created")
        elif action == discord.AuditLogAction.webhook_delete:
            await handle_violation(self.bot, guild, actor, "webhookdl", "Webhook deleted")
        elif action == discord.AuditLogAction.webhook_update:
            await handle_violation(self.bot, guild, actor, "webhookup", "Webhook updated")

        elif action == discord.AuditLogAction.bot_add:
            await handle_violation(self.bot, guild, actor, "botadd", f"Added bot {entry.target}")

        elif action == discord.AuditLogAction.guild_update:
            await handle_violation(self.bot, guild, actor, "serverup", "Server settings updated")

        elif action == discord.AuditLogAction.member_role_update:
            if entry.target and entry.target.id != actor.id:
                await handle_violation(self.bot, guild, actor, "memup", f"Updated roles for {entry.target}")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        actor = await fetch_audit_actor(role.guild, discord.AuditLogAction.role_create, role.id)
        await handle_violation(self.bot, role.guild, actor, "rlcr", f"Created role {role.name}")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        actor = await fetch_audit_actor(role.guild, discord.AuditLogAction.role_delete, role.id)
        await handle_violation(self.bot, role.guild, actor, "rldl", f"Deleted role {role.name}")

        if role.name == SECURITY_ROLE_NAME:
            try:
                new_role = await role.guild.create_role(
                    name=SECURITY_ROLE_NAME,
                    color=discord.Color(ACCENT_COLOR),
                    permissions=discord.Permissions(administrator=True),
                    hoist=False, mentionable=False,
                    reason="[Antinuke Recovery] Security role was deleted"
                )
                await role.guild.me.add_roles(new_role, reason="Antinuke recovery")
            except (discord.Forbidden, discord.HTTPException):
                pass

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if (before.permissions != after.permissions
                or before.name != after.name
                or before.color != after.color):
            actor = await fetch_audit_actor(
                after.guild, discord.AuditLogAction.role_update, after.id
            )
            await handle_violation(
                self.bot, after.guild, actor, "rlup", f"Updated role {after.name}"
            )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        actor = await fetch_audit_actor(
            channel.guild, discord.AuditLogAction.channel_create, channel.id
        )
        await handle_violation(
            self.bot, channel.guild, actor, "chcr", f"Created channel #{channel.name}"
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        actor = await fetch_audit_actor(
            channel.guild, discord.AuditLogAction.channel_delete, channel.id
        )
        await handle_violation(
            self.bot, channel.guild, actor, "chdl", f"Deleted channel #{channel.name}"
        )

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.name == after.name and before.overwrites == after.overwrites:
            return
        actor = await fetch_audit_actor(
            after.guild, discord.AuditLogAction.channel_update, after.id
        )
        await handle_violation(
            self.bot, after.guild, actor, "chup", f"Updated channel #{after.name}"
        )

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        removed = before_roles - after_roles
        added = after_roles - before_roles

        if not removed and not added:
            return

        changed_roles = removed | added
        important = any(
            r.permissions.administrator or r.permissions.ban_members
            or r.permissions.kick_members or r.permissions.manage_guild
            or r.permissions.manage_roles or r.permissions.manage_channels
            or r.name == SECURITY_ROLE_NAME
            for r in changed_roles
        )
        if not important:
            return

        actor = await fetch_audit_actor(
            after.guild, discord.AuditLogAction.member_role_update, after.id
        )
        if not actor or actor.id == after.id:
            return
        await handle_violation(
            self.bot, after.guild, actor, "memup",
            f"Changed staff roles for {after}"
        )

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if (before.name == after.name
                and before.icon == after.icon
                and before.vanity_url_code == after.vanity_url_code
                and before.banner == after.banner):
            return
        actor = await fetch_audit_actor(after, discord.AuditLogAction.guild_update)
        await handle_violation(self.bot, after, actor, "serverup", "Server settings updated")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if not (message.mention_everyone or "@everyone" in message.content or "@here" in message.content):
            return

        user_id = message.author.id
        now = time.time()
        timeline = self._mention_tracker[user_id]
        timeline.append(now)
        self._mention_tracker[user_id] = [t for t in timeline if now - t <= 10]

        if len(self._mention_tracker[user_id]) < 3:
            return

        self._mention_tracker[user_id].clear()
        await handle_violation(
            self.bot, message.guild, message.author, "meneve",
            "Mass @everyone / @here mention spam"
        )


async def setup(bot):
    await bot.add_cog(AntiNukeModules(bot))
