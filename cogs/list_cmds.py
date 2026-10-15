import discord
from discord.ext import commands
from discord import ui
from utils import emojis as E
from XEON.emojis import partial
from utils.category_help import send_category_help

BLACK          = discord.Colour(0x000000)
ITEMS_PER_PAGE = 10

NAV_FIRST  = partial("FIRST")
NAV_PREV   = partial("PREV")
NAV_DELETE = partial("DELETE")
NAV_NEXT   = partial("NEXT")
NAV_LAST   = partial("LAST")


class ListPaginatorView(ui.LayoutView):
    def __init__(self, ctx, title: str, items: list[str], header: str = None):
        super().__init__(timeout=120)
        self.ctx    = ctx
        self.title  = title
        self.items  = items
        self.header = header
        self.page   = 0
        self._rebuild()

    def _total_pages(self) -> int:
        return max(1, -(-len(self.items) // ITEMS_PER_PAGE))

    def _build_container(self) -> ui.Container:
        total      = self._total_pages()
        start      = self.page * ITEMS_PER_PAGE
        end        = start + ITEMS_PER_PAGE
        page_items = self.items[start:end]

        container = ui.Container(accent_color=BLACK)
        container.add_item(ui.TextDisplay(
            content=f"{E.LIST}  **{self.title} [{len(self.items)}]**"
        ))

        if self.header:
            container.add_item(ui.TextDisplay(content=self.header))

        container.add_item(ui.Separator())

        body = "\n".join(
            f"**[{start + i + 1:02d}]**  {item}"
            for i, item in enumerate(page_items)
        )
        container.add_item(ui.TextDisplay(content=body or "*No items found.*"))
        container.add_item(ui.Separator())

        container.add_item(ui.TextDisplay(
            content=(
                f"Page `{self.page + 1}/{total}` | "
                f"Requested by {self.ctx.author.mention}"
            )
        ))

        return container

    def _build_nav_row(self) -> ui.ActionRow:
        total = self._total_pages()
        nav_row = ui.ActionRow(
            ui.Button(
                emoji=NAV_FIRST,
                style=discord.ButtonStyle.secondary,
                custom_id="lp_first",
                disabled=(self.page == 0),
            ),
            ui.Button(
                emoji=NAV_PREV,
                style=discord.ButtonStyle.secondary,
                custom_id="lp_prev",
                disabled=(self.page == 0),
            ),
            ui.Button(
                emoji=NAV_DELETE,
                style=discord.ButtonStyle.danger,
                custom_id="lp_delete",
            ),
            ui.Button(
                emoji=NAV_NEXT,
                style=discord.ButtonStyle.secondary,
                custom_id="lp_next",
                disabled=(self.page >= total - 1),
            ),
            ui.Button(
                emoji=NAV_LAST,
                style=discord.ButtonStyle.secondary,
                custom_id="lp_last",
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
                f"{E.DENIED} This is not your list!", ephemeral=True
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
        if self.page > 0: self.page -= 1
        self._rebuild()
        await interaction.response.edit_message(view=self)

    async def _next(self, interaction: discord.Interaction):
        if not await self._guard(interaction): return
        if self.page < self._total_pages() - 1: self.page += 1
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


class RoleListView(ui.LayoutView):
    def __init__(self, ctx, roles: list[discord.Role]):
        super().__init__(timeout=120)
        self.ctx   = ctx
        self.roles = roles
        self.page  = 0
        self._rebuild()

    def _total_pages(self) -> int:
        return max(1, -(-len(self.roles) // ITEMS_PER_PAGE))

    def _build_container(self) -> ui.Container:
        total      = self._total_pages()
        start      = self.page * ITEMS_PER_PAGE
        page_roles = self.roles[start : start + ITEMS_PER_PAGE]

        container = ui.Container(accent_color=BLACK)
        container.add_item(ui.TextDisplay(
            content=f"{E.LIST}  **Role's list [{len(self.roles)}]**"
        ))
        container.add_item(ui.Separator())

        lines = []
        for i, role in enumerate(page_roles):
            lines.append(
                f"**[{start + i + 1:02d}]**  {role.mention}"
                f"  →  `{role.id}`  →  **{len(role.members)}**"
            )
        container.add_item(ui.TextDisplay(
            content="\n".join(lines) or "*No roles found.*"
        ))
        container.add_item(ui.Separator())

        container.add_item(ui.TextDisplay(
            content=(
                f"Page `{self.page + 1}/{total}` | "
                f"Requested by {self.ctx.author.mention}"
            )
        ))

        return container

    def _build_nav_row(self) -> ui.ActionRow:
        total = self._total_pages()
        nav_row = ui.ActionRow(
            ui.Button(
                emoji=NAV_FIRST,
                style=discord.ButtonStyle.secondary,
                custom_id="rl_first",
                disabled=(self.page == 0),
            ),
            ui.Button(
                emoji=NAV_PREV,
                style=discord.ButtonStyle.secondary,
                custom_id="rl_prev",
                disabled=(self.page == 0),
            ),
            ui.Button(
                emoji=NAV_DELETE,
                style=discord.ButtonStyle.danger,
                custom_id="rl_delete",
            ),
            ui.Button(
                emoji=NAV_NEXT,
                style=discord.ButtonStyle.secondary,
                custom_id="rl_next",
                disabled=(self.page >= total - 1),
            ),
            ui.Button(
                emoji=NAV_LAST,
                style=discord.ButtonStyle.secondary,
                custom_id="rl_last",
                disabled=(self.page >= total - 1),
            ),
        )
        nav_row.children[0].callback = self._first
        nav_row.children[1].callback = self._prev
        nav_row.children[2].callback = self._delete
        nav_row.children[3].callback = self._next
        nav_row.children[4].callback = self._last
        return nav_row

    def _build_sort_row(self) -> ui.ActionRow:
        sort_row = ui.ActionRow(
            ui.Button(
                label="Sort by Members",
                style=discord.ButtonStyle.secondary,
                custom_id="rl_sort",
            ),
        )
        sort_row.children[0].callback = self._sort
        return sort_row

    def _rebuild(self):
        self.clear_items()
        self.add_item(self._build_container())
        self.add_item(self._build_nav_row())
        self.add_item(self._build_sort_row())

    async def _guard(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                f"{E.DENIED} This is not your list!", ephemeral=True
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
        if self.page > 0: self.page -= 1
        self._rebuild()
        await interaction.response.edit_message(view=self)

    async def _next(self, interaction: discord.Interaction):
        if not await self._guard(interaction): return
        if self.page < self._total_pages() - 1: self.page += 1
        self._rebuild()
        await interaction.response.edit_message(view=self)

    async def _last(self, interaction: discord.Interaction):
        if not await self._guard(interaction): return
        self.page = self._total_pages() - 1
        self._rebuild()
        await interaction.response.edit_message(view=self)

    async def _sort(self, interaction: discord.Interaction):
        if not await self._guard(interaction): return
        self.roles = sorted(self.roles, key=lambda r: len(r.members), reverse=True)
        self.page  = 0
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


class ListCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_list(
        self,
        ctx,
        title : str,
        items : list[str],
        header: str = None,
    ):
        if not items:
            from utils.ui import denied_container
            return await ctx.send(**denied_container(f"No {title.lower()} found!"))
        view = ListPaginatorView(ctx, title, items, header)
        await ctx.send(view=view)

    @commands.group(
        name    ="list",
        aliases =["ls"],
        invoke_without_command=True,
    )
    @commands.guild_only()
    async def list_group(self, ctx):
        await send_category_help(ctx, "list", self.bot)

    @list_group.command(name="roles")
    @commands.guild_only()
    async def list_roles(self, ctx):
        roles = [r for r in reversed(ctx.guild.roles) if r.name != "@everyone"]
        if not roles:
            from utils.ui import denied_container
            return await ctx.send(**denied_container("No roles found!"))
        view = RoleListView(ctx, roles)
        await ctx.send(view=view)

    @list_group.command(name="users")
    @commands.guild_only()
    async def list_users(self, ctx):
        members = [
            f"{m.mention}  →  `{m.id}`"
            for m in ctx.guild.members
            if not m.bot
        ]
        await self._send_list(ctx, "Users list", members)

    @list_group.command(name="bots")
    @commands.guild_only()
    async def list_bots(self, ctx):
        bots = [
            f"{m.mention}  →  `{m.id}`"
            for m in ctx.guild.members
            if m.bot
        ]
        await self._send_list(ctx, "Bots list", bots)

    @list_group.command(name="bans")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def list_bans(self, ctx):
        bans = [
            f"`{entry.user.name}`  →  `{entry.user.id}`  →  "
            f"`{entry.reason or 'No reason'}`"
            async for entry in ctx.guild.bans()
        ]
        await self._send_list(ctx, "Bans list", bans)

    @list_group.command(name="boosters")
    @commands.guild_only()
    async def list_boosters(self, ctx):
        boosters = [
            f"{m.mention}  →  `{m.id}`  →  "
            f"{discord.utils.format_dt(m.premium_since, style='R')}"
            for m in ctx.guild.premium_subscribers
        ]
        await self._send_list(ctx, "Boosters list", boosters)

    @list_group.command(name="emojis")
    @commands.guild_only()
    async def list_emojis(self, ctx):
        emojis = [
            f"{e}  `:{e.name}:`  →  `{e.id}`"
            for e in ctx.guild.emojis
        ]
        await self._send_list(ctx, "Emojis list", emojis)

    @list_group.command(name="channels")
    @commands.guild_only()
    async def list_channels(self, ctx):
        channels = [
            f"{ch.mention}  →  `{ch.id}`"
            for ch in ctx.guild.text_channels
        ]
        await self._send_list(ctx, "Channels list", channels)

    @list_group.command(name="timeouts")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def list_timeouts(self, ctx):
        muted = [
            f"{m.mention}  →  `{m.id}`  →  "
            f"{discord.utils.format_dt(m.timed_out_until, style='R')}"
            for m in ctx.guild.members
            if m.timed_out_until
        ]
        await self._send_list(ctx, "Timeouts list", muted)

    @list_group.command(name="hasperms", aliases=["hasperm"])
    @commands.guild_only()
    async def list_hasperms(self, ctx, *, permission: str = None):
        if not permission:
            from utils.ui import denied_container
            return await ctx.send(**denied_container(
                "Provide a permission name! e.g. `ban_members`"
            ))
        perm_name = permission.lower().replace(" ", "_").replace("-", "_")
        members = [
            f"{m.mention}  →  `{m.id}`"
            for m in ctx.guild.members
            if not m.bot and getattr(m.guild_permissions, perm_name, False)
        ]
        await self._send_list(ctx, f"Has `{perm_name}` list", members)

    @list_group.command(name="admins", aliases=["admin"])
    @commands.guild_only()
    async def list_admins(self, ctx):
        admins = [
            f"{m.mention}  →  `{m.id}`"
            for m in ctx.guild.members
            if m.guild_permissions.administrator and not m.bot
        ]
        await self._send_list(ctx, "Admins list", admins)

    @list_group.command(name="mods", aliases=["mod"])
    @commands.guild_only()
    async def list_mods(self, ctx):
        mods = [
            f"{m.mention}  →  `{m.id}`"
            for m in ctx.guild.members
            if m.guild_permissions.manage_messages
            and not m.guild_permissions.administrator
            and not m.bot
        ]
        await self._send_list(ctx, "Mods list", mods)

    @list_group.command(name="inrole")
    @commands.guild_only()
    async def list_inrole(self, ctx, role: discord.Role = None):
        if not role:
            from utils.ui import denied_container
            return await ctx.send(**denied_container("Please mention a role!"))
        members = [f"{m.mention}  →  `{m.id}`" for m in role.members]
        await self._send_list(ctx, f"In @{role.name} list", members)

    @list_group.command(name="hypesquad")
    @commands.guild_only()
    async def list_hypesquad(self, ctx):
        items = []
        for m in ctx.guild.members:
            if m.bot:
                continue
            flags = m.public_flags
            house = None
            if flags.hypesquad_bravery   : house = "Bravery"
            if flags.hypesquad_brilliance: house = "Brilliance"
            if flags.hypesquad_balance   : house = "Balance"
            if house:
                items.append(f"{m.mention}  →  `{m.id}`  →  `{house}`")
        await self._send_list(ctx, "HypeSquad list", items)

    @list_group.command(name="pending")
    @commands.guild_only()
    async def list_pending(self, ctx):
        pending = [
            f"{m.mention}  →  `{m.id}`"
            for m in ctx.guild.members
            if m.pending
        ]
        await self._send_list(ctx, "Pending list", pending)

    @list_group.command(name="invoice", aliases=["invc", "invchannel"])
    @commands.guild_only()
    async def list_invoice(self, ctx):
        vc_members = []
        for vc in ctx.guild.voice_channels:
            for m in vc.members:
                vc_members.append(
                    f"{m.mention}  →  `{m.id}`  →  `#{vc.name}`"
                )
        await self._send_list(ctx, "In Voice list", vc_members)

    @list_group.command(name="activedeveloper", aliases=["activedev", "adev"])
    @commands.guild_only()
    async def list_activedeveloper(self, ctx):
        devs = [
            f"{m.mention}  →  `{m.id}`"
            for m in ctx.guild.members
            if m.public_flags.active_developer
        ]
        await self._send_list(ctx, "Active Developer list", devs)

    @list_group.command(name="joinedat", aliases=["joindate"])
    @commands.guild_only()
    async def list_joinedat(self, ctx):
        sorted_members = sorted(
            [m for m in ctx.guild.members if m.joined_at],
            key=lambda m: m.joined_at,
        )
        items = [
            f"{m.mention}  →  "
            f"{discord.utils.format_dt(m.joined_at, style='D')}"
            for m in sorted_members
        ]
        await self._send_list(ctx, "Joined At list", items)

    @list_group.command(name="early", aliases=["earlysupporter"])
    @commands.guild_only()
    async def list_early(self, ctx):
        early = [
            f"{m.mention}  →  `{m.id}`"
            for m in ctx.guild.members
            if m.public_flags.early_supporter
        ]
        await self._send_list(ctx, "Early Supporter list", early)

    @list_group.command(name="createdat", aliases=["accountage"])
    @commands.guild_only()
    async def list_createdat(self, ctx):
        sorted_members = sorted(
            ctx.guild.members,
            key=lambda m: m.created_at,
        )
        items = [
            f"{m.mention}  →  "
            f"{discord.utils.format_dt(m.created_at, style='D')}"
            for m in sorted_members
        ]
        await self._send_list(ctx, "Created At list", items)

    @list_group.command(name="bughunters", aliases=["bughunter"])
    @commands.guild_only()
    async def list_bughunters(self, ctx):
        hunters = [
            f"{m.mention}  →  `{m.id}`  →  "
            f"`{'Level 2' if m.public_flags.bug_hunter_level_2 else 'Level 1'}`"
            for m in ctx.guild.members
            if m.public_flags.bug_hunter or m.public_flags.bug_hunter_level_2
        ]
        await self._send_list(ctx, "Bug Hunters list", hunters)


async def setup(bot):
    await bot.add_cog(ListCommands(bot))
