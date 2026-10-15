import discord
from discord import ui
from utils import emojis as E
from XEON.emojis import E as _EMGR, FALLBACK_EMOJI
import re as _re

def _nav_partial(key: str) -> discord.PartialEmoji:
    s = _EMGR[key]
    m = _re.match(r'<(a)?:([A-Za-z0-9_]+):(\d+)>', s)
    if m:
        return discord.PartialEmoji(name=m.group(2), id=int(m.group(3)), animated=bool(m.group(1)))
    return FALLBACK_EMOJI

BLACK          = discord.Colour(0x000000)
ITEMS_PER_PAGE = 7

NAV_FIRST  = _nav_partial("FIRST")
NAV_PREV   = _nav_partial("PREV")
NAV_DELETE = _nav_partial("DELETE")
NAV_NEXT   = _nav_partial("NEXT")
NAV_LAST   = _nav_partial("LAST")


CATEGORIES = {
    "moderation": {
        "title"   : "moderation",
        "aliases" : ["mod"],
        "commands": [
            ("ban",         "Ban a member from the server."),
            ("fakeban",     "Fake ban a member."),
            ("softban",     "Ban and unban to delete messages."),
            ("kick",        "Kick a member from the server."),
            ("mute",        "Timeout/mute a member."),
            ("unmute",      "Remove timeout from a member."),
            ("unban",       "Unban a user by their ID."),
            ("nick",        "Change a member's nickname."),
            ("nuke",        "Clone and delete a channel."),
            ("unbanall",    "Unban all banned users."),
            ("lock",        "Lock a channel."),
            ("unlock",      "Unlock a channel."),
            ("lockall",     "Lock all text channels."),
            ("unlockall",   "Unlock all text channels."),
            ("hide",        "Hide a channel from members."),
            ("unhide",      "Unhide a channel."),
            ("hideall",     "Hide all text channels."),
            ("unhideall",   "Unhide all text channels."),
            ("slowmode",    "Set slowmode for a channel."),
            ("unslowmode",  "Remove slowmode from a channel."),
            ("snipe",       "Snipe the last deleted message."),
        ],
    },

    "automod": {
        "title"   : "automod",
        "aliases" : ["automodhelp", "amhelp", "spamhelp", "modhelp", "filterhelp"],
        "commands": [
            ("automod",                 "Show the AutoMod main panel."),
            ("automod enable",          "Enable AutoMod on the server."),
            ("automod disable",         "Disable AutoMod on the server."),
            ("automod manage",          "Toggle individual filters on/off."),
            ("automod settings",        "View master settings (heat/punishment)."),
            ("automod rules",           "Show rules for all filters."),
            ("automod reset",           "Reset all AutoMod configuration."),
            ("automod logging",         "Set or reset the AutoMod log channel."),
            ("automod help",            "Show this help panel."),

            ("automod wl channel",      "Whitelist a channel."),
            ("automod wl role",         "Whitelist a role."),
            ("automod wl show",         "View whitelisted channels & roles."),
            ("automod wl reset",        "Clear the whitelist."),

            ("automod bl add",          "Add a blacklisted word."),
            ("automod bl remove",       "Remove a blacklisted word."),
            ("automod bl list",         "View blacklisted words."),
        ],
    },
    "list": {
        "title"   : "list",
        "aliases" : ["ls"],
        "commands": [
            ("list hypesquad",      "Lists members in hypesquad houses."),
            ("list pending",        "Lists members pending membership screening."),
            ("list channels",       "Lists all text channels."),
            ("list timeouts",       "Lists all timed out members."),
            ("list hasperms",       "Lists members with a specific permission."),
            ("list bans",           "Lists all banned users."),
            ("list users",          "Lists all human members."),
            ("list boosters",       "Lists all server boosters."),
            ("list emojis",         "Lists server emojis."),
            ("list bots",           "Lists all bots."),
            ("list admins",         "Lists all admins."),
            ("list mods",           "Lists all moderators."),
            ("list roles",          "Lists all roles with ID and member count."),
            ("list invoice",        "Lists members in a voice channel."),
            ("list activedeveloper","Lists members with Active Developer badge."),
            ("list joinedat",       "Lists members by their join date."),
            ("list early",          "Lists members with the early supporter badge."),
            ("list inrole",         "Lists members with a specific role."),
            ("list createdat",      "Lists members by their account creation date."),
            ("list bughunters",     "Lists members with Bug Hunter badge."),
        ],
    },
    "channel": {
        "title"   : "channel",
        "aliases" : ["ch"],
        "commands": [
            ("channel create",   "Create a new text channel."),
            ("channel delete",   "Delete a channel."),
            ("channel rename",   "Rename current channel."),
            ("channel clone",    "Clone a channel."),
            ("channel transfer", "Move channel to a category."),
        ],
    },
    "role": {
        "title"   : "role",
        "aliases" : ["r"],
        "commands": [
            ("role add",     "Adds a role to a user."),
            ("role all",     "Give the role to all members."),
            ("role bots",    "Give the role to all bot members."),
            ("role colour",  "Changes the color of a role."),
            ("role create", "Creates a new role."),
            ("role delete",  "Deletes a role."),
            ("role humans",  "Give the role to all human members."),
            ("role remove", "Removes a role from a user."),
            ("role rename",  "Renames a role."),
            ("rrole",        "Remove role from all members."),
            ("rrole humans", "Remove role from all humans."),
            ("rrole bots",   "Remove role from all bots."),
            ("rrole all",    "Remove role from absolutely everyone."),
        ],
    },
    "purge": {
        "title"   : "purge",
        "aliases" : ["clear", "clean"],
        "commands": [
            ("clear",          "Clear a number of messages."),
            ("clearall",       "Clear all messages (up to 1000)."),
            ("clearuser",      "Clear messages from a specific user."),
            ("clearbots",      "Clear bot messages."),
            ("clearembed",     "Clear messages with embeds."),
            ("clearmentions",  "Clear messages with mentions."),
            ("clearreactions", "Remove all reactions from messages."),
            ("clearfiles",     "Clear messages with file attachments."),
            ("clearimages",    "Clear messages with images."),
            ("clearemoji",     "Clear messages with custom emojis."),
            ("clearcontain",   "Clear messages containing specific text."),
        ],
    },
    "general": {
        "title"   : "general",
        "aliases" : ["info", "bot"],
        "commands": [
            ("ping",      "Check bot's latency."),
            ("pong",      "Pong!"),
            ("stats",     "View comprehensive bot statistics."),
            ("uptime",    "Check how long bot has been running."),
            ("system",    "View system resource usage."),
        ],
    },


    "embed": {
        "title"   : "embed",
        "aliases" : ["embeds"],
        "commands": [
            ("embed",          "Embed builder root command."),
            ("embed create",   "Open the embed builder modal."),
        ],
    },

    "noprefix": {
        "title"   : "noprefix",
        "aliases" : ["np"],
        "commands": [
            ("np",             "Show NoPrefix help menu."),
            ("np add",         "Add NoPrefix to a user (with plan select)."),
            ("np remove",      "Remove NoPrefix from a user."),
            ("np list",        "Show all active NoPrefix users."),
            ("np check",       "Check a user's NoPrefix status."),
        ],
    },

    "greet": {
        "title"   : "greet",
        "aliases" : ["welcome", "welcomer"],
        "commands": [
            ("greet setup",        "Quick interactive welcome setup."),
            ("greet channel",      "Set welcome channel."),
            ("greet type",         "Set greet type: simple or container."),
            ("greet content",      "Plain text shown above the container."),
            ("greet title",        "Container title."),
            ("greet description",  "Container description body."),
            ("greet color",        "Container accent color (hex)."),
            ("greet thumbnail",    "Container thumbnail image URL."),
            ("greet image",        "Container main image URL."),
            ("greet message",      "Simple-mode message text."),
            ("greet deleteafter",  "Auto-delete welcome after N seconds."),
            ("greet test",         "Send a test welcome message."),
            ("greet config",       "Show current configuration."),
            ("greet variables",    "List supported template variables."),
            ("greet disable",      "Disable welcome messages."),
        ],
    },

    "tracker": {
        "title": "tracker",
        "aliases": ["track"],
        "commands": [
            ("messages",          "Show message count for a user."),
            ("addmessages",       "Add messages to a user's count."),
            ("removemessages",    "Remove messages from a user's count."),
            ("resetmessages",     "Reset messages for user or all."),
            ("blacklistchannel",  "Blacklist channel from tracking."),
            ("unblacklistchannel","Remove channel from blacklist."),
            ("blacklistedchannels","List blacklisted channels."),
            ("invites",           "Show invite stats for a user."),
            ("tracker",           "Show server tracking overview."),
        ],
    },
    "autorole": {
        "title": "autorole",
        "aliases": ["autoroles"],
        "commands": [
            ("autorole humans add",     "Add human autorole."),
            ("autorole humans remove",  "Remove human autorole."),
            ("autorole humans list",    "List human autoroles."),
            ("autorole bots add",       "Add bot autorole."),
            ("autorole bots remove",    "Remove bot autorole."),
            ("autorole bots list",      "List bot autoroles."),
        ],
    },
    "autoresponder": {
        "title": "autoresponder",
        "aliases": ["ar"],
        "commands": [
            ("ar add",            "Add autoresponse (exact match)."),
            ("ar addcontains",    "Trigger if message contains text."),
            ("ar addstart",       "Trigger if message starts with text."),
            ("ar remove",         "Remove an autoresponse."),
            ("ar list",           "List autoresponses."),
            ("ar clear",          "Clear all autoresponses."),
        ],
    },
    "autoreact": {
        "title": "autoreact",
        "aliases": ["arc"],
        "commands": [
            ("arc add",           "Add trigger-based autoreact."),
            ("arc channel",       "Auto-react in entire channel."),
            ("arc remove",        "Remove trigger autoreact."),
            ("arc removechannel", "Remove channel autoreact."),
            ("arc list",          "List all autoreacts."),
            ("arc clear",         "Clear all autoreacts."),
        ],
    },
    "reactionrole": {
        "title": "reactionrole",
        "aliases": ["rr"],
        "commands": [
            ("rr add",            "Bind emoji to role on a message."),
            ("rr remove",         "Remove a reaction role binding."),
            ("rr list",           "List all reaction roles."),
            ("rr clear",          "Clear all reaction roles on a message."),
        ],
    },
    "logging": {
        "title": "logging",
        "aliases": ["log"],
        "commands": [
            ("log setup",         "Set default log channel for all events."),
            ("log set",           "Override per-type log channel."),
            ("log enable",        "Enable a log event type."),
            ("log disable",       "Disable a log event type."),
            ("log config",        "Show current logging config."),
            ("log types",         "List all available event types."),
            ("log reset",         "Reset all logging settings."),
        ],
    },

    "giveaway": {
        "title"   : "giveaway",
        "aliases" : ["g", "gw"],
        "commands": [
            ("giveaway",       "Show giveaway help menu."),
            ("gstart",         "Start a giveaway. `<duration> <winners> <prize>`"),
            ("gend",           "End a giveaway early by message ID."),
            ("greroll",        "Reroll winners for an ended giveaway."),
            ("glist",          "List all active giveaways in this server."),
            ("gdelete",        "Delete a giveaway without picking winners."),
        ],
    },

    "utility": {
        "title"   : "utility",
        "aliases" : ["util", "misc"],
        "commands": [
            ("@mention",       "Mention the bot to see prefix info & links."),
            ("(auto) welcome", "DM owner & post in server when bot joins."),
        ],
    },

    "security": {
        "title"   : "security",
        "aliases" : ["securityhelp", "antinukehelp", "protection", "raidhelp", "nukehelp"],
        "commands": [
            ("antinuke",              "Show the main antinuke panel."),
            ("antinuke enable",       "Enable antinuke and create security role."),
            ("antinuke disable",      "Disable antinuke on the server."),
            ("antinuke wizard",       "Auto-apply recommended antinuke settings."),
            ("antinuke filters",      "Open the filter toggle panel."),
            ("antinuke logs",         "Set the antinuke logs channel."),
            ("antinuke help",         "Show this help panel."),

            ("antinuke wl",           "Open whitelist panel for a user."),
            ("antinuke unwl",         "Remove a user from the whitelist."),
            ("antinuke wlist",        "View all whitelisted users."),
            ("antinuke wlreset",      "Clear the entire whitelist."),

            ("extraowner",            "Show extra owner help menu."),
            ("extraowner set",        "Add a user as extra owner."),
            ("extraowner reset",      "Remove a user from extra owners."),
            ("extraowner view",       "View all extra owners."),
            ("extraowner clear",      "Remove all extra owners."),
        ],
    },
}

CAT_ALIAS_MAP: dict[str, str] = {}
for _key, _data in CATEGORIES.items():
    for _alias in _data.get("aliases", []):
        CAT_ALIAS_MAP[_alias.lower()] = _key


def get_category(name: str) -> tuple[str | None, dict | None]:
    name = name.lower()
    if name in CATEGORIES:
        return name, CATEGORIES[name]
    if name in CAT_ALIAS_MAP:
        real = CAT_ALIAS_MAP[name]
        return real, CATEGORIES[real]
    return None, None


class CategoryHelpView(ui.LayoutView):

    def __init__(
        self,
        ctx,
        category_key : str,
        category_data: dict,
        bot_name     : str,
        prefix       : str,
    ):
        super().__init__(timeout=120)
        self.ctx           = ctx
        self.category_key  = category_key
        self.category_data = category_data
        self.bot_name      = bot_name
        self.prefix        = prefix
        self.page          = 0
        self._rebuild()

    def _total_pages(self) -> int:
        return max(
            1,
            -(-len(self.category_data["commands"]) // ITEMS_PER_PAGE),
        )

    def _build_container(self) -> ui.Container:
        cmds       = self.category_data["commands"]
        total      = self._total_pages()
        start      = self.page * ITEMS_PER_PAGE
        end        = start + ITEMS_PER_PAGE
        page_cmds  = cmds[start:end]
        title      = self.category_data["title"]
        total_cmds = len(cmds)

        container = ui.Container(accent_color=BLACK)

        container.add_item(ui.TextDisplay(
            content=f"**{self.bot_name} {title} [{total_cmds}]**"
        ))

        container.add_item(ui.TextDisplay(
            content="` <..> <required>  |  [..] [optional]`"
        ))
        container.add_item(ui.Separator())
        container.add_item(ui.Separator(visible=False))

        for cmd_name, desc in page_cmds:
            container.add_item(ui.TextDisplay(
                content=f"`{self.prefix}{cmd_name}`"
            ))
            container.add_item(ui.TextDisplay(
                content=f"> {E.ARROW} {desc}"
            ))
            container.add_item(ui.Separator(visible=False))

        container.add_item(ui.Separator())

        container.add_item(ui.TextDisplay(
            content=(
                f"Page `{self.page + 1}/{total}` | "
                f"Requested by {self.ctx.author.name}"
            )
        ))

        return container

    def _build_nav_row(self) -> ui.ActionRow:
        total = self._total_pages()

        nav_row = ui.ActionRow(
            ui.Button(
                emoji=NAV_FIRST,
                style=discord.ButtonStyle.secondary,
                custom_id="ch_first",
                disabled=(self.page == 0),
            ),
            ui.Button(
                emoji=NAV_PREV,
                style=discord.ButtonStyle.secondary,
                custom_id="ch_prev",
                disabled=(self.page == 0),
            ),
            ui.Button(
                emoji=NAV_DELETE,
                style=discord.ButtonStyle.danger,
                custom_id="ch_delete",
            ),
            ui.Button(
                emoji=NAV_NEXT,
                style=discord.ButtonStyle.secondary,
                custom_id="ch_next",
                disabled=(self.page >= total - 1),
            ),
            ui.Button(
                emoji=NAV_LAST,
                style=discord.ButtonStyle.secondary,
                custom_id="ch_last",
                disabled=(self.page >= total - 1),
            ),
        )
        nav_row.children[0].callback = self._first
        nav_row.children[1].callback = self._prev
        nav_row.children[2].callback = self._delete
        nav_row.children[3].callback = self._next
        nav_row.children[4].callback = self._last
        return nav_row

    def _rebuild(self):
        self.clear_items()
        self.add_item(self._build_container())
        self.add_item(self._build_nav_row())

    async def _guard(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                f"{E.DENIED} This is not your help menu!",
                ephemeral=True,
            )
            return False
        return True

    async def _first(self, interaction: discord.Interaction):
        if not await self._guard(interaction): return
        self.page = 0
        self._rebuild()
        await interaction.response.edit_message(view=self)

    async def _prev(self, interaction: discord.Interaction):
        if not await self._guard(interaction): return
        if self.page > 0:
            self.page -= 1
        self._rebuild()
        await interaction.response.edit_message(view=self)

    async def _next(self, interaction: discord.Interaction):
        if not await self._guard(interaction): return
        if self.page < self._total_pages() - 1:
            self.page += 1
        self._rebuild()
        await interaction.response.edit_message(view=self)

    async def _last(self, interaction: discord.Interaction):
        if not await self._guard(interaction): return
        self.page = self._total_pages() - 1
        self._rebuild()
        await interaction.response.edit_message(view=self)

    async def _delete(self, interaction: discord.Interaction):
        if not await self._guard(interaction): return
        await interaction.response.defer()
        try:
            await interaction.message.delete()
        except Exception:
            pass

    async def on_timeout(self):
        pass


async def send_category_help(ctx, category_name: str, bot) -> bool:
    key, data = get_category(category_name)
    if not key or not data:
        return False
    view = CategoryHelpView(
        ctx           = ctx,
        category_key  = key,
        category_data = data,
        bot_name      = bot.BOT_NAME,
        prefix        = ctx.prefix,
    )
    await ctx.send(view=view)
    return True
