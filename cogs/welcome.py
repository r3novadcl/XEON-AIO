import discord
from discord.ext import commands
from discord import ui
import aiosqlite
import asyncio
import re
from pathlib import Path


from XEON.emojis import E as _EMGR, FALLBACK_EMOJI
import re as _re

_LOCAL_KEY_MAP = {
    "success": "SUCCESS",
    "error": "ERROR",
    "info": "INFO",
    "wave": "WAVE",
    "user": "USER",
    "channel": "CHANNEL",
    "settings": "SETTINGS",
    "dot": "DOT",
    "timer": "CLOCK",
    "edit": "EDIT_ICO",
    "trash": "TRASH",
    "color": "COLOR",
    "image": "IMAGE",
    "test": "TEST",
}

def E(key: str) -> discord.PartialEmoji:
    s = _EMGR[_LOCAL_KEY_MAP.get(key, key.upper())]
    m = _re.match(r'<(a)?:([A-Za-z0-9_]+):(\d+)>', s)
    if m:
        return discord.PartialEmoji(name=m.group(2), id=int(m.group(3)), animated=bool(m.group(1)))
    return FALLBACK_EMOJI

def ES(key: str) -> str:
    return _EMGR[_LOCAL_KEY_MAP.get(key, key.upper())]


DB_DIR = Path("db")
DB_PATH = DB_DIR / "welcome.db"

DEFAULT_ACCENT = discord.Colour(0x000000)
DEFAULT_ACCENT_INT = 0x000000


def _ensure_db():
    DB_DIR.mkdir(exist_ok=True)


def _ordinal(n: int) -> str:
    s = ["th", "st", "nd", "rd"]
    v = n % 100
    return str(n) + (s[(v - 20) % 10] if 20 < v and (v - 20) % 10 < len(s) else s[v] if v < len(s) else s[0])


def _resolve_vars(template: str, member: discord.Member) -> str:
    if not template:
        return ""
    guild = member.guild
    member_count = guild.member_count or 1
    join_ts = int(member.joined_at.timestamp()) if member.joined_at else 0
    join_time = f"<t:{join_ts}:F>" if join_ts else "Unknown"

    vars_map = {
        "{user}":          member.mention,
        "{user_name}":     member.name,
        "{user_tag}":      str(member),
        "{user_id}":       str(member.id),
        "{user_avatar}":   str(member.display_avatar.url),
        "{member_count}":  str(member_count),
        "{member_number}": _ordinal(member_count),
        "{server}":        guild.name,
        "{server_id}":     str(guild.id),
        "{join_time}":     join_time,
    }
    for key, value in sorted(vars_map.items(), key=lambda kv: -len(kv[0])):
        template = template.replace(key, value)
    return template


async def init_db():
    _ensure_db()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS welcome (
                guild_id       INTEGER PRIMARY KEY,
                channel_id     INTEGER,
                greet_type     TEXT    DEFAULT 'container',
                message        TEXT,
                content_text   TEXT,
                title          TEXT,
                description    TEXT,
                color          INTEGER,
                thumbnail_url  TEXT,
                image_url      TEXT,
                delete_after   INTEGER,
                enabled        INTEGER DEFAULT 1
            )
        """)
        await db.commit()


async def get_config(guild_id: int) -> dict | None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM welcome WHERE guild_id = ?", (guild_id,)
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def set_config(guild_id: int, **fields):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT OR IGNORE INTO welcome (guild_id) VALUES (?)", (guild_id,)
        )
        for col, val in fields.items():
            await db.execute(
                f"UPDATE welcome SET {col} = ? WHERE guild_id = ?", (val, guild_id)
            )
        await db.commit()


async def delete_config(guild_id: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("DELETE FROM welcome WHERE guild_id = ?", (guild_id,))
        await db.commit()


def _error_view(text: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('error')} {text}"))
    view.add_item(c)
    return view


def _success_view(text: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('success')} {text}"))
    view.add_item(c)
    return view


def _info_view(title: str, body: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('info')} **{title}**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(body))
    view.add_item(c)
    return view


def _config_view(cfg: dict | None, guild: discord.Guild, prefix: str) -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)

    c.add_item(ui.TextDisplay(f"{ES('settings')} **Welcome Configuration**"))
    c.add_item(ui.Separator())

    if not cfg or not cfg.get("channel_id"):
        c.add_item(ui.TextDisplay(
            f"{ES('error')} **Status:** Not set up\n\n"
            f"Use `{prefix}greet setup` to get started."
        ))
        view.add_item(c)
        return view

    ch = guild.get_channel(cfg["channel_id"])
    ch_mention = ch.mention if ch else f"`{cfg['channel_id']}` (deleted)"
    greet_type = cfg.get("greet_type", "container")
    enabled = bool(cfg.get("enabled", 1))
    delete_after = cfg.get("delete_after")
    color = cfg.get("color")

    status_line = f"{ES('success')} **Enabled**" if enabled else f"{ES('error')} **Disabled**"

    c.add_item(ui.TextDisplay(
        f"{ES('dot')} **Status:** {status_line}\n"
        f"{ES('dot')} **Channel:** {ch_mention}\n"
        f"{ES('dot')} **Type:** `{greet_type}`\n"
        f"{ES('dot')} **Color:** `{f'#{color:06X}' if color else '#000000 (default)'}`\n"
        f"{ES('dot')} **Auto-delete:** `{f'{delete_after}s' if delete_after else 'Never'}`"
    ))

    c.add_item(ui.Separator())

    if greet_type == "simple":
        msg = cfg.get("message") or "*(not set — default will be used)*"
        c.add_item(ui.TextDisplay(f"{ES('edit')} **Message:**\n```\n{msg[:500]}\n```"))
    else:
        title = cfg.get("title") or "*(not set)*"
        desc = cfg.get("description") or "*(not set)*"
        content = cfg.get("content_text") or "*(not set — member will be pinged)*"
        thumb = cfg.get("thumbnail_url") or "*(not set)*"
        image = cfg.get("image_url") or "*(not set)*"

        c.add_item(ui.TextDisplay(
            f"{ES('edit')} **Title:** {title}\n"
            f"{ES('edit')} **Description:**\n```\n{desc[:300]}\n```\n"
            f"{ES('edit')} **Content (above):** {content[:100]}\n"
            f"{ES('image')} **Thumbnail:** {thumb[:80]}\n"
            f"{ES('image')} **Image:** {image[:80]}"
        ))

    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(f"-# Use `{prefix}greet variables` to see template variables"))

    view.add_item(c)
    return view


def _variables_view() -> ui.LayoutView:
    view = ui.LayoutView()
    c = ui.Container(accent_color=DEFAULT_ACCENT)
    c.add_item(ui.TextDisplay(f"{ES('info')} **Available Variables**"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(
        "Use these in any text field (message, title, description, content, "
        "thumbnail, image):\n\n"
        f"{ES('dot')} `{{user}}` — Member mention (@User)\n"
        f"{ES('dot')} `{{user_name}}` — Username only\n"
        f"{ES('dot')} `{{user_tag}}` — Full tag (user#1234)\n"
        f"{ES('dot')} `{{user_id}}` — Member's ID\n"
        f"{ES('dot')} `{{user_avatar}}` — Avatar URL (use in thumbnail/image)\n"
        f"{ES('dot')} `{{member_count}}` — Total members (e.g. 100)\n"
        f"{ES('dot')} `{{member_number}}` — Ordinal (e.g. 100th)\n"
        f"{ES('dot')} `{{server}}` — Server name\n"
        f"{ES('dot')} `{{server_id}}` — Server ID\n"
        f"{ES('dot')} `{{join_time}}` — Join timestamp"
    ))
    view.add_item(c)
    return view


def _build_welcome_view(cfg: dict, member: discord.Member) -> tuple[ui.LayoutView | None, str | None]:
    greet_type = cfg.get("greet_type", "container")

    content_text = cfg.get("content_text")
    resolved_content = _resolve_vars(content_text, member) if content_text else None

    if greet_type == "simple":
        template = cfg.get("message") or "Welcome {user} to **{server}**! You are our {member_number} member."
        text = _resolve_vars(template, member)
        return None, text

    title_raw = cfg.get("title") or "Welcome"
    desc_raw = cfg.get("description") or "Welcome {user} to **{server}**!\nYou are our **{member_number}** member."

    title = _resolve_vars(title_raw, member)
    desc = _resolve_vars(desc_raw, member)

    color_int = cfg.get("color") or DEFAULT_ACCENT_INT
    accent = discord.Colour(color_int)

    view = ui.LayoutView(timeout=None)
    c = ui.Container(accent_color=accent)

    ping_line = resolved_content if resolved_content else member.mention
    if ping_line:
        c.add_item(ui.TextDisplay(ping_line))
        c.add_item(ui.Separator(visible=False))

    thumbnail_raw = cfg.get("thumbnail_url")
    thumbnail_url = None
    if thumbnail_raw:
        resolved_thumb = _resolve_vars(thumbnail_raw, member).strip()
        if resolved_thumb.startswith(("http://", "https://")):
            thumbnail_url = resolved_thumb

    header_text = ui.TextDisplay(f"{ES('wave')} **{title}**")

    if thumbnail_url:
        try:
            section = ui.Section(
                header_text,
                accessory=ui.Thumbnail(
                    media=discord.UnfurledMediaItem(url=thumbnail_url)
                ),
            )
            c.add_item(section)
        except Exception:
            c.add_item(header_text)
    else:
        c.add_item(header_text)

    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(desc))

    image_raw = cfg.get("image_url")
    image_url = None
    if image_raw:
        resolved_img = _resolve_vars(image_raw, member).strip()
        if resolved_img.startswith(("http://", "https://")):
            image_url = resolved_img

    if image_url:
        try:
            c.add_item(ui.Separator(visible=False))
            gallery = ui.MediaGallery()
            gallery.add_item(media=discord.UnfurledMediaItem(url=image_url))
            c.add_item(gallery)
        except Exception:
            pass

    c.add_item(ui.Separator(visible=False))
    c.add_item(ui.TextDisplay(
        f"-# {ES('user')} Member #{cfg.get('_member_num', _ordinal(member.guild.member_count or 1))} • "
        f"Joined <t:{int(member.joined_at.timestamp()) if member.joined_at else 0}:R>"
    ))

    view.add_item(c)

    return view, None


class Welcomer(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await init_db()


    @commands.group(name="greet", aliases=["welcome"], invoke_without_command=True)
    @commands.guild_only()
    async def greet(self, ctx: commands.Context):
        try:
            from utils.category_help import send_category_help
            if await send_category_help(ctx, "greet", self.bot):
                return
            if await send_category_help(ctx, "welcome", self.bot):
                return
        except Exception:
            pass

        await ctx.send(view=_info_view(
            "Greet Commands",
            f"`{ctx.prefix}greet setup` — Quick interactive setup\n"
            f"`{ctx.prefix}greet channel #ch` — Set welcome channel\n"
            f"`{ctx.prefix}greet type <simple/container>` — Set greet style\n"
            f"`{ctx.prefix}greet content <text>` — Plain message above container\n"
            f"`{ctx.prefix}greet title <text>` — Container title\n"
            f"`{ctx.prefix}greet description <text>` — Container description\n"
            f"`{ctx.prefix}greet color <#hex>` — Accent color\n"
            f"`{ctx.prefix}greet thumbnail <url>` — Thumbnail image\n"
            f"`{ctx.prefix}greet image <url>` — Main image\n"
            f"`{ctx.prefix}greet message <text>` — Simple mode message\n"
            f"`{ctx.prefix}greet deleteafter <sec>` — Auto-delete (0 = off)\n"
            f"`{ctx.prefix}greet test` — Test the welcome message\n"
            f"`{ctx.prefix}greet config` — Show current settings\n"
            f"`{ctx.prefix}greet variables` — List template variables\n"
            f"`{ctx.prefix}greet disable` — Turn off welcome"
        ))


    @greet.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def greet_setup(self, ctx: commands.Context):
        view = ui.LayoutView(timeout=120)
        c = ui.Container(accent_color=DEFAULT_ACCENT)

        c.add_item(ui.TextDisplay(f"{ES('settings')} **Welcome Setup**"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            "Select a channel where welcome messages will be sent."
        ))
        c.add_item(ui.Separator(visible=False))

        ch_select = ui.ChannelSelect(
            placeholder="Choose a welcome channel...",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        )

        async def on_channel_pick(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message(
                    f"{ES('error')} Not your setup.", ephemeral=True
                )
                return

            ch_id = int(interaction.data["values"][0])
            channel = ctx.guild.get_channel(ch_id)
            if not channel:
                await interaction.response.send_message(
                    f"{ES('error')} Channel not found.", ephemeral=True
                )
                return

            await set_config(
                ctx.guild.id,
                channel_id=ch_id,
                greet_type="container",
                enabled=1,
            )

            done = ui.LayoutView()
            dc = ui.Container(accent_color=DEFAULT_ACCENT)
            dc.add_item(ui.TextDisplay(f"{ES('success')} **Welcome Enabled!**"))
            dc.add_item(ui.Separator())
            dc.add_item(ui.TextDisplay(
                f"{ES('dot')} **Channel:** {channel.mention}\n"
                f"{ES('dot')} **Type:** `container` (default)\n\n"
                f"Customize further:\n"
                f"`{ctx.prefix}greet title <text>`\n"
                f"`{ctx.prefix}greet description <text>`\n"
                f"`{ctx.prefix}greet test` — to test it"
            ))
            done.add_item(dc)

            await interaction.response.edit_message(view=done)

        ch_select.callback = on_channel_pick
        c.add_item(ui.ActionRow(ch_select))

        cancel_btn = ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="setup_cancel",
        )

        async def on_cancel(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message(
                    f"{ES('error')} Not your setup.", ephemeral=True
                )
                return
            cancel_v = ui.LayoutView()
            cc = ui.Container(accent_color=DEFAULT_ACCENT)
            cc.add_item(ui.TextDisplay(f"{ES('error')} Setup cancelled."))
            cancel_v.add_item(cc)
            await interaction.response.edit_message(view=cancel_v)

        cancel_btn.callback = on_cancel
        c.add_item(ui.ActionRow(cancel_btn))

        view.add_item(c)
        await ctx.send(view=view)


    @greet.command(name="channel")
    @commands.has_permissions(administrator=True)
    async def greet_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await set_config(ctx.guild.id, channel_id=channel.id, enabled=1)
        await ctx.send(view=_success_view(f"Welcome channel set to {channel.mention}"))


    @greet.command(name="type")
    @commands.has_permissions(administrator=True)
    async def greet_type(self, ctx: commands.Context, mode: str):
        mode = mode.lower()
        if mode not in ("simple", "container"):
            await ctx.send(view=_error_view("Type must be `simple` or `container`."))
            return
        await set_config(ctx.guild.id, greet_type=mode)
        await ctx.send(view=_success_view(f"Greet type set to `{mode}`"))


    @greet.command(name="content")
    @commands.has_permissions(administrator=True)
    async def greet_content(self, ctx: commands.Context, *, text: str = None):
        val = None if (text is None or text.lower() == "none") else text
        await set_config(ctx.guild.id, content_text=val)
        if val:
            await ctx.send(view=_success_view(f"Content set:\n> {val[:200]}"))
        else:
            await ctx.send(view=_success_view("Content cleared. Member will be pinged by default."))


    @greet.command(name="title")
    @commands.has_permissions(administrator=True)
    async def greet_title(self, ctx: commands.Context, *, title: str):
        await set_config(ctx.guild.id, title=title)
        await ctx.send(view=_success_view(f"Title set: **{title[:100]}**"))


    @greet.command(name="description", aliases=["desc"])
    @commands.has_permissions(administrator=True)
    async def greet_description(self, ctx: commands.Context, *, description: str):
        await set_config(ctx.guild.id, description=description)
        await ctx.send(view=_success_view(f"Description updated ({len(description)} chars)."))


    @greet.command(name="color", aliases=["colour"])
    @commands.has_permissions(administrator=True)
    async def greet_color(self, ctx: commands.Context, color: str):
        match = re.match(r"^#?([0-9A-Fa-f]{6})$", color.strip())
        if not match:
            await ctx.send(view=_error_view("Invalid hex color. Example: `#000000` or `5865F2`"))
            return
        color_int = int(match.group(1), 16)
        await set_config(ctx.guild.id, color=color_int)
        await ctx.send(view=_success_view(f"Accent color set to `#{match.group(1).upper()}`"))


    @greet.command(name="thumbnail", aliases=["thumb"])
    @commands.has_permissions(administrator=True)
    async def greet_thumbnail(self, ctx: commands.Context, *, url: str):
        url = url.strip()

        if url.lower() == "none":
            await set_config(ctx.guild.id, thumbnail_url=None)
            await ctx.send(view=_success_view("Thumbnail cleared."))
            return

        is_url = url.startswith(("http://", "https://"))
        is_variable = "{" in url and "}" in url

        if not (is_url or is_variable):
            await ctx.send(view=_error_view(
                "Provide a valid URL (`http://` / `https://`) "
                "or a variable like `{user_avatar}`."
            ))
            return

        await set_config(ctx.guild.id, thumbnail_url=url)
        await ctx.send(view=_success_view(
            f"Thumbnail updated to: `{url[:100]}`"
        ))


    @greet.command(name="image", aliases=["img"])
    @commands.has_permissions(administrator=True)
    async def greet_image(self, ctx: commands.Context, *, url: str):
        url = url.strip()

        if url.lower() == "none":
            await set_config(ctx.guild.id, image_url=None)
            await ctx.send(view=_success_view("Image cleared."))
            return

        is_url = url.startswith(("http://", "https://"))
        is_variable = "{" in url and "}" in url

        if not (is_url or is_variable):
            await ctx.send(view=_error_view(
                "Provide a valid URL (`http://` / `https://`) "
                "or a variable like `{user_avatar}`."
            ))
            return

        await set_config(ctx.guild.id, image_url=url)
        await ctx.send(view=_success_view(
            f"Image updated to: `{url[:100]}`"
        ))


    @greet.command(name="message", aliases=["msg"])
    @commands.has_permissions(administrator=True)
    async def greet_message(self, ctx: commands.Context, *, message: str):
        await set_config(ctx.guild.id, message=message)
        await ctx.send(view=_success_view(f"Simple message updated ({len(message)} chars)."))


    @greet.command(name="deleteafter", aliases=["da"])
    @commands.has_permissions(administrator=True)
    async def greet_deleteafter(self, ctx: commands.Context, seconds: int):
        if seconds < 0:
            await ctx.send(view=_error_view("Seconds must be 0 or greater."))
            return
        val = seconds if seconds > 0 else None
        await set_config(ctx.guild.id, delete_after=val)
        if val:
            await ctx.send(view=_success_view(f"Auto-delete set to **{seconds}s**"))
        else:
            await ctx.send(view=_success_view("Auto-delete disabled."))


    @greet.command(name="test")
    @commands.has_permissions(administrator=True)
    async def greet_test(self, ctx: commands.Context):
        cfg = await get_config(ctx.guild.id)
        if not cfg or not cfg.get("channel_id"):
            await ctx.send(view=_error_view(
                f"Welcome not configured. Use `{ctx.prefix}greet setup` first."
            ))
            return

        channel = ctx.guild.get_channel(cfg["channel_id"])
        if not channel:
            await ctx.send(view=_error_view("Welcome channel no longer exists."))
            return

        try:
            await self._send_welcome(channel, ctx.author, cfg)
            await ctx.send(view=_success_view(f"Test welcome sent to {channel.mention}"))
        except Exception as e:
            await ctx.send(view=_error_view(f"Failed: `{e}`"))


    @greet.command(name="config", aliases=["settings", "show"])
    @commands.has_permissions(administrator=True)
    async def greet_config(self, ctx: commands.Context):
        cfg = await get_config(ctx.guild.id)
        await ctx.send(view=_config_view(cfg, ctx.guild, ctx.prefix))


    @greet.command(name="variables", aliases=["vars"])
    async def greet_variables(self, ctx: commands.Context):
        await ctx.send(view=_variables_view())


    @greet.command(name="disable", aliases=["off", "reset"])
    @commands.has_permissions(administrator=True)
    async def greet_disable(self, ctx: commands.Context):
        cfg = await get_config(ctx.guild.id)
        if not cfg:
            await ctx.send(view=_error_view("Welcome is not configured."))
            return

        view = ui.LayoutView(timeout=60)
        c = ui.Container(accent_color=DEFAULT_ACCENT)
        c.add_item(ui.TextDisplay(f"{ES('error')} **Confirm Disable**"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(
            "Are you sure you want to disable welcome messages?\n"
            "All your settings will be deleted."
        ))

        confirm_btn = ui.Button(label="Confirm", style=discord.ButtonStyle.danger, custom_id="dis_yes")
        cancel_btn = ui.Button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="dis_no")

        async def on_confirm(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message(f"{ES('error')} Not yours.", ephemeral=True)
                return
            await delete_config(ctx.guild.id)
            done_v = ui.LayoutView()
            dc = ui.Container(accent_color=DEFAULT_ACCENT)
            dc.add_item(ui.TextDisplay(f"{ES('success')} Welcome messages disabled."))
            done_v.add_item(dc)
            await interaction.response.edit_message(view=done_v)

        async def on_cancel(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message(f"{ES('error')} Not yours.", ephemeral=True)
                return
            cancel_v = ui.LayoutView()
            cc = ui.Container(accent_color=DEFAULT_ACCENT)
            cc.add_item(ui.TextDisplay(f"{ES('info')} Cancelled."))
            cancel_v.add_item(cc)
            await interaction.response.edit_message(view=cancel_v)

        confirm_btn.callback = on_confirm
        cancel_btn.callback = on_cancel
        c.add_item(ui.ActionRow(confirm_btn, cancel_btn))

        view.add_item(c)
        await ctx.send(view=view)


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        cfg = await get_config(member.guild.id)
        if not cfg or not cfg.get("enabled") or not cfg.get("channel_id"):
            return

        channel = self.bot.get_channel(cfg["channel_id"])
        if not channel:
            return

        try:
            await self._send_welcome(channel, member, cfg)
        except Exception as e:
            print(f"[Welcomer] Failed to send welcome: {e}")


    async def _send_welcome(
        self,
        channel: discord.TextChannel,
        member: discord.Member,
        cfg: dict,
    ):
        view, content = _build_welcome_view(cfg, member)

        allowed = discord.AllowedMentions(
            users=[member],
            roles=False,
            everyone=False,
        )

        sent_msg = None

        if view is not None:
            sent_msg = await channel.send(
                view=view,
                allowed_mentions=allowed,
            )
        else:
            if not content:
                content = f"Welcome {member.mention}!"
            sent_msg = await channel.send(
                content=content,
                allowed_mentions=allowed,
            )

        delete_after = cfg.get("delete_after")
        if sent_msg and delete_after and delete_after > 0:
            await asyncio.sleep(delete_after)
            try:
                await sent_msg.delete()
            except (discord.NotFound, discord.Forbidden):
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcomer(bot))
