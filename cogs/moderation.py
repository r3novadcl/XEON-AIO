import discord
from discord import ui
from discord.ext import commands
import asyncio
import datetime
from utils.ui import (
    denied_container,
    mod_action_container,
    action_container,
    confirmation_prompt,
)
from utils import emojis as E
from utils.cmd_help import cmd_usage_view
from utils.category_help import CategoryHelpView, get_category

BLACK = discord.Colour(0x000000)


def hierarchy_check(ctx, target: discord.Member) -> tuple[bool, str]:
    if target == ctx.guild.owner:
        return False, "I cannot act on the server owner!"
    if target.top_role >= ctx.guild.me.top_role:
        return False, "I cannot act on someone with a higher or equal role to me!"
    if ctx.author != ctx.guild.owner and target.top_role >= ctx.author.top_role:
        return False, "You cannot act on someone with a higher or equal role to you!"
    return True, ""


async def try_dm(member: discord.Member, content: str) -> bool:
    try:
        await member.send(content)
        return True
    except Exception:
        return False


class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot   = bot
        self._snipe: dict[int, dict] = {}

    @commands.command(name="kick", aliases=["kickmember"])
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason: str = None,
    ):

        if member is None:
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "kick"))

        if member == ctx.author:
            return await ctx.send(**denied_container("You cannot kick yourself!"))

        if member == ctx.guild.me:
            return await ctx.send(**denied_container("I cannot kick myself!"))

        ok, err = hierarchy_check(ctx, member)
        if not ok:
            return await ctx.send(**denied_container(err))

        confirmed = await confirmation_prompt(ctx, self.bot.user)
        if not confirmed:
            m = await ctx.send(
                **action_container(
                    "Action Cancelled",
                    [f"{E.ERROR} The kick was cancelled."],
                    BLACK,
                )
            )
            await asyncio.sleep(3)
            await m.delete()
            return

        dm_done = await try_dm(
            member,
            f"You have been **kicked** from **{ctx.guild.name}**.\n"
            f"**Reason:** {reason or 'No reason provided'}",
        )
        await member.kick(reason=f"[{ctx.author}] {reason or 'No reason'}")

        await ctx.send(
            **mod_action_container(
                action         = "User have been kicked!",
                target_name    = str(member),
                moderator_name = ctx.author.name,
                reason         = reason,
                dm_done        = dm_done,
                bot_avatar     = self.bot.user.display_avatar.url,
            )
        )

    @commands.command(name="ban", aliases=["banmember"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason: str = None,
    ):

        if member is None:
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "ban"))

        if member == ctx.author:
            return await ctx.send(**denied_container("You cannot ban yourself!"))

        if member == ctx.guild.me:
            return await ctx.send(**denied_container("I cannot ban myself!"))

        ok, err = hierarchy_check(ctx, member)
        if not ok:
            return await ctx.send(**denied_container(err))

        confirmed = await confirmation_prompt(ctx, self.bot.user)
        if not confirmed:
            return

        dm_done = await try_dm(
            member,
            f"You have been **banned** from **{ctx.guild.name}**.\n"
            f"**Reason:** {reason or 'No reason provided'}",
        )
        await member.ban(
            reason=f"[{ctx.author}] {reason or 'No reason'}",
            delete_message_days=0,
        )

        await ctx.send(
            **mod_action_container(
                action         = "User have been banned!",
                target_name    = str(member),
                moderator_name = ctx.author.name,
                reason         = reason,
                dm_done        = dm_done,
                bot_avatar     = self.bot.user.display_avatar.url,
            )
        )

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def unban(
        self,
        ctx,
        user_id: int = None,
        *,
        reason: str = None,
    ):

        if user_id is None:
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "unban"))

        try:
            entry = await ctx.guild.fetch_ban(discord.Object(id=user_id))
        except discord.NotFound:
            return await ctx.send(**denied_container("That user is not banned!"))
        except discord.HTTPException:
            return await ctx.send(**denied_container("Invalid user ID provided!"))

        await ctx.guild.unban(
            entry.user,
            reason=f"[{ctx.author}] {reason or 'No reason'}",
        )

        await ctx.send(
            **mod_action_container(
                action         = "User have been unbanned!",
                target_name    = str(entry.user),
                moderator_name = ctx.author.name,
                reason         = reason,
                bot_avatar     = self.bot.user.display_avatar.url,
            )
        )

    @commands.command(name="softban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def softban(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason: str = None,
    ):

        if member is None:
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "softban"))

        if member == ctx.author:
            return await ctx.send(**denied_container("You cannot softban yourself!"))

        ok, err = hierarchy_check(ctx, member)
        if not ok:
            return await ctx.send(**denied_container(err))

        confirmed = await confirmation_prompt(ctx, self.bot.user)
        if not confirmed:
            return

        dm_done = await try_dm(
            member,
            f"You have been **softbanned** from **{ctx.guild.name}**.\n"
            f"(Messages deleted. You may rejoin.)\n"
            f"**Reason:** {reason or 'No reason provided'}",
        )
        await member.ban(
            reason=f"[Softban][{ctx.author}] {reason or 'No reason'}",
            delete_message_days=7,
        )
        await ctx.guild.unban(member, reason="Softban - auto unban")

        await ctx.send(
            **mod_action_container(
                action         = "User have been softbanned!",
                target_name    = str(member),
                moderator_name = ctx.author.name,
                reason         = reason,
                dm_done        = dm_done,
                bot_avatar     = self.bot.user.display_avatar.url,
            )
        )

    @commands.command(name="fakeban")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def fakeban(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason: str = None,
    ):

        if member is None:
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "fakeban"))

        await ctx.send(
            **mod_action_container(
                action         = "User have been banned! (fake)",
                target_name    = str(member),
                moderator_name = ctx.author.name,
                reason         = reason,
                dm_done        = False,
                bot_avatar     = self.bot.user.display_avatar.url,
            )
        )

    @commands.command(name="mute", aliases=["timeout"])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @commands.guild_only()
    async def mute(
        self,
        ctx,
        member: discord.Member = None,
        duration: str = None,
        *,
        reason: str = None,
    ):

        if member is None:
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "mute"))

        if duration is None:
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "mute"))

        if member == ctx.author:
            return await ctx.send(**denied_container("You cannot mute yourself!"))

        if member == ctx.guild.me:
            return await ctx.send(**denied_container("I cannot mute myself!"))

        ok, err = hierarchy_check(ctx, member)
        if not ok:
            return await ctx.send(**denied_container(err))

        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            unit    = duration[-1].lower()
            amount  = int(duration[:-1])
            seconds = amount * units[unit]
        except (KeyError, ValueError, IndexError):
            return await ctx.send(
                **denied_container(
                    "Invalid duration format!\n"
                    "Use: `10s` `5m` `2h` `1d`"
                )
            )

        if seconds <= 0:
            return await ctx.send(**denied_container("Duration must be greater than 0!"))

        if seconds > 2_419_200:
            return await ctx.send(
                **denied_container("Maximum timeout duration is 28 days!")
            )

        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)

        dm_done = await try_dm(
            member,
            f"You have been **muted** in **{ctx.guild.name}** for `{duration}`.\n"
            f"**Reason:** {reason or 'No reason provided'}",
        )
        await member.timeout(
            until,
            reason=f"[{ctx.author}] {reason or 'No reason'}",
        )

        await ctx.send(
            **mod_action_container(
                action         = f"User have been muted for {duration}!",
                target_name    = str(member),
                moderator_name = ctx.author.name,
                reason         = reason,
                dm_done        = dm_done,
                extra_lines    = [f"Duration : `{duration}`"],
                bot_avatar     = self.bot.user.display_avatar.url,
            )
        )

    @commands.command(name="unmute", aliases=["untimeout"])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @commands.guild_only()
    async def unmute(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason: str = None,
    ):

        if member is None:
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "unmute"))

        if not member.timed_out:
            return await ctx.send(**denied_container("That member is not muted!"))

        await member.timeout(
            None,
            reason=f"[{ctx.author}] {reason or 'No reason'}",
        )

        await ctx.send(
            **mod_action_container(
                action         = "User have been unmuted!",
                target_name    = str(member),
                moderator_name = ctx.author.name,
                reason         = reason,
                bot_avatar     = self.bot.user.display_avatar.url,
            )
        )

    @commands.command(name="nick", aliases=["nickname"])
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.guild_only()
    async def nick(
        self,
        ctx,
        member: discord.Member = None,
        *,
        nickname: str = None,
    ):

        if member is None:
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "nick"))

        ok, err = hierarchy_check(ctx, member)
        if not ok:
            return await ctx.send(**denied_container(err))

        old = member.display_name
        await member.edit(nick=nickname)

        await ctx.send(
            **action_container(
                "Nickname Changed!",
                [
                    f"{E.TARGET}  **User :** {member.mention}",
                    f"**Old Nick :** `{old}`",
                    f"**New Nick :** `{nickname or member.name}`",
                    f"{E.MODERATOR}  **Moderator :** {ctx.author.name}",
                ],
            )
        )

    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def lock(
        self,
        ctx,
        channel: discord.TextChannel = None,
        *,
        reason: str = None,
    ):

        ch = channel or ctx.channel
        await ch.set_permissions(
            ctx.guild.default_role,
            send_messages=False,
            reason=f"[{ctx.author}] {reason or 'No reason'}",
        )

        await ctx.send(
            **action_container(
                f"{E.LOCK} Channel Locked!",
                [
                    f"{E.CHANNEL} **Channel:** {ch.mention}",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                    f"{E.REASON} **Reason:** `{reason or 'No reason provided'}`",
                ],
            )
        )

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def unlock(
        self,
        ctx,
        channel: discord.TextChannel = None,
        *,
        reason: str = None,
    ):

        ch = channel or ctx.channel
        await ch.set_permissions(
            ctx.guild.default_role,
            send_messages=True,
            reason=f"[{ctx.author}] {reason or 'No reason'}",
        )

        await ctx.send(
            **action_container(
                f"{E.UNLOCK} Channel Unlocked!",
                [
                    f"{E.CHANNEL} **Channel:** {ch.mention}",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                    f"{E.REASON} **Reason:** `{reason or 'No reason provided'}`",
                ],
            )
        )

    @commands.command(name="lockall")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def lockall(self, ctx, *, reason: str = None):

        confirmed = await confirmation_prompt(ctx, self.bot.user)
        if not confirmed:
            return

        locked = failed = 0
        for ch in ctx.guild.text_channels:
            try:
                await ch.set_permissions(
                    ctx.guild.default_role,
                    send_messages=False,
                )
                locked += 1
            except Exception:
                failed += 1

        await ctx.send(
            **action_container(
                f"{E.LOCK} All Channels Locked!",
                [
                    f"{E.SUCCESS} **Locked:** `{locked}` channels",
                    f"{E.ERROR} **Failed:** `{failed}` channels",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                    f"{E.REASON} **Reason:** `{reason or 'No reason provided'}`",
                ],
            )
        )

    @commands.command(name="unlockall")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def unlockall(self, ctx, *, reason: str = None):

        unlocked = failed = 0
        for ch in ctx.guild.text_channels:
            try:
                await ch.set_permissions(
                    ctx.guild.default_role,
                    send_messages=True,
                )
                unlocked += 1
            except Exception:
                failed += 1

        await ctx.send(
            **action_container(
                f"{E.UNLOCK} All Channels Unlocked!",
                [
                    f"{E.SUCCESS} **Unlocked:** `{unlocked}` channels",
                    f"{E.ERROR} **Failed:** `{failed}` channels",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                    f"{E.REASON} **Reason:** `{reason or 'No reason provided'}`",
                ],
            )
        )

    @commands.command(name="hide")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def hide(
        self,
        ctx,
        channel: discord.TextChannel = None,
    ):

        ch = channel or ctx.channel
        await ch.set_permissions(
            ctx.guild.default_role,
            view_channel=False,
        )

        await ctx.send(
            **action_container(
                f"{E.HIDE} Channel Hidden!",
                [
                    f"{E.CHANNEL} **Channel:** {ch.mention}",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @commands.command(name="unhide")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def unhide(
        self,
        ctx,
        channel: discord.TextChannel = None,
    ):

        ch = channel or ctx.channel
        await ch.set_permissions(
            ctx.guild.default_role,
            view_channel=True,
        )

        await ctx.send(
            **action_container(
                f"{E.UNHIDE} Channel Unhidden!",
                [
                    f"{E.CHANNEL} **Channel:** {ch.mention}",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @commands.command(name="hideall")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def hideall(self, ctx):

        hidden = failed = 0
        for ch in ctx.guild.text_channels:
            try:
                await ch.set_permissions(
                    ctx.guild.default_role,
                    view_channel=False,
                )
                hidden += 1
            except Exception:
                failed += 1

        await ctx.send(
            **action_container(
                f"{E.HIDE} All Channels Hidden!",
                [
                    f"{E.SUCCESS} **Hidden:** `{hidden}` channels",
                    f"{E.ERROR} **Failed:** `{failed}` channels",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @commands.command(name="unhideall")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def unhideall(self, ctx):

        unhidden = failed = 0
        for ch in ctx.guild.text_channels:
            try:
                await ch.set_permissions(
                    ctx.guild.default_role,
                    view_channel=True,
                )
                unhidden += 1
            except Exception:
                failed += 1

        await ctx.send(
            **action_container(
                f"{E.UNHIDE} All Channels Unhidden!",
                [
                    f"{E.SUCCESS} **Unhidden:** `{unhidden}` channels",
                    f"{E.ERROR} **Failed:** `{failed}` channels",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @commands.command(name="slowmode", aliases=["slow"])
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def slowmode(
        self,
        ctx,
        seconds: int = None,
        channel: discord.TextChannel = None,
    ):

        if seconds is None:
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "slowmode"))

        if not 0 <= seconds <= 21600:
            return await ctx.send(
                **denied_container(
                    "Slowmode must be between `0` and `21600` seconds!\n"
                    "Use `0` to disable slowmode."
                )
            )

        ch = channel or ctx.channel
        await ch.edit(slowmode_delay=seconds)

        status = "Disabled" if seconds == 0 else f"Set to `{seconds}s`"

        await ctx.send(
            **action_container(
                f"{E.SLOW} Slowmode {status}!",
                [
                    f"{E.CHANNEL} **Channel:** {ch.mention}",
                    f"{E.UPTIME} **Delay:** `{seconds}s`",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @commands.command(name="unslowmode", aliases=["unslow"])
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def unslowmode(
        self,
        ctx,
        channel: discord.TextChannel = None,
    ):

        ch = channel or ctx.channel
        await ch.edit(slowmode_delay=0)

        await ctx.send(
            **action_container(
                "Slowmode Removed!",
                [
                    f"{E.CHANNEL} **Channel:** {ch.mention}",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @commands.command(name="nuke")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def nuke(
        self,
        ctx,
        channel: discord.TextChannel = None,
    ):

        ch        = channel or ctx.channel
        confirmed = await confirmation_prompt(ctx, self.bot.user)
        if not confirmed:
            return

        pos    = ch.position
        new_ch = await ch.clone(reason=f"[Nuke] {ctx.author}")
        await ch.delete(reason=f"[Nuke] {ctx.author}")
        await new_ch.edit(position=pos)

        await new_ch.send(
            **action_container(
                f"{E.NUKE} Channel Nuked!",
                [
                    f"{E.CHANNEL} **Channel:** {new_ch.mention}",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @commands.command(name="snipe")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def snipe(self, ctx):

        data = self._snipe.get(ctx.channel.id)
        if not data:
            return await ctx.send(
                **denied_container("There is nothing to snipe in this channel!")
            )

        container = ui.Container(accent_color=BLACK)
        container.add_item(ui.TextDisplay(
            content=f"{E.SNIPE}  **Sniped Message**"
        ))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(
            content=(
                f"{E.TARGET} **Author :** {data['author']}\n"
                f"{E.CHANNEL} **Content :**\n"
                f"{data['content'] or '*[No text content]*'}"
            )
        ))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(
            content=f"{E.MODERATOR} **Sniped by :** {ctx.author.name}"
        ))

        view = ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        self._snipe[message.channel.id] = {
            "content": message.content,
            "author" : str(message.author),
        }

    @commands.command(name="unbanall")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def unbanall(self, ctx):

        confirmed = await confirmation_prompt(ctx, self.bot.user)
        if not confirmed:
            return

        msg = await ctx.send(
            **action_container(
                f"{E.LOADING} Processing…",
                ["Unbanning all users, please wait…"],
                BLACK,
            )
        )

        count = failed = 0
        async for entry in ctx.guild.bans():
            try:
                await ctx.guild.unban(
                    entry.user,
                    reason=f"[Unbanall] {ctx.author}",
                )
                count += 1
            except Exception:
                failed += 1

        await msg.edit(
            **action_container(
                "All Users Unbanned!",
                [
                    f"{E.SUCCESS} **Unbanned:** `{count}` users",
                    f"{E.ERROR} **Failed:** `{failed}` users",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @commands.group(
        name="channel",
        aliases=["ch"],
        invoke_without_command=True,
    )
    @commands.guild_only()
    async def channel_group(self, ctx):

        cat_key, cat_data = get_category("channel")
        view = CategoryHelpView(
            ctx           = ctx,
            category_key  = cat_key,
            category_data = cat_data,
            bot_name      = self.bot.BOT_NAME,
            prefix        = ctx.prefix,
        )
        await ctx.send(view=view)

    @channel_group.command(name="create")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def ch_create(self, ctx, *, name: str = None):

        if not name:
            return await ctx.send(
                view=cmd_usage_view(ctx.prefix, "channel")
            )

        ch = await ctx.guild.create_text_channel(
            name=name,
            reason=f"[{ctx.author}] Created via command",
        )

        await ctx.send(
            **action_container(
                "Channel Created!",
                [
                    f"{E.CHANNEL} **Channel:** {ch.mention}",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @channel_group.command(name="delete")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def ch_delete(
        self,
        ctx,
        channel: discord.TextChannel = None,
    ):

        ch        = channel or ctx.channel
        confirmed = await confirmation_prompt(ctx, self.bot.user)
        if not confirmed:
            return

        name = ch.name
        await ch.delete(reason=f"[{ctx.author}] Deleted via command")

        if ch != ctx.channel:
            await ctx.send(
                **action_container(
                    "Channel Deleted!",
                    [
                        f"{E.CHANNEL} **Channel:** `#{name}`",
                        f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                    ],
                )
            )

    @channel_group.command(name="rename")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def ch_rename(self, ctx, *, name: str = None):

        if not name:
            return await ctx.send(
                view=cmd_usage_view(ctx.prefix, "channel")
            )

        old = ctx.channel.name
        await ctx.channel.edit(
            name=name,
            reason=f"[{ctx.author}] Renamed via command",
        )

        await ctx.send(
            **action_container(
                "Channel Renamed!",
                [
                    f"**Old Name:** `#{old}`",
                    f"**New Name:** `#{name}`",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @channel_group.command(name="clone")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def ch_clone(
        self,
        ctx,
        channel: discord.TextChannel = None,
    ):

        ch  = channel or ctx.channel
        new = await ch.clone(
            reason=f"[{ctx.author}] Cloned via command"
        )

        await ctx.send(
            **action_container(
                "Channel Cloned!",
                [
                    f"**Original:** {ch.mention}",
                    f"**Clone:** {new.mention}",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @channel_group.command(name="transfer")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def ch_transfer(
        self,
        ctx,
        channel: discord.TextChannel = None,
        category: discord.CategoryChannel = None,
    ):

        if not channel or not category:
            return await ctx.send(
                view=cmd_usage_view(ctx.prefix, "channel")
            )

        old_cat = channel.category
        await channel.edit(
            category=category,
            reason=f"[{ctx.author}] Transferred via command",
        )

        await ctx.send(
            **action_container(
                "Channel Transferred!",
                [
                    f"{E.CHANNEL} **Channel:** {channel.mention}",
                    f"**From:** `{old_cat.name if old_cat else 'No Category'}`",
                    f"**To:** `{category.name}`",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
