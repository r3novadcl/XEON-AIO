import asyncio
import json
import os
import sys
import time
from pathlib import Path

import discord
from discord.ext import commands, tasks

from utils.config import (
    BOT_NAME, DEFAULT_PREFIX, INVITE_URL, OWNER_IDS,
    STATUS_PAGE, SUPPORT_SERVER, WEBSITE,
)

COGS = [
    "cogs.prefix",
    "cogs.ping",
    "cogs.stats",
    "cogs.moderation",
    "cogs.purge",
    "cogs.role",
    "cogs.channelinfo",
    "cogs.general",
    "cogs.list_cmds",
    "cogs.roleinfo",
    "cogs.serverinfo",
    "cogs.ticket",
    "cogs.userinfo",
    "cogs.embeds",
    "cogs.devjsk",
    "cogs.noprefix",
    "cogs.guild_join",
    "cogs.mention_reply",
    "cogs.giveaway",
    "cogs.welcome",
    "cogs.tracker",
    "cogs.autorole",
    "cogs.autoresponder",
    "cogs.autoreact",
    "cogs.reactionrole",
    "cogs.logging",
    "cogs.antinuke_core",
    "cogs.antinuke_modules",
    "cogs.automod",
    "cogs.help",
    "cogs.premium",
    "cogs.webhook_logger",
]


def _get_prefix(bot, message: discord.Message):
    if not message.guild:
        return DEFAULT_PREFIX
    try:
        from cogs.prefix import get_prefix
        return get_prefix(message.guild.id)
    except Exception:
        return DEFAULT_PREFIX


class XEON(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=_get_prefix,
            intents=discord.Intents.all(),
            help_command=None,
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=False, replied_user=False,
            ),
        )
        self.start_time = time.time()
        self.BOT_NAME = BOT_NAME
        self.DEFAULT_PREFIX = DEFAULT_PREFIX
        self.WEBSITE = WEBSITE
        self.SUPPORT_SERVER = SUPPORT_SERVER
        self.STATUS_PAGE = STATUS_PAGE
        self.INVITE_URL = INVITE_URL
        self.OWNER_IDS = OWNER_IDS
        self.status_list = [
            f"Powered by XEON development | {DEFAULT_PREFIX}help",
            "XEON - Control Everything",
        ]
        self.status_index = 0

    async def setup_hook(self):
        for cog in COGS:
            try:
                await self.load_extension(cog)
                print(f"Loaded: {cog}")
            except Exception as err:
                print(f"Failed: {cog} - {err}")

    async def on_ready(self):
        print(f"{BOT_NAME} is online as {self.user} | "
              f"{len(self.guilds)} guilds | "
              f"{sum(g.member_count or 0 for g in self.guilds)} users")
        if not self.rotate_status.is_running():
            self.rotate_status.start()

    @tasks.loop(seconds=10)
    async def rotate_status(self):
        try:
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=self.status_list[self.status_index],
                )
            )
            self.status_index = (self.status_index + 1) % len(self.status_list)
        except Exception as e:
            print(f"Status error: {e}")

    @rotate_status.before_loop
    async def before_rotate_status(self):
        await self.wait_until_ready()

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        ctx = await self.get_context(message)

        if message.guild:
            from cogs.prefix import is_ignored
            if is_ignored(message.guild.id, message.channel.id):
                if ctx.command and ctx.command.qualified_name in ("ignore", "unignore", "ignorelist"):
                    await self.invoke(ctx)
                return

        if ctx.prefix and not ctx.command:
            try:
                from utils.category_help import get_category, CategoryHelpView

                raw = message.content[len(ctx.prefix):].strip()
                query = raw.lower().split()[0] if raw else ""
                if query:
                    cat_key, cat_data = get_category(query)
                    if cat_key and cat_data:
                        view = CategoryHelpView(
                            ctx=ctx,
                            category_key=cat_key,
                            category_data=cat_data,
                            bot_name=self.BOT_NAME,
                            prefix=ctx.prefix,
                        )
                        return await message.channel.send(view=view)
            except Exception:
                pass

        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        from utils.ui import denied_container
        from utils.cmd_help import cmd_usage_view

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)) \
                and not isinstance(error, (commands.MemberNotFound, commands.RoleNotFound)):
            view = cmd_usage_view(ctx.prefix, ctx.command.name)
            if view:
                return await ctx.send(view=view)
            if isinstance(error, commands.MissingRequiredArgument):
                return await ctx.send(**denied_container(f"Missing argument: `{error.param.name}`"))
            return await ctx.send(**denied_container(f"Invalid argument: `{error}`"))

        messages = (
            (commands.MissingPermissions, "You don't have permission to use this command!"),
            (commands.BotMissingPermissions, "I don't have the required permissions!"),
            (commands.MemberNotFound, "Member not found! Please mention a valid member."),
            (commands.RoleNotFound, "Role not found! Please mention a valid role."),
            (commands.CheckFailure, "You don't have permission to use this command!"),
        )
        for exc_type, text in messages:
            if isinstance(error, exc_type):
                return await ctx.send(**denied_container(text))

        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(**denied_container(
                f"Command on cooldown! Try again in `{error.retry_after:.1f}s`"
            ))


async def _auto_upload_emojis():
    uploaded_path = Path("emojis.uploaded.json")
    try:
        if uploaded_path.exists() and json.loads(uploaded_path.read_text()):
            return
    except Exception:
        pass

    print("First-time application emoji upload starting...")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from scripts.upload_application_emojis import run as upload_run
        from XEON.emojis import E as emoji_map
        await upload_run()
        emoji_map.reload()
        print("Application emoji upload complete.")
    except (Exception, SystemExit) as e:
        print(f"Emoji upload failed ({e}), using fallback emoji IDs.")


async def _start():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("DISCORD_TOKEN is missing in .env")
        return
    await _auto_upload_emojis()
    async with bot:
        await bot.start(token)


bot = XEON()

if __name__ == "__main__":
    try:
        asyncio.run(_start())
    except KeyboardInterrupt:
        print("Bot stopped.")
