import discord
from discord.ext import commands
from discord.ui import (
    LayoutView, Container, TextDisplay, Separator,
    ActionRow, Button
)
import json
import os
from XEON.emojis import E, FALLBACK_EMOJI, partial
from utils.config import DEFAULT_PREFIX


ACCENT   = 0x000001
DATA_DIR = "data"

PREFIX_FILE  = os.path.join(DATA_DIR, "prefixes.json")
IGNORE_FILE  = os.path.join(DATA_DIR, "ignored_channels.json")

def _partial_from_e(key: str) -> discord.PartialEmoji:
    import re as _re
    m = _re.match(r"<a?:([A-Za-z0-9_]+):(\d+)>", E[key])
    if m:
        return discord.PartialEmoji(name=m.group(1), id=int(m.group(2)))
    return FALLBACK_EMOJI

TICK    = E.SUCCESS
CROSS   = E.ERROR
ARROW   = E.ARROW
WARN    = E.WARNING
LOADING = E.LOADING

TICK_EMOJI  = _partial_from_e("SUCCESS")
CROSS_EMOJI = _partial_from_e("ERROR")
ARROW_EMOJI = _partial_from_e("ARROW")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(path: str, data: dict):
    _ensure_dir()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_prefix(guild_id: int) -> str:
    data = _load_json(PREFIX_FILE)
    return data.get(str(guild_id), DEFAULT_PREFIX)


def set_prefix(guild_id: int, prefix: str):
    data = _load_json(PREFIX_FILE)
    data[str(guild_id)] = prefix
    _save_json(PREFIX_FILE, data)


def reset_prefix(guild_id: int):
    data = _load_json(PREFIX_FILE)
    data.pop(str(guild_id), None)
    _save_json(PREFIX_FILE, data)


def get_ignored(guild_id: int) -> list:
    data = _load_json(IGNORE_FILE)
    return data.get(str(guild_id), [])


def toggle_ignore(guild_id: int, channel_id: int) -> bool:
    data     = _load_json(IGNORE_FILE)
    ignored  = data.get(str(guild_id), [])

    if channel_id in ignored:
        ignored.remove(channel_id)
        added = False
    else:
        ignored.append(channel_id)
        added = True

    data[str(guild_id)] = ignored
    _save_json(IGNORE_FILE, data)
    return added


def is_ignored(guild_id: int, channel_id: int) -> bool:
    return channel_id in get_ignored(guild_id)


def get_guild_prefix(bot, message: discord.Message):
    if not message.guild:
        return DEFAULT_PREFIX
    return get_prefix(message.guild.id)


def _success_container(title: str, body: str) -> Container:
    return Container(
        TextDisplay(f"### {TICK} {title}\n{ARROW} {body}"),
        accent_color=ACCENT,
    )


def _denied_container(reason: str) -> Container:
    return Container(
        TextDisplay(f"### {WARN} Access Denied\n{CROSS} {reason}"),
        accent_color=ACCENT,
    )


def _info_container(text: str) -> Container:
    return Container(
        TextDisplay(text),
        accent_color=ACCENT,
    )


class PrefixResetView(LayoutView):
    def __init__(self, guild_id: int, author_id: int):
        super().__init__(timeout=30)
        self.guild_id  = guild_id
        self.author_id = author_id
        self._build()

    def _build(self):
        self.clear_items()

        yes_btn = Button(
            emoji     = TICK_EMOJI,
            label     = "Yes, Reset",
            style     = discord.ButtonStyle.danger,
            custom_id = "prefix_reset_yes",
        )
        yes_btn.callback = self._yes

        no_btn = Button(
            emoji     = CROSS_EMOJI,
            label     = "Cancel",
            style     = discord.ButtonStyle.secondary,
            custom_id = "prefix_reset_no",
        )
        no_btn.callback = self._no

        container = Container(
            TextDisplay(
                f"### {WARN} Reset Prefix?\n"
                f"{ARROW} This will reset the prefix back to `{DEFAULT_PREFIX}`\n"
                f"{ARROW} Are you sure?"
            ),
            Separator(),
            ActionRow(yes_btn, no_btn),
            accent_color=ACCENT,
        )
        self.add_item(container)

    async def _yes(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("This is not your panel."))
            return await interaction.response.send_message(view=v, ephemeral=True)

        reset_prefix(self.guild_id)

        v = LayoutView(timeout=None)
        v.add_item(_success_container(
            "Prefix Reset",
            f"Prefix has been reset to `{DEFAULT_PREFIX}`"
        ))
        await interaction.response.edit_message(view=v)
        self.stop()

    async def _no(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("This is not your panel."))
            return await interaction.response.send_message(view=v, ephemeral=True)

        v = LayoutView(timeout=None)
        v.add_item(_info_container(f"{CROSS} Reset cancelled."))
        await interaction.response.edit_message(view=v)
        self.stop()


class IgnoreListView(LayoutView):
    def __init__(self, guild: discord.Guild, author_id: int, page: int = 0):
        super().__init__(timeout=60)
        self.guild     = guild
        self.author_id = author_id
        self.page      = page
        self.per_page  = 10
        self._build()

    def _build(self):
        self.clear_items()

        ignored     = get_ignored(self.guild.id)
        total_pages = max(1, -(-len(ignored) // self.per_page))
        self.page   = max(0, min(self.page, total_pages - 1))

        start = self.page * self.per_page
        chunk = ignored[start:start + self.per_page]

        if not ignored:
            lines = f"{CROSS} No channels are currently ignored."
        else:
            entries = []
            for i, ch_id in enumerate(chunk, start=start + 1):
                ch = self.guild.get_channel(ch_id)
                if ch:
                    entries.append(f"`{i:02d}.` {ch.mention} (`{ch.id}`)")
                else:
                    entries.append(f"`{i:02d}.` Unknown (`{ch_id}`)")
            lines = "\n".join(entries)

        body = (
            f"### {ARROW} Ignored Channels [{len(ignored)}]\n\n"
            f"{lines}"
        )

        components = [TextDisplay(body)]

        if len(ignored) > self.per_page:
            components.append(Separator())
            components.append(TextDisplay(f"-# Page {self.page + 1}/{total_pages}"))
            components.append(Separator())

            prev_btn = Button(
                emoji     = partial("BACKWARD"),
                style     = discord.ButtonStyle.secondary,
                custom_id = "ign_prev",
                disabled  = (self.page <= 0),
            )
            prev_btn.callback = self._prev

            next_btn = Button(
                emoji     = partial("SKIP"),
                style     = discord.ButtonStyle.secondary,
                custom_id = "ign_next",
                disabled  = (self.page >= total_pages - 1),
            )
            next_btn.callback = self._next

            page_btn = Button(
                label     = f"{self.page + 1}/{total_pages}",
                style     = discord.ButtonStyle.secondary,
                custom_id = "ign_page",
                disabled  = True,
            )

            components.append(ActionRow(prev_btn, page_btn, next_btn))

        self.add_item(Container(*components, accent_color=ACCENT))

    async def _prev(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("This is not your panel."))
            return await interaction.response.send_message(view=v, ephemeral=True)
        self.page -= 1
        self._build()
        await interaction.response.edit_message(view=self)

    async def _next(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("This is not your panel."))
            return await interaction.response.send_message(view=v, ephemeral=True)
        self.page += 1
        self._build()
        await interaction.response.edit_message(view=self)


class Prefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def bot_check(self, ctx: commands.Context) -> bool:
        if not ctx.guild:
            return True

        if ctx.command and ctx.command.qualified_name in ("ignore", "unignore", "ignorelist"):
            return True

        if is_ignored(ctx.guild.id, ctx.channel.id):
            v = LayoutView(timeout=None)
            v.add_item(Container(
                TextDisplay(
                    f"### {WARN} Channel Ignored\n"
                    f"{CROSS} Commands are disabled in this channel.\n"
                    f"{ARROW} An administrator can run `{ctx.prefix}ignore #{ctx.channel.name}` to unignore."
                ),
                accent_color=ACCENT,
            ))
            try:
                await ctx.send(view=v, delete_after=8)
            except Exception:
                pass
            return False

        return True


    @commands.command(name="prefix")
    @commands.guild_only()
    async def prefix_cmd(self, ctx: commands.Context):
        current = get_prefix(ctx.guild.id)

        v = LayoutView(timeout=None)
        v.add_item(Container(
            TextDisplay(
                f"### {ARROW} Server Prefix\n\n"
                f"{TICK} **Current Prefix:** `{current}`\n"
                f"{ARROW} **Default Prefix:** `{DEFAULT_PREFIX}`\n\n"
                f"-# Use `{current}setprefix <new>` to change\n"
                f"-# Use `{current}resetprefix` to reset to default"
            ),
            accent_color=ACCENT,
        ))
        await ctx.send(view=v)


    @commands.command(name="setprefix")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setprefix_cmd(self, ctx: commands.Context, *, new_prefix: str = None):
        if not new_prefix:
            v = LayoutView(timeout=None)
            v.add_item(_denied_container(
                f"Please provide a new prefix.\n"
                f"Usage: `{ctx.prefix}setprefix <new prefix>`"
            ))
            return await ctx.send(view=v)

        new_prefix = new_prefix.strip()

        if len(new_prefix) > 5:
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("Prefix can't be longer than **5 characters**."))
            return await ctx.send(view=v)

        if new_prefix == get_prefix(ctx.guild.id):
            v = LayoutView(timeout=None)
            v.add_item(_denied_container(f"Prefix is already set to `{new_prefix}`"))
            return await ctx.send(view=v)

        if " " in new_prefix:
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("Prefix can't contain **spaces**."))
            return await ctx.send(view=v)

        old_prefix = get_prefix(ctx.guild.id)
        set_prefix(ctx.guild.id, new_prefix)

        v = LayoutView(timeout=None)
        v.add_item(Container(
            TextDisplay(
                f"### {TICK} Prefix Updated\n\n"
                f"{ARROW} **Old Prefix:** `{old_prefix}`\n"
                f"{TICK} **New Prefix:** `{new_prefix}`\n\n"
                f"-# All commands now use `{new_prefix}` in this server"
            ),
            accent_color=ACCENT,
        ))
        await ctx.send(view=v)

    @setprefix_cmd.error
    async def setprefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("You need **Administrator** permission to change the prefix."))
            await ctx.send(view=v)


    @commands.command(name="resetprefix")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def resetprefix_cmd(self, ctx: commands.Context):
        current = get_prefix(ctx.guild.id)

        if current == DEFAULT_PREFIX:
            v = LayoutView(timeout=None)
            v.add_item(_denied_container(f"Prefix is already the default `{DEFAULT_PREFIX}`"))
            return await ctx.send(view=v)

        view = PrefixResetView(ctx.guild.id, ctx.author.id)
        await ctx.send(view=view)

    @resetprefix_cmd.error
    async def resetprefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("You need **Administrator** permission."))
            await ctx.send(view=v)


    @commands.command(name="ignore")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ignore_cmd(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel = None,
    ):
        if not channel:
            v = LayoutView(timeout=None)
            v.add_item(_denied_container(
                f"Please mention a channel.\n"
                f"Usage: `{ctx.prefix}ignore #channel`"
            ))
            return await ctx.send(view=v)

        added = toggle_ignore(ctx.guild.id, channel.id)

        if added:
            v = LayoutView(timeout=None)
            v.add_item(Container(
                TextDisplay(
                    f"### {TICK} Channel Ignored\n\n"
                    f"{ARROW} {channel.mention} has been **ignored**.\n"
                    f"{CROSS} Bot will not respond to any commands in that channel.\n\n"
                    f"-# Run `{ctx.prefix}ignore #{channel.name}` again to unignore"
                ),
                accent_color=ACCENT,
            ))
        else:
            v = LayoutView(timeout=None)
            v.add_item(Container(
                TextDisplay(
                    f"### {TICK} Channel Unignored\n\n"
                    f"{ARROW} {channel.mention} has been **unignored**.\n"
                    f"{TICK} Bot will now respond to commands in that channel."
                ),
                accent_color=ACCENT,
            ))

        await ctx.send(view=v)

    @ignore_cmd.error
    async def ignore_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("You need **Administrator** permission."))
            await ctx.send(view=v)
        elif isinstance(error, commands.ChannelNotFound):
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("Channel not found. Please mention a valid text channel."))
            await ctx.send(view=v)


    @commands.command(name="ignorelist", aliases=["ignoredchannels", "ignlist"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def ignorelist_cmd(self, ctx: commands.Context):
        view = IgnoreListView(ctx.guild, ctx.author.id)
        await ctx.send(view=view)

    @ignorelist_cmd.error
    async def ignorelist_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("You need **Manage Server** permission."))
            await ctx.send(view=v)


    @commands.command(name="unignore")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def unignore_cmd(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel = None,
    ):
        if not channel:
            v = LayoutView(timeout=None)
            v.add_item(_denied_container(
                f"Please mention a channel.\n"
                f"Usage: `{ctx.prefix}unignore #channel`"
            ))
            return await ctx.send(view=v)

        ignored = get_ignored(ctx.guild.id)

        if channel.id not in ignored:
            v = LayoutView(timeout=None)
            v.add_item(_denied_container(f"{channel.mention} is not ignored."))
            return await ctx.send(view=v)

        toggle_ignore(ctx.guild.id, channel.id)

        v = LayoutView(timeout=None)
        v.add_item(_success_container(
            "Channel Unignored",
            f"{channel.mention} has been **unignored**. Bot will now respond there."
        ))
        await ctx.send(view=v)

    @unignore_cmd.error
    async def unignore_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            v = LayoutView(timeout=None)
            v.add_item(_denied_container("You need **Administrator** permission."))
            await ctx.send(view=v)


async def setup(bot):
    await bot.add_cog(Prefix(bot))
