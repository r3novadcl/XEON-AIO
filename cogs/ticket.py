import discord
from discord import ui
from discord.ext import commands
import json
import os
import io
import asyncio
import traceback
from datetime import datetime
from XEON.emojis import E as _EMGR, FALLBACK_EMOJI
import re as _re

def _mgr_partial(key: str) -> discord.PartialEmoji:
    s = _EMGR[key]
    m = _re.match(r'<(a)?:([A-Za-z0-9_]+):(\d+)>', s)
    if m:
        return discord.PartialEmoji(name=m.group(2), id=int(m.group(3)), animated=bool(m.group(1)))
    return FALLBACK_EMOJI


E_TICKET     = _mgr_partial("TICKET")
E_SUCCESS    = _mgr_partial("SUCCESS")
E_ERROR      = _mgr_partial("ERROR")
E_LOCK       = _mgr_partial("VM_LOCK")
E_UNLOCK     = _mgr_partial("VM_UNLOCK")
E_CLAIM      = _mgr_partial("VM_CLAIM")
E_CLOSE      = _mgr_partial("VM_BAN")
E_DELETE     = _mgr_partial("DELETE")
E_REOPEN     = _mgr_partial("VM_RENAME")
E_TRANSCRIPT = _mgr_partial("GLOBAL")

S_FILTER     = _EMGR["GLOBAL"]
S_DOT        = _EMGR["ARROW"]
S_PLAYLIST   = _EMGR["GLOBAL"]
S_ARROW_R    = _EMGR["ARROW"]
S_INFO       = _EMGR["ARROW"]
S_FAVOURITE  = _EMGR["ARROW"]
S_SUCCESS    = _EMGR["SUCCESS"]
S_ERROR      = _EMGR["ERROR"]


BLACK     = discord.Colour(0x000000)
DATA_DIR  = "data"
DATA_FILE = os.path.join(DATA_DIR, "tickets.json")

COMMON_PREFIXES = ("&", "!", ".", "?", ";", ",", "+", "-", ">", "$")

OPEN_CATEGORY_NAME   = "Xeon Tickets"
CLOSED_CATEGORY_NAME = "Closed Tickets"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def load_data() -> dict:
    try:
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w") as f:
                f.write("{}")
            return {}
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_guild_data(guild_id: int) -> dict:
    data = load_data()
    gid  = str(guild_id)
    if gid not in data:
        data[gid] = {
            "panel": {
                "title":         "Support Tickets",
                "description":   (
                    "Need help? Select a category below to open a ticket.\n"
                    "Our staff will assist you shortly."
                ),
                "placeholder":   "Select a category to open ticket",
                "thumbnail":     None,
                "image":         None,
                "enabled":       True,
                "logChannel":    None,
                "maxTickets":    3,
                "ticketMessage": "Welcome {user}! Please describe your issue and staff will assist you shortly.",
            },
            "categories":          [],
            "tickets":             {},
            "staffRoles":          [],
            "totalTickets":        0,
            "openCategoryId":      None,
            "closedCategoryId":    None,
        }
        save_data(data)
    return data[gid]


async def _get_or_create_category(
    guild: discord.Guild,
    gd: dict,
    key: str,
    name: str,
    staff_role_ids: list = None,
) -> discord.CategoryChannel | None:
    data = load_data()
    gid  = str(guild.id)
    if gid not in data:
        data[gid] = gd

    cat_id = data[gid].get(key)
    category = None

    if cat_id:
        category = guild.get_channel(int(cat_id))
        if category and isinstance(category, discord.CategoryChannel):
            return category
        data[gid][key] = None

    for c in guild.categories:
        if c.name.lower() == name.lower():
            data[gid][key] = c.id
            save_data(data)
            return c

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, manage_channels=True, send_messages=True,
                read_message_history=True,
            ),
        }
        if staff_role_ids:
            for rid in staff_role_ids:
                role = guild.get_role(int(rid))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True,
                        read_message_history=True,
                    )

        category = await guild.create_category(
            name=name,
            overwrites=overwrites,
            reason="Auto-created by ticket system",
        )
        data[gid][key] = category.id
        save_data(data)
        return category
    except discord.Forbidden:
        print(f"[ticket] No permission to create category '{name}'")
        return None
    except Exception as e:
        print(f"[ticket] Failed to create category '{name}': {e}")
        return None


def quick_view(text: str) -> ui.LayoutView:
    v = ui.LayoutView(timeout=None)
    c = ui.Container(accent_color=BLACK)
    c.add_item(ui.TextDisplay(content=text))
    v.add_item(c)
    return v


def _safe_emoji_for_bot(bot: commands.Bot, emoji_str: str):
    if not emoji_str:
        return None
    if not emoji_str.startswith("<"):
        return emoji_str
    try:
        partial = discord.PartialEmoji.from_str(emoji_str)
        if partial.id is None:
            return emoji_str
        emoji_obj = bot.get_emoji(partial.id)
        if emoji_obj is not None:
            return partial
        return None
    except Exception:
        return None


def _strip_prefix(text: str) -> str:
    if not text:
        return text
    text = text.strip()
    for prefix in COMMON_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return text


def _clean_username_for_channel(username: str) -> str:
    clean = "".join(c for c in username.lower() if c.isalnum() or c in "-_")
    return clean[:20] or "user"


def build_main_panel(cog, guild: discord.Guild, gd: dict) -> ui.LayoutView:
    p           = gd["panel"]
    cats        = gd.get("categories", [])
    open_count  = sum(1 for t in gd.get("tickets", {}).values() if not t.get("closed"))
    staff_roles = ", ".join(f"<@&{r}>" for r in gd.get("staffRoles", [])) or "None"
    log_str     = f"<#{p['logChannel']}>" if p.get("logChannel") else "`Not Set`"

    view      = ui.LayoutView(timeout=600)
    container = ui.Container(accent_color=BLACK)

    container.add_item(ui.TextDisplay(
        content=f"{S_FILTER}  **Ticket Panel Settings**"
    ))
    container.add_item(ui.Separator())

    container.add_item(ui.TextDisplay(content=(
        f"{S_DOT}  **Status:** {'`✓ Active`' if p['enabled'] else '`✗ Disabled`'}\n"
        f"{S_DOT}  **Title:** {p['title']}\n"
        f"{S_DOT}  **Categories:** {len(cats)}/25\n"
        f"{S_DOT}  **Open Tickets:** {open_count}\n"
        f"{S_DOT}  **Max/User:** {p['maxTickets']}\n"
        f"{S_DOT}  **Logs:** {log_str}\n"
        f"{S_DOT}  **Staff Roles:** {staff_roles}\n"
        f"{S_DOT}  **Thumbnail:** {'`Set ✓`' if p.get('thumbnail') else '`Not Set`'}\n"
        f"{S_DOT}  **Image:** {'`Set ✓`' if p.get('image') else '`Not Set`'}"
    )))

    container.add_item(ui.Separator())

    row1 = ui.ActionRow()
    row1.add_item(ui.Button(label="Title",       style=discord.ButtonStyle.secondary, custom_id="tp_title"))
    row1.add_item(ui.Button(label="Description", style=discord.ButtonStyle.secondary, custom_id="tp_desc"))
    row1.add_item(ui.Button(label="Placeholder", style=discord.ButtonStyle.secondary, custom_id="tp_placeholder"))
    container.add_item(row1)

    row2 = ui.ActionRow()
    row2.add_item(ui.Button(label="Thumbnail",      style=discord.ButtonStyle.secondary, custom_id="tp_thumbnail"))
    row2.add_item(ui.Button(label="Image",          style=discord.ButtonStyle.secondary, custom_id="tp_image"))
    row2.add_item(ui.Button(label="Ticket Message", style=discord.ButtonStyle.secondary, custom_id="tp_ticketmsg"))
    container.add_item(row2)

    row3 = ui.ActionRow()
    row3.add_item(ui.Button(label="Max Tickets", style=discord.ButtonStyle.secondary, custom_id="tp_maxtickets"))
    row3.add_item(ui.Button(label="Log Channel", style=discord.ButtonStyle.primary,   custom_id="tp_logs"))
    row3.add_item(ui.Button(label="Staff Roles", style=discord.ButtonStyle.primary,   custom_id="tp_staffroles"))
    container.add_item(row3)

    row4 = ui.ActionRow()
    row4.add_item(ui.Button(label="Manage Categories", style=discord.ButtonStyle.primary, custom_id="tp_categories"))
    row4.add_item(ui.Button(
        label=("Disable" if p["enabled"] else "Enable"),
        style=(discord.ButtonStyle.danger if p["enabled"] else discord.ButtonStyle.success),
        custom_id="tp_toggle",
    ))
    row4.add_item(ui.Button(label="Send Panel", style=discord.ButtonStyle.success, custom_id="tp_send"))
    container.add_item(row4)

    view.add_item(container)
    cog._bind_main_callbacks(view)
    return view


def build_category_panel(cog, gd: dict) -> ui.LayoutView:
    cats = gd.get("categories", [])

    view      = ui.LayoutView(timeout=600)
    container = ui.Container(accent_color=BLACK)

    container.add_item(ui.TextDisplay(
        content=f"{S_PLAYLIST}  **Categories** ({len(cats)}/25)"
    ))
    container.add_item(ui.Separator())

    if not cats:
        container.add_item(ui.TextDisplay(
            content="No categories found.\nAdd one to get started!"
        ))
    else:
        lines = []
        for i, c in enumerate(cats):
            lines.append(
                f"**{i + 1}.** {c['emoji']} **{c['name']}**\n"
                f"{S_ARROW_R} {c['description']}"
            )
        container.add_item(ui.TextDisplay(content="\n\n".join(lines)))

    container.add_item(ui.Separator())

    row1 = ui.ActionRow()
    row1.add_item(ui.Button(label="Add Category", style=discord.ButtonStyle.success,   custom_id="tp_addcat"))
    row1.add_item(ui.Button(label="← Back",       style=discord.ButtonStyle.secondary, custom_id="tp_main"))
    container.add_item(row1)

    if cats:
        row2 = ui.ActionRow()
        options = []
        for i, c in enumerate(cats[:25]):
            emoji_obj = _safe_emoji_for_bot(cog.bot, c["emoji"])
            options.append(discord.SelectOption(
                label=c["name"],
                description=c["description"][:50],
                value=f"del_{i}",
                emoji=emoji_obj,
            ))

        select = ui.Select(
            custom_id="tp_catselect",
            placeholder="Select category to delete",
            options=options,
        )
        row2.add_item(select)
        container.add_item(row2)

    view.add_item(container)
    cog._bind_main_callbacks(view)
    return view


def build_public_panel(bot, gd: dict) -> ui.LayoutView:
    p    = gd["panel"]
    cats = gd.get("categories", [])

    view      = ui.LayoutView(timeout=None)
    container = ui.Container(accent_color=BLACK)

    container.add_item(ui.TextDisplay(
        content=f"{S_FAVOURITE}  **{p['title']}**"
    ))
    container.add_item(ui.Separator())
    container.add_item(ui.TextDisplay(content=p["description"]))

    if p.get("image"):
        try:
            container.add_item(ui.MediaGallery(
                ui.MediaGalleryItem(media=p["image"])
            ))
        except Exception:
            container.add_item(ui.TextDisplay(content=f"[Image]({p['image']})"))

    container.add_item(ui.Separator())

    if not cats:
        row = ui.ActionRow()
        ticket_emoji = _safe_emoji_for_bot(bot, str(E_TICKET))
        row.add_item(ui.Button(
            label="Open Ticket",
            emoji=ticket_emoji if isinstance(ticket_emoji, discord.PartialEmoji) else None,
            style=discord.ButtonStyle.primary,
            custom_id="ticket_open_general",
        ))
        container.add_item(row)
    else:
        row = ui.ActionRow()
        options = []
        for i, c in enumerate(cats[:25]):
            emoji_obj = _safe_emoji_for_bot(bot, c["emoji"])
            options.append(discord.SelectOption(
                label=c["name"],
                description=c["description"][:50],
                value=f"cat_{i}",
                emoji=emoji_obj,
                default=False,
            ))

        select = ui.Select(
            custom_id="ticket_category_select",
            placeholder=p["placeholder"],
            min_values=1,
            max_values=1,
            options=options,
        )
        row.add_item(select)
        container.add_item(row)

    view.add_item(container)
    return view


class SendPanelPickerView(ui.LayoutView):
    def __init__(self, cog, author_id: int):
        super().__init__(timeout=120)
        self.cog       = cog
        self.author_id = author_id
        self._build()

    def _build(self):
        c = ui.Container(accent_color=BLACK)
        c.add_item(ui.TextDisplay(content=f"## {S_INFO}  Send Panel"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(content=(
            "Select the channel where you want to send the ticket panel."
        )))
        c.add_item(ui.Separator(visible=False))

        ch_select = ui.ChannelSelect(
            placeholder="Choose a channel...",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            custom_id="sp_chan_select",
        )
        ch_select.callback = self._on_channel_pick
        c.add_item(ui.ActionRow(ch_select))

        c.add_item(ui.Separator(visible=False))

        row = ui.ActionRow()
        here_btn   = ui.Button(label="Send Here", style=discord.ButtonStyle.success, custom_id="sp_here")
        cancel_btn = ui.Button(label="Cancel",    style=discord.ButtonStyle.danger,  custom_id="sp_cancel")
        here_btn.callback   = self._on_here
        cancel_btn.callback = self._on_cancel
        row.add_item(here_btn)
        row.add_item(cancel_btn)
        c.add_item(row)

        self.add_item(c)

    async def _check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                view=quick_view("Only the command user can use this!"),
                ephemeral=True,
            )
            return False
        return True

    async def _send_panel_to(self, interaction: discord.Interaction, target):
        gd = get_guild_data(interaction.guild.id)
        guild = interaction.guild

        if not isinstance(target, (discord.TextChannel, discord.Thread)):
            return await interaction.response.edit_message(
                view=quick_view(f"{S_ERROR}  That channel type can't receive messages!")
            )

        perms = target.permissions_for(guild.me)
        if not (perms.send_messages and perms.view_channel):
            return await interaction.response.edit_message(
                view=quick_view(f"{S_ERROR}  I don't have permission to send in {target.mention}!")
            )

        try:
            public_view = build_public_panel(self.cog.bot, gd)
            await target.send(view=public_view, allowed_mentions=discord.AllowedMentions.none())
            await interaction.response.edit_message(
                view=quick_view(f"{S_SUCCESS}  **Panel sent to** {target.mention}!")
            )
        except discord.HTTPException as e:
            traceback.print_exc()
            await interaction.response.edit_message(
                view=quick_view(f"{S_ERROR}  **Discord rejected the panel!**\n`{str(e)[:300]}`")
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.response.edit_message(
                view=quick_view(f"{S_ERROR}  **Unexpected error!**\n`{str(e)[:300]}`")
            )

    async def _on_channel_pick(self, interaction: discord.Interaction):
        if not await self._check(interaction):
            return
        try:
            ch_id = int(interaction.data["values"][0])
        except Exception:
            return await interaction.response.edit_message(view=quick_view(f"{S_ERROR}  Invalid selection."))

        target = interaction.guild.get_channel(ch_id)
        if target is None:
            try:
                target = await interaction.guild.fetch_channel(ch_id)
            except Exception:
                target = None

        if target is None:
            return await interaction.response.edit_message(view=quick_view(f"{S_ERROR}  Channel not found!"))

        await self._send_panel_to(interaction, target)

    async def _on_here(self, interaction: discord.Interaction):
        if not await self._check(interaction):
            return
        await self._send_panel_to(interaction, interaction.channel)

    async def _on_cancel(self, interaction: discord.Interaction):
        if not await self._check(interaction):
            return
        await interaction.response.edit_message(view=quick_view(f"{S_INFO}  Cancelled."))


async def _ticket_check_staff(interaction: discord.Interaction) -> bool:
    gd = get_guild_data(interaction.guild.id)
    staff_roles = gd.get("staffRoles", [])
    if not staff_roles:
        return True
    user_role_ids = {str(r.id) for r in interaction.user.roles}
    if not user_role_ids.intersection(set(staff_roles)):
        await interaction.response.send_message(
            view=quick_view("You don't have a staff role!"), ephemeral=True
        )
        return False
    return True


async def _ticket_check_staff_ctx(ctx: commands.Context) -> bool:
    gd = get_guild_data(ctx.guild.id)
    staff_roles = gd.get("staffRoles", [])
    if not staff_roles:
        return True
    user_role_ids = {str(r.id) for r in ctx.author.roles}
    if not user_role_ids.intersection(set(staff_roles)):
        await ctx.send(view=quick_view("You don't have a staff role!"))
        return False
    return True


async def _do_close_ticket(cog, channel: discord.TextChannel, closer: discord.Member, original_msg=None):
    data = load_data()
    gid   = str(channel.guild.id)
    ch_id = str(channel.id)

    ticket = data.get(gid, {}).get("tickets", {}).get(ch_id)
    if not ticket:
        return False, "Ticket not found!"
    if ticket.get("closed"):
        return False, "Ticket is already closed!"

    ticket["closed"]   = True
    ticket["closedBy"] = closer.id
    ticket["closedAt"] = datetime.now().isoformat()
    save_data(data)

    creator = channel.guild.get_member(ticket["creatorId"])

    if creator:
        try:
            await channel.set_permissions(creator, view_channel=False, send_messages=False)
        except Exception:
            pass

    gd = get_guild_data(channel.guild.id)
    staff_roles = gd.get("staffRoles", [])
    closed_cat = await _get_or_create_category(
        channel.guild, gd,
        "closedCategoryId",
        CLOSED_CATEGORY_NAME,
        staff_role_ids=staff_roles,
    )

    creator_name = "user"
    if creator:
        creator_name = _clean_username_for_channel(creator.name)
    else:
        try:
            user_obj = await cog.bot.fetch_user(ticket["creatorId"])
            creator_name = _clean_username_for_channel(user_obj.name)
        except Exception:
            pass

    new_name = f"closed-{creator_name}"

    try:
        edit_kwargs = {"name": new_name}
        if closed_cat:
            edit_kwargs["category"] = closed_cat
            edit_kwargs["sync_permissions"] = False
        await channel.edit(**edit_kwargs, reason=f"Ticket closed by {closer}")
    except discord.HTTPException as e:
        print(f"[ticket close] rename/move failed: {e}")

    v = ui.LayoutView(timeout=None)
    c = ui.Container(accent_color=BLACK)
    c.add_item(ui.TextDisplay(content=f"## Ticket Closed"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(content=(
        f"> **Creator   :** <@{ticket['creatorId']}>\n"
        f"> **Closed By :** {closer.mention}\n"
        f"> **Time      :** {discord.utils.format_dt(datetime.now(), style='F')}"
    )))
    c.add_item(ui.Separator())

    closed = ClosedTicketHandler(cog, channel.id)

    bot = cog.bot
    em_reo = _safe_emoji_for_bot(bot, str(E_REOPEN))
    em_trn = _safe_emoji_for_bot(bot, str(E_TRANSCRIPT))
    em_del = _safe_emoji_for_bot(bot, str(E_DELETE))

    row = ui.ActionRow()
    b_reo = ui.Button(label="Reopen",     emoji=em_reo if isinstance(em_reo, discord.PartialEmoji) else None, style=discord.ButtonStyle.success, custom_id="ct_reopen")
    b_trn = ui.Button(label="Transcript", emoji=em_trn if isinstance(em_trn, discord.PartialEmoji) else None, style=discord.ButtonStyle.primary, custom_id="ct_transcript")
    b_del = ui.Button(label="Delete",     emoji=em_del if isinstance(em_del, discord.PartialEmoji) else None, style=discord.ButtonStyle.danger,  custom_id="ct_delete")
    b_reo.callback = closed._reopen
    b_trn.callback = closed._transcript
    b_del.callback = closed._delete
    row.add_item(b_reo)
    row.add_item(b_trn)
    row.add_item(b_del)
    c.add_item(row)

    v.add_item(c)

    await channel.send(view=v, allowed_mentions=discord.AllowedMentions.none())

    if original_msg:
        try:
            await original_msg.edit(view=None)
        except Exception:
            pass

    return True, "Ticket closed!"


async def _do_delete_ticket(cog, channel: discord.TextChannel, deleter: discord.Member):
    try:
        messages = [m async for m in channel.history(limit=None, oldest_first=True)]
        content  = f"Transcript for #{channel.name} in {channel.guild.name}\n"
        content += "=" * 60 + "\n\n"
        for m in messages:
            ts = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content += f"[{ts}] {m.author.display_name}: {m.clean_content}\n"
            for a in m.attachments:
                content += f"   [Attachment] {a.url}\n"

        file = discord.File(io.BytesIO(content.encode("utf-8")), filename=f"transcript-{channel.name}.txt")

        try:
            await deleter.send(
                content=f"📝 Transcript for **#{channel.name}** in **{channel.guild.name}**",
                file=file,
            )
        except Exception:
            pass
    except Exception:
        pass

    data = load_data()
    gid  = str(channel.guild.id)
    if gid in data and str(channel.id) in data[gid].get("tickets", {}):
        del data[gid]["tickets"][str(channel.id)]
        save_data(data)

    try:
        await channel.delete(reason=f"Ticket deleted by {deleter}")
    except Exception:
        return False
    return True


class ClosedTicketHandler:
    def __init__(self, cog, channel_id: int):
        self.cog        = cog
        self.channel_id = channel_id

    async def _reopen(self, interaction: discord.Interaction):
        if not await _ticket_check_staff(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        gid  = str(interaction.guild.id)
        ch_id = str(self.channel_id)

        ticket = data.get(gid, {}).get("tickets", {}).get(ch_id)
        if not ticket:
            return await interaction.followup.send(view=quick_view("Ticket not found!"), ephemeral=True)

        ticket["closed"]   = False
        ticket["closedBy"] = None
        ticket["closedAt"] = None
        save_data(data)

        creator = interaction.guild.get_member(ticket["creatorId"])
        if creator:
            try:
                await interaction.channel.set_permissions(creator, view_channel=True, send_messages=True)
            except Exception:
                pass

        gd = get_guild_data(interaction.guild.id)
        staff_roles = gd.get("staffRoles", [])
        open_cat = await _get_or_create_category(
            interaction.guild, gd,
            "openCategoryId",
            OPEN_CATEGORY_NAME,
            staff_role_ids=staff_roles,
        )

        creator_name = "user"
        if creator:
            creator_name = _clean_username_for_channel(creator.name)
        else:
            try:
                user_obj = await self.cog.bot.fetch_user(ticket["creatorId"])
                creator_name = _clean_username_for_channel(user_obj.name)
            except Exception:
                pass

        t_num = ticket.get("ticketNumber", 0)
        new_name = f"ticket-{t_num:04d}-{creator_name}"

        try:
            edit_kwargs = {"name": new_name}
            if open_cat:
                edit_kwargs["category"] = open_cat
                edit_kwargs["sync_permissions"] = False
            await interaction.channel.edit(**edit_kwargs, reason=f"Ticket reopened by {interaction.user}")
        except Exception as e:
            print(f"[ticket reopen] rename/move failed: {e}")

        await _send_ticket_welcome(self.cog, interaction.channel, ticket, reopen=True)

        try:
            await interaction.message.edit(view=None)
        except Exception:
            pass

        await interaction.followup.send(view=quick_view("Reopened!"), ephemeral=True)

    async def _transcript(self, interaction: discord.Interaction):
        if not await _ticket_check_staff(interaction):
            return
        await self._make_transcript(interaction, delete_after=False)

    async def _delete(self, interaction: discord.Interaction):
        if not await _ticket_check_staff(interaction):
            return
        await self._make_transcript(interaction, delete_after=True)

    async def _make_transcript(self, interaction: discord.Interaction, delete_after: bool):
        await interaction.response.defer(ephemeral=True, thinking=True)
        ch = interaction.guild.get_channel(self.channel_id)
        if not ch:
            return await interaction.followup.send(view=quick_view("Channel not found!"), ephemeral=True)

        messages = [m async for m in ch.history(limit=None, oldest_first=True)]
        content  = f"Transcript for #{ch.name} in {interaction.guild.name}\n"
        content += "=" * 60 + "\n\n"
        for m in messages:
            ts = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content += f"[{ts}] {m.author.display_name}: {m.clean_content}\n"
            for a in m.attachments:
                content += f"   [Attachment] {a.url}\n"

        file = discord.File(io.BytesIO(content.encode("utf-8")), filename=f"transcript-{ch.name}.txt")

        try:
            await interaction.user.send(
                content=f"📝 Transcript for **#{ch.name}** in **{interaction.guild.name}**",
                file=file,
            )
            await interaction.followup.send(view=quick_view("Transcript sent to your DMs!"), ephemeral=True)
        except Exception:
            await interaction.followup.send(content="Couldn't DM — sending here:", file=file, ephemeral=True)

        if delete_after:
            await interaction.followup.send(view=quick_view("Channel deleting in **10s**..."), ephemeral=True)
            await asyncio.sleep(10)
            try:
                await ch.delete()
            except Exception:
                pass
            data = load_data()
            gid  = str(interaction.guild.id)
            if gid in data and str(self.channel_id) in data[gid].get("tickets", {}):
                del data[gid]["tickets"][str(self.channel_id)]
                save_data(data)


async def _send_ticket_welcome(cog, channel: discord.TextChannel, ticket: dict, reopen: bool = False):
    gd        = get_guild_data(channel.guild.id)
    guild     = channel.guild
    user      = guild.get_member(ticket["creatorId"]) or await cog.bot.fetch_user(ticket["creatorId"])
    cat_name  = ticket.get("category", "Support")
    t_num     = ticket.get("ticketNumber", 0)

    cat_emoji = "🎫"
    for c in gd.get("categories", []):
        if c["name"] == cat_name:
            cat_emoji = c["emoji"]
            break

    user_mention = user.mention if hasattr(user, "mention") else f"<@{ticket['creatorId']}>"
    welcome_text = gd["panel"]["ticketMessage"].replace("{user}", user_mention)

    v = ui.LayoutView(timeout=None)
    c = ui.Container(accent_color=BLACK)

    if reopen:
        c.add_item(ui.TextDisplay(content=f"**Ticket Reopened**"))
    else:
        c.add_item(ui.TextDisplay(content=f"**Welcome to Your Ticket**"))

    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(content=(
        f"**Ticket ID:** `#{t_num:04d}`\n"
        f"**Category:** {cat_emoji} `{cat_name}`\n"
        f"**Opened By:** {user_mention}\n"
        f"**Opened At:** {discord.utils.format_dt(datetime.now(), style='F')}"
    )))

    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(content=f"> {welcome_text}"))
    c.add_item(ui.Separator())

    bot = cog.bot
    em_lock = _safe_emoji_for_bot(bot, str(E_LOCK))
    em_unlk = _safe_emoji_for_bot(bot, str(E_UNLOCK))
    em_clm  = _safe_emoji_for_bot(bot, str(E_CLAIM))
    em_cls  = _safe_emoji_for_bot(bot, str(E_CLOSE))

    handler = TicketControlHandler(cog, channel.id)

    row = ui.ActionRow()
    b_lock = ui.Button(label="Lock",   emoji=em_lock if isinstance(em_lock, discord.PartialEmoji) else None, style=discord.ButtonStyle.secondary, custom_id="t_lock")
    b_unlk = ui.Button(label="Unlock", emoji=em_unlk if isinstance(em_unlk, discord.PartialEmoji) else None, style=discord.ButtonStyle.secondary, custom_id="t_unlock")
    b_clm  = ui.Button(label="Claim",  emoji=em_clm  if isinstance(em_clm,  discord.PartialEmoji) else None, style=discord.ButtonStyle.primary,   custom_id="t_claim")
    b_cls  = ui.Button(label="Close",  emoji=em_cls  if isinstance(em_cls,  discord.PartialEmoji) else None, style=discord.ButtonStyle.danger,    custom_id="t_close")
    b_lock.callback = handler._lock
    b_unlk.callback = handler._unlock
    b_clm.callback  = handler._claim
    b_cls.callback  = handler._close
    row.add_item(b_lock)
    row.add_item(b_unlk)
    row.add_item(b_clm)
    row.add_item(b_cls)
    c.add_item(row)

    v.add_item(c)
    return await channel.send(view=v, allowed_mentions=discord.AllowedMentions.none())


class TicketControlHandler:
    def __init__(self, cog, channel_id: int):
        self.cog        = cog
        self.channel_id = channel_id

    async def _lock(self, interaction: discord.Interaction):
        if not await _ticket_check_staff(interaction): return
        data = load_data()
        gid  = str(interaction.guild.id)
        ch_id = str(self.channel_id)

        ticket = data.get(gid, {}).get("tickets", {}).get(ch_id)
        if not ticket:
            return await interaction.response.send_message(view=quick_view("Ticket not found!"), ephemeral=True)
        if ticket.get("locked"):
            return await interaction.response.send_message(view=quick_view("Already locked!"), ephemeral=True)

        creator = interaction.guild.get_member(ticket["creatorId"])
        if creator:
            try:
                await interaction.channel.set_permissions(creator, send_messages=False)
            except Exception:
                pass

        ticket["locked"] = True
        save_data(data)
        await interaction.response.send_message(view=quick_view(f"Ticket **locked** by {interaction.user.mention}."))

    async def _unlock(self, interaction: discord.Interaction):
        if not await _ticket_check_staff(interaction): return
        data = load_data()
        gid  = str(interaction.guild.id)
        ch_id = str(self.channel_id)

        ticket = data.get(gid, {}).get("tickets", {}).get(ch_id)
        if not ticket:
            return await interaction.response.send_message(view=quick_view("Ticket not found!"), ephemeral=True)
        if not ticket.get("locked"):
            return await interaction.response.send_message(view=quick_view("Already unlocked!"), ephemeral=True)

        creator = interaction.guild.get_member(ticket["creatorId"])
        if creator:
            try:
                await interaction.channel.set_permissions(creator, send_messages=True)
            except Exception:
                pass

        ticket["locked"] = False
        save_data(data)
        await interaction.response.send_message(view=quick_view(f"Ticket **unlocked** by {interaction.user.mention}."))

    async def _claim(self, interaction: discord.Interaction):
        if not await _ticket_check_staff(interaction): return
        data = load_data()
        gid  = str(interaction.guild.id)
        ch_id = str(self.channel_id)

        ticket = data.get(gid, {}).get("tickets", {}).get(ch_id)
        if not ticket:
            return await interaction.response.send_message(view=quick_view("Ticket not found!"), ephemeral=True)
        if ticket.get("claimedBy"):
            return await interaction.response.send_message(
                view=quick_view(f"Already claimed by <@{ticket['claimedBy']}>!"),
                ephemeral=True,
            )

        ticket["claimedBy"] = interaction.user.id
        save_data(data)
        await interaction.response.send_message(view=quick_view(f"Claimed by {interaction.user.mention}!"))

    async def _close(self, interaction: discord.Interaction):
        if not await _ticket_check_staff(interaction): return
        await interaction.response.defer(ephemeral=True)

        success, msg = await _do_close_ticket(
            self.cog,
            interaction.channel,
            interaction.user,
            original_msg=interaction.message,
        )

        if not success:
            return await interaction.followup.send(view=quick_view(msg), ephemeral=True)

        await interaction.followup.send(view=quick_view("Ticket closed!"), ephemeral=True)


async def await_message(bot, channel, user_id, timeout=30.0):
    def check(m):
        return m.author.id == user_id and m.channel.id == channel.id

    try:
        msg = await bot.wait_for("message", check=check, timeout=timeout)
    except asyncio.TimeoutError:
        return None

    try:
        await msg.delete()
    except Exception:
        pass

    return _strip_prefix(msg.content)


class TicketCog(commands.Cog, name="Ticket System"):
    def __init__(self, bot):
        self.bot         = bot
        self._panel_msgs = {}

    def _bind_main_callbacks(self, view: ui.LayoutView):
        for item in view.walk_children():
            if isinstance(item, ui.Button):
                cid = item.custom_id or ""
                handler = self._get_button_handler(cid)
                if handler:
                    item.callback = handler
            elif isinstance(item, ui.Select):
                cid = item.custom_id or ""
                handler = self._get_select_handler(cid)
                if handler:
                    item.callback = handler

    def _get_button_handler(self, cid: str):
        mapping = {
            "tp_title":       self._cb_title,
            "tp_desc":        self._cb_desc,
            "tp_placeholder": self._cb_placeholder,
            "tp_thumbnail":   self._cb_thumbnail,
            "tp_image":       self._cb_image,
            "tp_ticketmsg":   self._cb_ticketmsg,
            "tp_maxtickets":  self._cb_maxtickets,
            "tp_logs":        self._cb_logs,
            "tp_staffroles":  self._cb_staffroles,
            "tp_toggle":      self._cb_toggle,
            "tp_categories":  self._cb_categories,
            "tp_main":        self._cb_main,
            "tp_addcat":      self._cb_addcat,
            "tp_send":        self._cb_send,
        }
        return mapping.get(cid)

    def _get_select_handler(self, cid: str):
        return {"tp_catselect": self._cb_catselect}.get(cid)

    async def _check_panel_owner(self, interaction: discord.Interaction) -> bool:
        owner_id = self._panel_msgs.get(interaction.message.id)
        if owner_id and interaction.user.id != owner_id:
            await interaction.response.send_message(view=quick_view("Only the command user can use this!"), ephemeral=True)
            return False
        return True

    async def _prompt_and_update(self, interaction, prompt_text, updater, timeout=30.0):
        await interaction.response.send_message(
            view=quick_view(f"{prompt_text}\n\n*Timeout: {int(timeout)}s*"),
            ephemeral=True,
        )

        input_text = await await_message(self.bot, interaction.channel, interaction.user.id, timeout)

        if not input_text:
            return await interaction.edit_original_response(view=quick_view("Timed out!"))

        data = load_data()
        gid  = str(interaction.guild.id)
        if gid not in data:
            data[gid] = get_guild_data(interaction.guild.id)

        updater(input_text, data, gid)
        save_data(data)

        await interaction.edit_original_response(view=quick_view("Updated successfully!"))

        try:
            new_view = build_main_panel(self, interaction.guild, data[gid])
            await interaction.message.edit(view=new_view)
            self._panel_msgs[interaction.message.id] = interaction.user.id
        except Exception:
            pass

    async def _cb_title(self, interaction):
        if not await self._check_panel_owner(interaction): return
        await self._prompt_and_update(
            interaction,
            "**Edit Title**\nSend the new panel title.",
            lambda val, d, gid: d[gid]["panel"].update({"title": val}),
        )

    async def _cb_desc(self, interaction):
        if not await self._check_panel_owner(interaction): return
        await self._prompt_and_update(
            interaction,
            "**Edit Description**\nSend the new panel description.",
            lambda val, d, gid: d[gid]["panel"].update({"description": val}),
        )

    async def _cb_placeholder(self, interaction):
        if not await self._check_panel_owner(interaction): return
        await self._prompt_and_update(
            interaction,
            "**Edit Placeholder**\nSend the dropdown placeholder text.",
            lambda val, d, gid: d[gid]["panel"].update({"placeholder": val[:150]}),
        )

    async def _cb_thumbnail(self, interaction):
        if not await self._check_panel_owner(interaction): return
        def upd(val, d, gid):
            d[gid]["panel"]["thumbnail"] = None if val.lower() == "remove" else val
        await self._prompt_and_update(
            interaction,
            "**Set Thumbnail**\nSend an image URL. Send `remove` to clear.",
            upd,
        )

    async def _cb_image(self, interaction):
        if not await self._check_panel_owner(interaction): return
        def upd(val, d, gid):
            d[gid]["panel"]["image"] = None if val.lower() == "remove" else val
        await self._prompt_and_update(
            interaction,
            "**Set Image**\nSend an image URL. Send `remove` to clear.",
            upd,
        )

    async def _cb_ticketmsg(self, interaction):
        if not await self._check_panel_owner(interaction): return
        await self._prompt_and_update(
            interaction,
            "**Edit Ticket Message**\nUse `{user}` for mention.\nSend the new message.",
            lambda val, d, gid: d[gid]["panel"].update({"ticketMessage": val}),
        )

    async def _cb_maxtickets(self, interaction):
        if not await self._check_panel_owner(interaction): return
        gd = get_guild_data(interaction.guild.id)
        def upd(val, d, gid):
            try:
                n = int(val)
                if 1 <= n <= 10:
                    d[gid]["panel"]["maxTickets"] = n
            except ValueError:
                pass
        await self._prompt_and_update(
            interaction,
            f"**Max Tickets Per User**\nSend a number (1-10).\nCurrent: **{gd['panel']['maxTickets']}**",
            upd,
        )

    async def _cb_logs(self, interaction):
        if not await self._check_panel_owner(interaction): return
        def upd(val, d, gid):
            if val.lower() == "disable":
                d[gid]["panel"]["logChannel"] = None
            else:
                ch_id = val.replace("<", "").replace(">", "").replace("#", "").strip()
                if ch_id.isdigit() and interaction.guild.get_channel(int(ch_id)):
                    d[gid]["panel"]["logChannel"] = ch_id
        await self._prompt_and_update(
            interaction,
            "**Log Channel**\nMention a channel or send ID.\nSend `disable` to remove.",
            upd,
        )

    async def _cb_staffroles(self, interaction):
        if not await self._check_panel_owner(interaction): return
        gd = get_guild_data(interaction.guild.id)
        current = ", ".join(f"<@&{r}>" for r in gd.get("staffRoles", [])) or "None"
        def upd(val, d, gid):
            if val.lower() == "clear":
                d[gid]["staffRoles"] = []
            else:
                role_id = val.replace("<", "").replace(">", "").replace("@", "").replace("&", "").strip()
                if not role_id.isdigit():
                    return
                if "staffRoles" not in d[gid]:
                    d[gid]["staffRoles"] = []
                if role_id in d[gid]["staffRoles"]:
                    d[gid]["staffRoles"] = [r for r in d[gid]["staffRoles"] if r != role_id]
                elif interaction.guild.get_role(int(role_id)):
                    d[gid]["staffRoles"].append(role_id)
        await self._prompt_and_update(
            interaction,
            f"**Staff Roles**\nCurrent: {current}\n\nMention a role to add/remove.\nSend `clear` to wipe all.",
            upd,
        )

    async def _cb_toggle(self, interaction):
        if not await self._check_panel_owner(interaction): return
        data = load_data()
        gid  = str(interaction.guild.id)
        if gid not in data:
            data[gid] = get_guild_data(interaction.guild.id)
        data[gid]["panel"]["enabled"] = not data[gid]["panel"]["enabled"]
        save_data(data)

        new_view = build_main_panel(self, interaction.guild, data[gid])
        await interaction.response.edit_message(view=new_view)
        self._panel_msgs[interaction.message.id] = interaction.user.id

    async def _cb_categories(self, interaction):
        if not await self._check_panel_owner(interaction): return
        gd = get_guild_data(interaction.guild.id)
        new_view = build_category_panel(self, gd)
        await interaction.response.edit_message(view=new_view)
        self._panel_msgs[interaction.message.id] = interaction.user.id

    async def _cb_main(self, interaction):
        if not await self._check_panel_owner(interaction): return
        gd = get_guild_data(interaction.guild.id)
        new_view = build_main_panel(self, interaction.guild, gd)
        await interaction.response.edit_message(view=new_view)
        self._panel_msgs[interaction.message.id] = interaction.user.id

    async def _cb_addcat(self, interaction):
        if not await self._check_panel_owner(interaction): return
        gd = get_guild_data(interaction.guild.id)
        if len(gd.get("categories", [])) >= 25:
            return await interaction.response.send_message(view=quick_view("Max 25 categories!"), ephemeral=True)

        await interaction.response.send_message(
            view=quick_view(
                "**Add Category**\n\n"
                "Send in this format:\n"
                "`Name | Description | Emoji`\n\n"
                "**Example:**\n"
                "`General Support | Get help with general issues | 🎫`\n\n"
                "*Timeout: 60s*"
            ),
            ephemeral=True,
        )

        input_text = await await_message(self.bot, interaction.channel, interaction.user.id, 60.0)

        if not input_text:
            return await interaction.edit_original_response(view=quick_view("Timed out!"))

        parts = [p.strip() for p in input_text.split("|")]
        new_cat = {
            "name":        (parts[0] if len(parts) > 0 else "Support")[:25],
            "description": (parts[1] if len(parts) > 1 else "Open a support ticket")[:50],
            "emoji":       (parts[2] if len(parts) > 2 else "🎫"),
        }

        data = load_data()
        gid  = str(interaction.guild.id)
        if gid not in data:
            data[gid] = get_guild_data(interaction.guild.id)
        data[gid]["categories"].append(new_cat)
        save_data(data)

        await interaction.edit_original_response(
            view=quick_view(
                f"**Category Added!**\n\n"
                f"**Name:** {new_cat['name']}\n"
                f"**Description:** {new_cat['description']}\n"
                f"**Emoji:** {new_cat['emoji']}"
            )
        )

        try:
            new_view = build_category_panel(self, data[gid])
            await interaction.message.edit(view=new_view)
            self._panel_msgs[interaction.message.id] = interaction.user.id
        except Exception:
            pass

    async def _cb_catselect(self, interaction):
        if not await self._check_panel_owner(interaction): return
        try:
            val = interaction.data["values"][0]
            idx = int(val.replace("del_", ""))
        except Exception:
            return

        data = load_data()
        gid  = str(interaction.guild.id)
        if gid not in data:
            return
        cats = data[gid].get("categories", [])
        if idx < 0 or idx >= len(cats):
            return
        removed = cats.pop(idx)
        save_data(data)

        await interaction.response.send_message(
            view=quick_view(f"Category **{removed['name']}** deleted!"),
            ephemeral=True,
        )

        try:
            new_view = build_category_panel(self, data[gid])
            await interaction.message.edit(view=new_view)
            self._panel_msgs[interaction.message.id] = interaction.user.id
        except Exception:
            pass

    async def _cb_send(self, interaction):
        if not await self._check_panel_owner(interaction):
            return
        gd = get_guild_data(interaction.guild.id)

        if not gd["panel"]["enabled"]:
            return await interaction.response.send_message(
                view=quick_view("Panel is **disabled**!"),
                ephemeral=True,
            )
        if not gd.get("categories"):
            return await interaction.response.send_message(
                view=quick_view("Add at least **1 category** first!"),
                ephemeral=True,
            )

        picker = SendPanelPickerView(self, interaction.user.id)
        await interaction.response.send_message(view=picker, ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id", "")

        if cid == "ticket_category_select":
            try:
                val = interaction.data["values"][0]
                idx = int(val.replace("cat_", ""))

                try:
                    gd_reset = get_guild_data(interaction.guild.id)
                    fresh_view = build_public_panel(self.bot, gd_reset)
                    await interaction.message.edit(view=fresh_view)
                except Exception as e:
                    print(f"[select reset failed] {e}")

                await self._open_ticket(interaction, idx)
            except Exception as e:
                traceback.print_exc()
                try:
                    await interaction.response.send_message(view=quick_view(f"Error: `{e}`"), ephemeral=True)
                except Exception:
                    pass

        elif cid == "ticket_open_general":
            try:
                await self._open_ticket(interaction, None)
            except Exception as e:
                traceback.print_exc()
                try:
                    await interaction.response.send_message(view=quick_view(f"Error: `{e}`"), ephemeral=True)
                except Exception:
                    pass

    async def _open_ticket(self, interaction: discord.Interaction, cat_idx: int | None):
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        gd     = get_guild_data(interaction.guild.id)
        guild  = interaction.guild
        user   = interaction.user

        open_count = sum(
            1 for t in gd.get("tickets", {}).values()
            if not t.get("closed") and t.get("creatorId") == user.id
        )
        if open_count >= gd["panel"]["maxTickets"]:
            return await interaction.followup.send(
                view=quick_view(f"You already have **{gd['panel']['maxTickets']}** open tickets!"),
                ephemeral=True,
            )

        cat = None
        if cat_idx is not None and cat_idx < len(gd.get("categories", [])):
            cat = gd["categories"][cat_idx]
        cat_name  = cat["name"]  if cat else "Support"

        staff_roles = gd.get("staffRoles", [])
        open_cat = await _get_or_create_category(
            guild, gd,
            "openCategoryId",
            OPEN_CATEGORY_NAME,
            staff_role_ids=staff_roles,
        )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user:               discord.PermissionOverwrite(
                view_channel=True, send_messages=True, attach_files=True,
                embed_links=True, read_message_history=True,
            ),
            guild.me:           discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True,
                manage_messages=True, attach_files=True, embed_links=True,
                read_message_history=True,
            ),
        }

        staff_pings = []
        for rid in staff_roles:
            role = guild.get_role(int(rid))
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, attach_files=True,
                    embed_links=True, read_message_history=True,
                )
                staff_pings.append(role.mention)

        data = load_data()
        gid  = str(guild.id)
        if gid not in data:
            data[gid] = gd
        data[gid]["totalTickets"] = data[gid].get("totalTickets", 0) + 1
        t_num = data[gid]["totalTickets"]

        clean_name = _clean_username_for_channel(user.name)

        try:
            create_kwargs = dict(
                name=f"ticket-{t_num:04d}-{clean_name}",
                overwrites=overwrites,
                topic=f"Ticket by {user} | Category: {cat_name}",
            )
            if open_cat:
                create_kwargs["category"] = open_cat
            new_ch = await guild.create_text_channel(**create_kwargs)
        except discord.Forbidden:
            return await interaction.followup.send(
                view=quick_view("**No permission!** I need `Manage Channels`."),
                ephemeral=True,
            )
        except Exception as e:
            traceback.print_exc()
            return await interaction.followup.send(
                view=quick_view(f"**Couldn't create channel!**\n`{e}`"),
                ephemeral=True,
            )

        if "tickets" not in data[gid]:
            data[gid]["tickets"] = {}
        data[gid]["tickets"][str(new_ch.id)] = {
            "creatorId":    user.id,
            "category":     cat_name,
            "createdAt":    datetime.now().isoformat(),
            "closed":       False,
            "locked":       False,
            "claimedBy":    None,
            "ticketNumber": t_num,
        }
        save_data(data)

        pings_line = user.mention
        if staff_pings:
            pings_line += " • " + " ".join(staff_pings)

        try:
            await new_ch.send(
                content=pings_line,
                allowed_mentions=discord.AllowedMentions(users=True, roles=True),
            )
        except Exception:
            pass

        try:
            ticket_dict = data[gid]["tickets"][str(new_ch.id)]
            await _send_ticket_welcome(self, new_ch, ticket_dict)
        except Exception as e:
            print(f"[ticket welcome failed] {e}")
            traceback.print_exc()
            try:
                gd_msg = gd["panel"]["ticketMessage"].replace("{user}", user.mention)
                await new_ch.send(content=f"## Ticket `#{t_num:04d}` — {cat_name}\n\n{gd_msg}")
            except Exception:
                pass

        log_ch_id = gd["panel"].get("logChannel")
        if log_ch_id:
            log_ch = guild.get_channel(int(log_ch_id))
            if log_ch:
                try:
                    lv = ui.LayoutView(timeout=None)
                    lc = ui.Container(accent_color=BLACK)
                    lc.add_item(ui.TextDisplay(content=f"## Ticket Created"))
                    lc.add_item(ui.Separator())
                    lc.add_item(ui.TextDisplay(content=(
                        f"> **Creator    :** {user.mention}\n"
                        f"> **Channel    :** {new_ch.mention}\n"
                        f"> **Category   :** `{cat_name}`\n"
                        f"> **Number     :** `#{t_num:04d}`\n"
                        f"> **Time       :** {discord.utils.format_dt(datetime.now(), style='F')}"
                    )))
                    lv.add_item(lc)
                    await log_ch.send(view=lv, allowed_mentions=discord.AllowedMentions.none())
                except Exception:
                    pass

        try:
            await interaction.followup.send(
                view=quick_view(f"**Your ticket has been created:** {new_ch.mention}"),
                ephemeral=True,
            )
        except Exception:
            try:
                await interaction.user.send(f"Your ticket was created: {new_ch.mention}")
            except Exception:
                pass


    @commands.hybrid_command(
        name="ticket",
        description="Open the ticket system configuration panel.",
    )
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def ticket_cmd(self, ctx: commands.Context):
        gd = get_guild_data(ctx.guild.id)
        view = build_main_panel(self, ctx.guild, gd)

        if ctx.interaction:
            await ctx.interaction.response.send_message(view=view)
            msg = await ctx.interaction.original_response()
        else:
            msg = await ctx.send(view=view)

        self._panel_msgs[msg.id] = ctx.author.id

    @commands.command(name="tclose", aliases=["closeticket"])
    @commands.guild_only()
    async def tclose_cmd(self, ctx: commands.Context):
        data = load_data()
        gid  = str(ctx.guild.id)
        ch_id = str(ctx.channel.id)

        ticket = data.get(gid, {}).get("tickets", {}).get(ch_id)
        if not ticket:
            return await ctx.send(view=quick_view("This is not a ticket channel!"))

        if not await _ticket_check_staff_ctx(ctx):
            return

        if ticket.get("closed"):
            return await ctx.send(view=quick_view("This ticket is already closed!"))

        success, msg = await _do_close_ticket(self, ctx.channel, ctx.author)

        if not success:
            return await ctx.send(view=quick_view(msg))

        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name="tdelete", aliases=["deleteticket"])
    @commands.guild_only()
    async def tdelete_cmd(self, ctx: commands.Context):
        data = load_data()
        gid  = str(ctx.guild.id)
        ch_id = str(ctx.channel.id)

        ticket = data.get(gid, {}).get("tickets", {}).get(ch_id)
        if not ticket:
            return await ctx.send(view=quick_view("This is not a ticket channel!"))

        if not await _ticket_check_staff_ctx(ctx):
            return

        await ctx.send(view=quick_view(
            f"**Deleting ticket in 5 seconds...**\n"
            f"Transcript will be sent to your DMs."
        ))

        await asyncio.sleep(5)
        await _do_delete_ticket(self, ctx.channel, ctx.author)

    @commands.command(name="ticketsync", aliases=["tsync"])
    @commands.is_owner()
    async def ticket_sync(self, ctx):
        try:
            synced = await self.bot.tree.sync()
            cmds_list = "\n".join(f"`/{c.name}`" for c in synced) or "*None*"
            await ctx.send(view=quick_view(
                f"**Synced {len(synced)} slash commands!**\n\n{cmds_list}"
            ))
        except Exception as e:
            traceback.print_exc()
            await ctx.send(view=quick_view(f"Sync failed: `{e}`"))


async def setup(bot):
    await bot.add_cog(TicketCog(bot))
