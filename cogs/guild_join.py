import discord
from discord.ext import commands
from utils.config import BOT_NAME, DEFAULT_PREFIX, INVITE_URL as INVITE_LINK, SUPPORT_SERVER as SUPPORT_LINK
from discord import ui


from XEON.emojis import E as _EMGR, FALLBACK_EMOJI
import re as _re

_LOCAL_KEY_MAP = {
    "success": "SUCCESS",
    "error": "ERROR",
    "info": "INFO",
    "wave": "WAVE",
    "link": "LINK_ICO",
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


class WelcomeDMView(ui.LayoutView):
    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        super().__init__(timeout=None)

        c = ui.Container(accent_color=DEFAULT_ACCENT)

        header = ui.TextDisplay(
            f"{ES('wave')} **Thanks for adding {BOT_NAME}!**\n\n"
            f"My default prefix is `{DEFAULT_PREFIX}`\n"
            f"Use `{DEFAULT_PREFIX}help` in the server for commands\n"
            f"For questions join the **Support server**"
        )

        if bot.user and bot.user.avatar:
            section = ui.Section(
                header,
                accessory=ui.Thumbnail(
                    media=discord.UnfurledMediaItem(url=bot.user.display_avatar.url)
                ),
            )
            c.add_item(section)
        else:
            c.add_item(header)

        c.add_item(ui.Separator())

        c.add_item(ui.ActionRow(
            ui.Button(
                label="Support Server",
                style=discord.ButtonStyle.link,
                url=SUPPORT_LINK,
            ),
            ui.Button(
                label="Invite Bot",
                style=discord.ButtonStyle.link,
                url=INVITE_LINK,
            ),
        ))

        c.add_item(ui.ActionRow(
            ui.Button(
                label=f"Go to {guild.name}"[:80],
                style=discord.ButtonStyle.link,
                url=f"https://discord.com/channels/{guild.id}",
            ),
        ))

        c.add_item(ui.Separator(visible=False))
        c.add_item(ui.TextDisplay(f"-# {BOT_NAME} • Thanks for choosing us"))

        self.add_item(c)


class WelcomeServerView(ui.LayoutView):
    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        super().__init__(timeout=None)

        c = ui.Container(accent_color=DEFAULT_ACCENT)

        header = ui.TextDisplay(
            f"{ES('wave')} **Thanks for adding {BOT_NAME}!**\n\n"
            f"My default prefix is `{DEFAULT_PREFIX}`\n"
            f"Use `{DEFAULT_PREFIX}help` or mention me for commands\n"
            f"For questions join our **Support server**"
        )

        if bot.user and bot.user.avatar:
            section = ui.Section(
                header,
                accessory=ui.Thumbnail(
                    media=discord.UnfurledMediaItem(url=bot.user.display_avatar.url)
                ),
            )
            c.add_item(section)
        else:
            c.add_item(header)

        c.add_item(ui.Separator())

        c.add_item(ui.ActionRow(
            ui.Button(
                label="Support Server",
                style=discord.ButtonStyle.link,
                url=SUPPORT_LINK,
            ),
            ui.Button(
                label="Invite Bot",
                style=discord.ButtonStyle.link,
                url=INVITE_LINK,
            ),
        ))

        c.add_item(ui.Separator(visible=False))
        c.add_item(ui.TextDisplay(f"-# Use `{DEFAULT_PREFIX}help` to get started"))

        self.add_item(c)


class GuildJoin(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        owner = guild.owner
        if owner:
            try:
                dm_view = WelcomeDMView(self.bot, guild)
                await owner.send(view=dm_view)
            except discord.Forbidden:
                pass
            except Exception:
                pass

        target_channel = self._find_channel(guild)
        if not target_channel:
            return

        try:
            server_view = WelcomeServerView(self.bot, guild)
            await target_channel.send(view=server_view)
        except discord.Forbidden:
            pass
        except Exception:
            pass

    def _find_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        me = guild.me
        if not me:
            return None

        priority_names = ("general", "welcome", "bot-commands", "commands", "bot", "chat")
        for name in priority_names:
            ch = discord.utils.find(
                lambda c: (
                    isinstance(c, discord.TextChannel)
                    and name in c.name.lower()
                    and c.permissions_for(me).send_messages
                ),
                guild.channels,
            )
            if ch:
                return ch

        if guild.system_channel and guild.system_channel.permissions_for(me).send_messages:
            return guild.system_channel

        for ch in guild.text_channels:
            if ch.permissions_for(me).send_messages:
                return ch

        return None


async def setup(bot: commands.Bot):
    await bot.add_cog(GuildJoin(bot))
