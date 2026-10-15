import discord
from discord import ui
from utils import emojis as E

BLACK = discord.Colour(0x010101)


class Accent:
    DEFAULT = BLACK
    SUCCESS = BLACK
    ERROR   = BLACK
    WARNING = BLACK
    INFO    = BLACK


def denied_container(reason: str) -> dict:
    container = ui.Container(accent_color=BLACK)
    container.add_item(ui.TextDisplay(content="**Process Denied !**"))
    container.add_item(ui.TextDisplay(content=f"{E.DENIED}  {reason}"))

    view = ui.LayoutView(timeout=None)
    view.add_item(container)
    return {"view": view}


def mod_action_container(
    action: str,
    target_name: str,
    moderator_name: str,
    reason: str = None,
    dm_done: bool = False,
    extra_lines: list = None,
    bot_avatar: str = None,
) -> dict:
    dm_emoji   = E.SUCCESS if dm_done else E.DENIED
    reason_str = reason or "No reason provided"

    extra = ""
    if extra_lines:
        extra = "\n" + "\n".join(f"> **{line}**" for line in extra_lines)

    body = (
        f"{E.TARGET}  {target_name}\n"
        f"{E.MODERATOR}  **Moderator :** {moderator_name}\n\n"
        f"{E.CHANNEL}\n"
        f"> **Dm Done ?** {dm_emoji}\n"
        f"> **Reason :** `{reason_str}`"
        f"{extra}"
    )

    container = ui.Container(accent_color=BLACK)
    if bot_avatar:
        section = ui.Section(accessory=ui.Thumbnail(media=bot_avatar))
        section.add_item(ui.TextDisplay(content=f"{E.SUCCESS}  **{action}**"))
        section.add_item(ui.TextDisplay(content=body))
        container.add_item(section)
    else:
        container.add_item(ui.TextDisplay(content=f"{E.SUCCESS}  **{action}**"))
        container.add_item(ui.TextDisplay(content=body))

    view = ui.LayoutView(timeout=None)
    view.add_item(container)
    return {"view": view}


def action_container(
    title: str,
    lines: list,
    accent: discord.Colour = None,
) -> dict:
    container = ui.Container(accent_color=accent or BLACK)
    container.add_item(ui.TextDisplay(content=f"{E.SUCCESS}  **{title}**"))
    if lines:
        container.add_item(ui.TextDisplay(content="\n".join(lines)))

    view = ui.LayoutView(timeout=None)
    view.add_item(container)
    return {"view": view}


def info_container(
    title: str,
    body: str,
    thumbnail_url: str = None,
) -> dict:
    container = ui.Container(accent_color=BLACK)
    if thumbnail_url:
        section = ui.Section(accessory=ui.Thumbnail(media=thumbnail_url))
        section.add_item(ui.TextDisplay(content=f"**{title}**"))
        section.add_item(ui.TextDisplay(content=body))
        container.add_item(section)
    else:
        container.add_item(ui.TextDisplay(content=f"**{title}**"))
        container.add_item(ui.TextDisplay(content=body))

    view = ui.LayoutView(timeout=None)
    view.add_item(container)
    return {"view": view}


def ping_container(
    ws_ms: int,
    msg_ms: int,
    api_ms: int,
    bot_avatar: str,
) -> dict:
    body = (
        f"__**Websocket Latency**__ :  `{ws_ms} ms`\n"
        f"__**Message Latency**__  : `{msg_ms} ms`\n"
        f"__**API Latency**__   :  `{api_ms} ms`"
    )
    container = ui.Container(accent_color=BLACK)
    section   = ui.Section(accessory=ui.Thumbnail(media=bot_avatar))
    section.add_item(ui.TextDisplay(content=f"{E.PING}  **Bot's Latency**"))
    section.add_item(ui.TextDisplay(content=body))
    container.add_item(section)

    view = ui.LayoutView(timeout=None)
    view.add_item(container)
    return {"view": view}


class _ConfirmView(ui.LayoutView):
    def __init__(self, author_id: int, author_name: str):
        super().__init__(timeout=10)
        self.author_id   = author_id
        self.author_name = author_name
        self.value: bool = False
        self._build()

    def _build(self):
        self.clear_items()
        container = ui.Container(accent_color=BLACK)
        container.add_item(
            ui.TextDisplay(content=f"**Do you want to continue?** {E.PROMPT}")
        )
        container.add_item(
            ui.TextDisplay(
                content=(
                    f"\u200b\n"
                    f"Are you sure **{self.author_name}** ?"
                    f" You have `10s` to decide."
                )
            )
        )
        container.add_item(ui.Separator())

        row = ui.ActionRow(
            ui.Button(
                label="Confirm",
                style=discord.ButtonStyle.secondary,
                emoji=E.CONFIRM,
                custom_id="XEON_confirm_yes",
            ),
            ui.Button(
                label="Remove",
                style=discord.ButtonStyle.danger,
                emoji=E.REMOVE,
                custom_id="XEON_confirm_no",
            ),
        )
        row.children[0].callback = self._confirm
        row.children[1].callback = self._remove
        container.add_item(row)
        self.add_item(container)

    async def _confirm(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(
                f"{E.DENIED} This is not your prompt!", ephemeral=True
            )
        self.value = True
        self.stop()
        await interaction.response.defer()

    async def _remove(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(
                f"{E.DENIED} This is not your prompt!", ephemeral=True
            )
        self.value = False
        self.stop()
        await interaction.response.defer()

    async def on_timeout(self):
        self.value = False
        self.stop()


async def confirmation_prompt(ctx, bot_user) -> bool:
    view = _ConfirmView(
        author_id   = ctx.author.id,
        author_name = ctx.author.name,
    )
    msg = await ctx.send(view=view)
    await view.wait()
    try:
        await msg.delete()
    except Exception:
        pass
    return view.value


class _StatsPagedView(ui.LayoutView):

    def __init__(
        self,
        author_id: int,
        bot_name: str,
        bot_avatar: str,
        invite_url: str,
        support_url: str,
        bot_info_body: str,
        team_data: dict,
        partners_data: list,
    ):
        super().__init__(timeout=180)
        self.author_id   = author_id
        self.bot_name    = bot_name
        self.bot_avatar  = bot_avatar
        self.invite_url  = invite_url
        self.support_url = support_url
        self.bot_info_body = bot_info_body
        self.team_data     = team_data
        self.partners_data = partners_data
        self.current_page  = 0
        self._build()

    def _page_bot_info(self) -> ui.Container:
        container = ui.Container(accent_color=BLACK)
        section   = ui.Section(accessory=ui.Thumbnail(media=self.bot_avatar))
        section.add_item(
            ui.TextDisplay(content=f"## {E.PING}  {self.bot_name} — System Info")
        )
        section.add_item(ui.TextDisplay(content=self.bot_info_body))
        container.add_item(section)
        container.add_item(ui.Separator())
        self._add_controls(container)
        return container

    def _page_team(self) -> ui.Container:
        container = ui.Container(accent_color=BLACK)
        section   = ui.Section(accessory=ui.Thumbnail(media=self.bot_avatar))
        section.add_item(
            ui.TextDisplay(content=f"## {E.INFO}  {self.bot_name} — Team Info")
        )

        body_parts = []
        for role in ("Owner", "Developer", "Staff"):
            members = self.team_data.get(role, [])
            if not members:
                continue
            body_parts.append(f"__**{role}:**__")
            for i, (display_name, username, uid) in enumerate(members, start=1):
                profile_url = f"https://discord.com/users/{uid}"
                body_parts.append(
                    f"`{i}.` [{display_name}]({profile_url})  —  `{username}`"
                )
            body_parts.append("")

        if not body_parts:
            body_parts = ["*No team members configured.*"]

        section.add_item(ui.TextDisplay(content="\n".join(body_parts)))
        container.add_item(section)
        container.add_item(ui.Separator())
        self._add_controls(container)
        return container

    def _page_partners(self) -> ui.Container:
        container = ui.Container(accent_color=BLACK)
        section   = ui.Section(accessory=ui.Thumbnail(media=self.bot_avatar))
        section.add_item(
            ui.TextDisplay(content=f"## {E.INFO}  {self.bot_name} — Partners")
        )

        if not self.partners_data:
            body = "*No partner servers configured yet.*"
        else:
            lines = []
            for i, (name, link, members) in enumerate(self.partners_data, start=1):
                if not name:
                    continue
                if link:
                    lines.append(
                        f"`{i}.` [{name}]({link})  —  `{members} members`"
                    )
                else:
                    lines.append(f"`{i}.` **{name}**  —  `{members} members`")
            body = "\n".join(lines) if lines else "*No partner servers configured yet.*"

        section.add_item(ui.TextDisplay(content=body))
        container.add_item(section)
        container.add_item(ui.Separator())
        self._add_controls(container)
        return container

    def _add_controls(self, container: ui.Container):
        select = ui.Select(
            placeholder="Select a page…",
            min_values=1,
            max_values=1,
            custom_id="stats_page_select",
            options=[
                discord.SelectOption(
                    label="Bot Info",
                    value="0",
                    description="System & runtime information",
                    default=(self.current_page == 0),
                ),
                discord.SelectOption(
                    label="Team Info",
                    value="1",
                    description="Owners, developers & staff",
                    default=(self.current_page == 1),
                ),
                discord.SelectOption(
                    label="Partners",
                    value="2",
                    description="Our amazing partner servers",
                    default=(self.current_page == 2),
                ),
            ],
        )
        select.callback = self._on_select
        container.add_item(ui.ActionRow(select))

        row = ui.ActionRow(
            ui.Button(
                label="Invite",
                style=discord.ButtonStyle.link,
                url=self.invite_url,
            ),
            ui.Button(
                label="Support",
                style=discord.ButtonStyle.link,
                url=self.support_url,
            ),
        )
        container.add_item(row)

    def _build(self):
        self.clear_items()
        if self.current_page == 0:
            self.add_item(self._page_bot_info())
        elif self.current_page == 1:
            self.add_item(self._page_team())
        else:
            self.add_item(self._page_partners())

    async def _on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(
                f"{E.DENIED} This panel isn't for you!", ephemeral=True
            )
        self.current_page = int(interaction.data["values"][0])
        self._build()
        await interaction.response.edit_message(view=self)


def stats_paged_container(
    author_id: int,
    bot_name: str,
    bot_avatar: str,
    invite_url: str,
    support_url: str,
    bot_info_body: str,
    team_data: dict,
    partners_data: list,
) -> _StatsPagedView:
    return _StatsPagedView(
        author_id     = author_id,
        bot_name      = bot_name,
        bot_avatar    = bot_avatar,
        invite_url    = invite_url,
        support_url   = support_url,
        bot_info_body = bot_info_body,
        team_data     = team_data,
        partners_data = partners_data,
    )
