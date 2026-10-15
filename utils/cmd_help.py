import discord
from discord import ui

BLACK = discord.Colour(0x000000)

CMD_DATA = {
    "kick":          ("kick <member> [reason]",       "Kick a member from the server.",              ["kickmember"]),
    "ban":           ("ban <member> [reason]",         "Ban a member from the server.",               ["banmember"]),
    "unban":         ("unban <user_id> [reason]",      "Unban a user by their ID.",                   []),
    "softban":       ("softban <member> [reason]",     "Ban and unban to delete messages.",           []),
    "fakeban":       ("fakeban <member> [reason]",     "Fake ban a member.",                          []),
    "mute":          ("mute <member> [dur] [reason]",  "Timeout a member. e.g. 10m, 2h, 1d",         ["timeout"]),
    "unmute":        ("unmute <member> [reason]",      "Remove timeout from a member.",               ["untimeout"]),
    "nick":          ("nick <member> [nickname]",      "Change a member's nickname.",                 ["nickname"]),
    "lock":          ("lock [channel] [reason]",       "Lock a channel.",                             []),
    "unlock":        ("unlock [channel] [reason]",     "Unlock a channel.",                           []),
    "lockall":       ("lockall [reason]",              "Lock all text channels.",                     []),
    "unlockall":     ("unlockall [reason]",            "Unlock all text channels.",                   []),
    "hide":          ("hide [channel]",                "Hide a channel from members.",                []),
    "unhide":        ("unhide [channel]",              "Unhide a channel.",                           []),
    "hideall":       ("hideall",                       "Hide all text channels.",                     []),
    "unhideall":     ("unhideall",                     "Unhide all text channels.",                   []),
    "slowmode":      ("slowmode <seconds> [channel]",  "Set slowmode for a channel.",                 ["slow"]),
    "unslowmode":    ("unslowmode [channel]",          "Remove slowmode from a channel.",             ["unslow"]),
    "nuke":          ("nuke [channel]",                "Clone and delete a channel.",                 []),
    "snipe":         ("snipe",                         "Snipe the last deleted message.",             []),
    "unbanall":      ("unbanall",                      "Unban all banned users.",                     []),

    "channel":       ("channel <subcommand>",          "Channel management commands.",                ["ch"]),

    "role":          ("role <member> <role>",          "Toggle a role on a member.",                  ["r"]),
    "rrole":         ("rrole <role>",                  "Remove role from all members.",               []),
    "rrolehumans":   ("rrolehumans <role>",            "Remove role from all humans.",                ["rrolehuman"]),
    "rrolebots":     ("rrolebots <role>",              "Remove role from all bots.",                  ["rrolebot"]),
    "rroleall":      ("rroleall <role>",               "Remove role from absolutely everyone.",       []),

    "clear":         ("clear <amount>",                "Clear a number of messages.",                 ["purge", "clean"]),
    "clearall":      ("clearall",                      "Clear all messages (up to 1000).",            ["purgeall"]),
    "clearuser":     ("clearuser <member> [amount]",   "Clear messages from a specific user.",        ["purgeuser"]),
    "clearbots":     ("clearbots [amount]",            "Clear bot messages.",                         ["purgebots"]),
    "clearembed":    ("clearembed [amount]",           "Clear messages with embeds.",                 ["clearembeds"]),
    "clearmentions": ("clearmentions [amount]",        "Clear messages with mentions.",               []),
    "clearreactions":("clearreactions [amount]",       "Remove all reactions from messages.",         []),
    "clearfiles":    ("clearfiles [amount]",           "Clear messages with attachments.",            []),
    "clearimages":   ("clearimages [amount]",          "Clear messages with images.",                 []),
    "clearemoji":    ("clearemoji [amount]",           "Clear messages with custom emojis.",          []),
    "clearcontain":  ("clearcontain <text>",           "Clear messages containing text.",             []),

    "ping":          ("ping",                          "Check bot latency.",                          ["latency", "ms"]),
    "pong":          ("pong",                          "Pong!",                                       []),
    "stats":         ("stats",                         "View comprehensive bot statistics.",           ["botstats", "botinfo", "bi"]),
    "uptime":        ("uptime",                        "Check how long bot has been running.",        ["up"]),
    "system":        ("system",                        "View system resource usage.",                 ["sys"]),
    "container":     ("container",                     "Build and send a Components V2 container.",   ["build", "cb"]),
    "help":          ("help [command/category]",        "Shows the help menu.",                       ["h", "commands"]),
}

ALIAS_MAP = {}
for cmd_name, (usage, desc, aliases) in CMD_DATA.items():
    for alias in aliases:
        ALIAS_MAP[alias] = cmd_name


def get_cmd_info(name: str):
    name = name.lower()
    if name in CMD_DATA:
        return name, CMD_DATA[name]
    if name in ALIAS_MAP:
        real = ALIAS_MAP[name]
        return real, CMD_DATA[real]
    return None, None


def cmd_usage_view(prefix: str, cmd_name: str) -> ui.LayoutView:
    _, info = get_cmd_info(cmd_name)
    if not info:
        return None

    usage, desc, aliases = info

    container = ui.Container(accent_color=BLACK)

    container.add_item(ui.TextDisplay(
        content="`<..> <required>` | `[..] [optional]`"
    ))
    container.add_item(ui.Separator())

    container.add_item(ui.TextDisplay(
        content=f"`{prefix}{usage}`"
    ))
    container.add_item(ui.Separator(visible=False))

    if aliases:
        alias_str = ", ".join(f"`{a}`" for a in aliases)
        container.add_item(ui.TextDisplay(
            content=f"> **Aliases :** {alias_str}"
        ))

    container.add_item(ui.TextDisplay(
        content=f"> {desc}"
    ))

    view = ui.LayoutView(timeout=None)
    view.add_item(container)
    return view
