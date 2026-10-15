import discord
from discord.ext import commands
from utils.config import BOT_NAME, DEFAULT_PREFIX, INVITE_URL, SUPPORT_SERVER as SUPPORT_URL
from discord import SelectOption
from discord.ui import (
    LayoutView, Container, Section, TextDisplay, Separator,
    Select, ActionRow, Thumbnail, Button
)
import traceback
import logging


ACCENT_COLOR   = discord.Color(0x000000)
BOT_TAGLINE    = " A Multipurpose Bot XEON - Controls Everything"


from XEON.emojis import E as _EMGR


CAT_EMOJI = _EMGR["GLOBAL"]

EMOJI_ANTINUKE       = _EMGR["SECURITY"]
EMOJI_AUTOMOD        = _EMGR["AUTOMOD"]
EMOJI_AUTOMATIONS    = _EMGR["PARTNERS"]
EMOJI_AUTOROLE       = _EMGR["ZBAT"]
EMOJI_EMBED          = _EMGR["SPONSOR"]
EMOJI_GENERAL        = _EMGR["SNAP"]
EMOJI_GIVEAWAY       = _EMGR["GIFTBOX"]
EMOJI_GREET          = _EMGR["GREET"]
EMOJI_LOGGING        = _EMGR["PROFILE"]
EMOJI_MODERATION     = _EMGR["MODERATION"]
EMOJI_NOPREFIX       = _EMGR["VIP"]
EMOJI_PREMIUM        = _EMGR["ZCROWN"]
EMOJI_REACTIONROLES  = _EMGR["REACTIONROLE"]
EMOJI_TICKET         = _EMGR["TICKET"]
EMOJI_TRACKER        = _EMGR["ROLEPLAY"]


CATEGORY_COMMANDS = {
    "Antinuke": {
        "emoji": EMOJI_ANTINUKE,
        "description": "Advanced protection against server nuking and unauthorised actions.",
        "sections": [
            {
                "header": "Antinuke",
                "commands": [
                    "antinuke", "antinuke enable",
                    "antinuke disable", "antinuke wizard",
                    "antinuke filters", "antinuke logs",
                    "antinuke wl", "antinuke unwl",
                    "antinuke wlist", "antinuke wlreset",
                ],
            },
            {
                "header": "ExtraOwner",
                "commands": [
                    "extraowner set", "extraowner reset",
                    "extraowner view", "extraowner clear",
                ],
            },
        ],
    },
    "AutoMod": {
        "emoji": EMOJI_AUTOMOD,
        "description": "Automatic moderation to keep your server safe from spam, invites, and disruptions.",
        "sections": [
            {
                "header": "AutoMod",
                "commands": [
                    "automod", "automod enable",
                    "automod disable", "automod manage",
                    "automod settings", "automod rules",
                    "automod reset", "automod logging",
                ],
            },
            {
                "header": "Whitelist",
                "commands": [
                    "automod wl channel", "automod wl role",
                    "automod wl show", "automod wl reset",
                ],
            },
            {
                "header": "Blacklist",
                "commands": [
                    "automod bl add", "automod bl remove",
                    "automod bl list",
                ],
            },
        ],
    },
    "Automations": {
        "emoji": EMOJI_AUTOMATIONS,
        "description": "Automatically react & respond — combines AutoReact and AutoResponder in one place.",
        "sections": [
            {
                "header": "AutoReact",
                "commands": [
                    "arc add", "arc channel",
                    "arc remove", "arc removechannel",
                    "arc list", "arc clear",
                ],
            },
            {
                "header": "AutoResponder",
                "commands": [
                    "ar add", "ar addcontains",
                    "ar addstart", "ar remove",
                    "ar list", "ar clear",
                ],
            },
        ],
    },
    "AutoRole": {
        "emoji": EMOJI_AUTOROLE,
        "description": "Automatically assign roles to new members when they join.",
        "sections": [
            {
                "header": "Humans",
                "commands": [
                    "autorole humans add",
                    "autorole humans remove",
                    "autorole humans list",
                ],
            },
            {
                "header": "Bots",
                "commands": [
                    "autorole bots add",
                    "autorole bots remove",
                    "autorole bots list",
                ],
            },
        ],
    },
    "Embed": {
        "emoji": EMOJI_EMBED,
        "description": "Build and send rich embeds with a clean modal builder.",
        "sections": [
            {
                "header": "Embed",
                "commands": [
                    "embed", "embed create",
                ],
            },
        ],
    },
    "General": {
        "emoji": EMOJI_GENERAL,
        "description": "General information about the bot, its stats, and user profiles.",
        "sections": [
            {
                "header": "General",
                "commands": [
                    "ping", "pong", "stats",
                    "uptime", "system",
                ],
            },
        ],
    },
    "Giveaway": {
        "emoji": EMOJI_GIVEAWAY,
        "description": "Host and manage giveaways for your community.",
        "sections": [
            {
                "header": "Giveaway",
                "commands": [
                    "giveaway", "gstart", "gend",
                    "greroll", "glist", "gdelete",
                ],
            },
        ],
    },
    "Greet": {
        "emoji": EMOJI_GREET,
        "description": "Setup automatic welcome messages for new members.",
        "sections": [
            {
                "header": "Setup",
                "commands": [
                    "greet setup", "greet channel",
                    "greet type", "greet disable",
                ],
            },
            {
                "header": "Container Settings",
                "commands": [
                    "greet content", "greet title",
                    "greet description", "greet color",
                    "greet thumbnail", "greet image",
                ],
            },
            {
                "header": "Other",
                "commands": [
                    "greet message", "greet deleteafter",
                    "greet test", "greet config",
                    "greet variables",
                ],
            },
        ],
    },
    "Logging": {
        "emoji": EMOJI_LOGGING,
        "description": "Advanced per-event logging for your server.",
        "sections": [
            {
                "header": "Logging",
                "commands": [
                    "log setup", "log set",
                    "log enable", "log disable",
                    "log config", "log types",
                    "log reset",
                ],
            },
        ],
    },
    "Moderation": {
        "emoji": EMOJI_MODERATION,
        "description": "Powerful moderation, purge, channel and list utilities — all in one place.",
        "sections": [
            {
                "header": "Moderation",
                "commands": [
                    "ban", "fakeban", "softban",
                    "kick", "mute", "unmute",
                    "unban", "nick", "nuke",
                    "unbanall", "snipe",
                ],
            },
            {
                "header": "Lock & Hide",
                "commands": [
                    "lock", "unlock",
                    "lockall", "unlockall",
                    "hide", "unhide",
                    "hideall", "unhideall",
                    "slowmode", "unslowmode",
                ],
            },
            {
                "header": "Purge",
                "commands": [
                    "clear", "clearall",
                    "clearuser", "clearbots",
                    "clearembed", "clearmentions",
                    "clearreactions", "clearfiles",
                    "clearimages", "clearemoji",
                    "clearcontain",
                ],
            },
            {
                "header": "Channel",
                "commands": [
                    "channel create", "channel delete",
                    "channel rename", "channel clone",
                    "channel transfer",
                ],
            },
            {
                "header": "List",
                "commands": [
                    "list hypesquad", "list pending",
                    "list channels", "list timeouts",
                    "list hasperms", "list bans",
                    "list users", "list boosters",
                    "list emojis", "list bots",
                    "list admins", "list mods",
                    "list roles", "list invoice",
                    "list activedeveloper", "list joinedat",
                    "list early", "list inrole",
                    "list createdat", "list bughunters",
                ],
            },
        ],
    },
    "NoPrefix": {
        "emoji": EMOJI_NOPREFIX,
        "description": "Manage NoPrefix access — users that don't need a prefix.",
        "sections": [
            {
                "header": "NoPrefix",
                "commands": [
                    "np", "np add", "np remove",
                    "np list", "np check",
                ],
            },
        ],
    },
    "Premium": {
        "emoji": EMOJI_PREMIUM,
        "description": "Exclusive premium features for boosters and supporters.",
        "sections": [
            {
                "header": "Premium",
                "commands": [
                    "premium", "premstatus", "activate", "custombot",
                ],
            },
        ],
    },
    "ReactionRoles": {
        "emoji": EMOJI_REACTIONROLES,
        "description": "Bind emojis to roles for self-assignment & full role management in bulk.",
        "sections": [
            {
                "header": "Reaction Roles",
                "commands": [
                    "rr add", "rr remove",
                    "rr list", "rr clear",
                ],
            },
            {
                "header": "Role Management",
                "commands": [
                    "role add", "role all",
                    "role bots", "role colour",
                    "role create", "role delete",
                    "role humans", "role remove",
                    "role rename",
                ],
            },
            {
                "header": "Remove Role",
                "commands": [
                    "rrole", "rrole humans",
                    "rrole bots", "rrole all",
                ],
            },
        ],
    },
    "Ticket": {
        "emoji": EMOJI_TICKET,
        "description": "Powerful ticket system for support, applications, and reports.",
        "sections": [
            {
                "header": "Ticket",
                "commands": [
                    "ticket", "ticket setup",
                    "ticket logs", "ticket staff",
                    "ticket category", "ticket config",
                ],
            },
        ],
    },
    "Tracker": {
        "emoji": EMOJI_TRACKER,
        "description": "Track messages, invites, and member activity.",
        "sections": [
            {
                "header": "Messages",
                "commands": [
                    "messages", "addmessages",
                    "removemessages", "resetmessages",
                ],
            },
            {
                "header": "Tracking",
                "commands": [
                    "blacklistchannel", "unblacklistchannel",
                    "blacklistedchannels", "invites",
                    "tracker",
                ],
            },
        ],
    },
}


def _safe_emoji(emoji_str: str):
    if not emoji_str:
        return None
    if emoji_str.startswith("<") and emoji_str.endswith(">"):
        try:
            animated = emoji_str.startswith("<a:")
            parts = emoji_str.strip("<>").split(":")
            name = parts[-2]
            emoji_id = int(parts[-1])
            return discord.PartialEmoji(name=name, id=emoji_id, animated=animated)
        except Exception:
            return None
    return emoji_str


def _build_sections_text(sections: list) -> str:
    blocks = []
    for sec in sections:
        header = sec["header"]
        cmds = sec["commands"]
        cmds_inline = ", ".join(cmds)
        blocks.append(f"__**{header}**__ :\n`{cmds_inline}`")
    return "\n\n".join(blocks)


def _total_commands() -> int:
    total = 0
    for data in CATEGORY_COMMANDS.values():
        for sec in data["sections"]:
            total += len(sec["commands"])
    return total


def _make_container(*items) -> Container:
    return Container(*items, accent_color=ACCENT_COLOR)


class HelpView(LayoutView):
    def __init__(self, bot: commands.Bot, author: discord.Member):
        super().__init__(timeout=180)
        self.bot = bot
        self.author = author
        self.message = None
        container = self._build_home_container()
        self.add_item(container)


    def _create_dropdown(self, default_category: str = None) -> Select:
        options = [
            SelectOption(
                label=category,
                value=category,
                description=f"Get All {category} Commands",
                emoji=_safe_emoji(data["emoji"]),
                default=(category == default_category) if default_category else False
            )
            for category, data in CATEGORY_COMMANDS.items()
        ]

        dropdown = Select(
            placeholder="❯ Select Module From Here",
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id=f"help_select_{id(self)}"
        )
        dropdown.callback = self.on_select
        return dropdown


    def _build_home_container(self) -> Container:
        total_cmds = _total_commands()

        module_lines = [
            f"> {data['emoji']} » {category}"
            for category, data in CATEGORY_COMMANDS.items()
        ]
        modules_text = "\n".join(module_lines)

        welcome_text = (
            f"## Hey, I'm {BOT_NAME}™\n"
            f"{BOT_TAGLINE}\n\n"
            f"- **My Prefix is** `{DEFAULT_PREFIX}`\n"
            f"- **Total Commands:** `282`\n\n"
            f"{modules_text}"
        )

        welcome_section = Section(
            TextDisplay(welcome_text),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description=f"{BOT_NAME}"
            ),
            id=1
        )

        dropdown = self._create_dropdown()

        support_btn = Button(label="Support", style=discord.ButtonStyle.link, url=SUPPORT_URL)
        invite_btn  = Button(label="Invite",  style=discord.ButtonStyle.link, url=INVITE_URL)

        close_btn = Button(
            label="Close",
            style=discord.ButtonStyle.danger,
            custom_id="help_close"
        )
        close_btn.callback = self.on_close

        return _make_container(
            welcome_section,
            Separator(),
            ActionRow(dropdown),
            ActionRow(support_btn, invite_btn, close_btn),
        )


    def _build_category_container(self, category: str) -> Container:
        category_data = CATEGORY_COMMANDS.get(category)
        if not category_data:
            return _make_container(TextDisplay("Category not found."))

        emoji       = category_data["emoji"]
        sections    = category_data["sections"]

        sections_text = _build_sections_text(sections)

        module_text = f"## {emoji} {category}"

        full_text = f"{module_text}\n\n{sections_text}"
        if len(full_text) > 3950:
            sections_text = sections_text[:3900 - len(module_text)] + "\n\n*... and more*"

        header_display = TextDisplay(module_text)

        small_separator = Separator(spacing=discord.SeparatorSpacing.small)

        dropdown = self._create_dropdown(default_category=category)

        back_button = Button(
            label="Home",
            style=discord.ButtonStyle.primary,
            custom_id="help_back_home"
        )
        back_button.callback = self.on_back_home

        close_btn = Button(
            label="Close",
            style=discord.ButtonStyle.danger,
            custom_id="help_close_cat"
        )
        close_btn.callback = self.on_close

        return _make_container(
            header_display,
            small_separator,
            TextDisplay(sections_text),
            Separator(),
            ActionRow(dropdown),
            ActionRow(back_button, close_btn),
        )


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "This help menu isn't for you. Run the `help` command yourself.",
                ephemeral=True
            )
            return False
        return True

    async def on_select(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            selected = interaction.data.get("values", [None])[0]

            if not selected or selected not in CATEGORY_COMMANDS:
                await interaction.followup.send(
                    "No commands found for this category.", ephemeral=True
                )
                return

            container = self._build_category_container(selected)
            self.clear_items()
            self.add_item(container)
            await interaction.followup.edit_message(
                message_id=interaction.message.id, view=self
            )
        except Exception as e:
            print(f"Error in on_select: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        f"An error occurred: {str(e)[:100]}", ephemeral=True
                    )
                except Exception:
                    pass

    async def on_back_home(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            container = self._build_home_container()
            self.clear_items()
            self.add_item(container)
            await interaction.followup.edit_message(
                message_id=interaction.message.id, view=self
            )
        except Exception as e:
            print(f"Error in on_back_home: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        f"An error occurred: {str(e)[:100]}", ephemeral=True
                    )
                except Exception:
                    pass

    async def on_close(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            await interaction.message.delete()
            self.stop()
        except Exception as e:
            print(f"Error in on_close: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        f"An error occurred: {str(e)[:100]}", ephemeral=True
                    )
                except Exception:
                    pass

    async def on_timeout(self):
        try:
            if self.message:
                await self.message.delete()
        except Exception:
            pass


class HelpCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        bot.remove_command("help")

    @commands.command(name="help", aliases=["h", "menu"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def help_command(self, ctx: commands.Context):
        try:
            view = HelpView(self.bot, ctx.author)
            msg = await ctx.send(view=view)
            view.message = msg
            self.logger.info(
                f"Help used by {ctx.author} ({ctx.author.id}) in "
                f"{ctx.guild.name if ctx.guild else 'DM'}"
            )
        except Exception as error:
            self.logger.error(f"Help command error: {error}", exc_info=True)
            try:
                await ctx.send("An error occurred while loading the help menu.")
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
