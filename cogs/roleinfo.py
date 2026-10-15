import discord
from discord.ext import commands
from utils import emojis as E

BLACK = discord.Colour(0x000000)


class RoleInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="roleinfo", aliases=["ri", "rinfo"])
    @commands.guild_only()
    async def roleinfo(self, ctx, role: discord.Role = None):
        if not role:
            from utils.ui import denied_container
            return await ctx.send(**denied_container("Please mention a role!"))

        created   = discord.utils.format_dt(role.created_at, style="F")
        created_r = discord.utils.format_dt(role.created_at, style="R")
        color_str = str(role.colour) if role.colour.value else "Default"
        members   = len(role.members)
        position  = role.position
        mentionable = "Yes" if role.mentionable else "No"
        hoisted   = "Yes" if role.hoist else "No"
        managed   = "Yes" if role.managed else "No"

        key_perms = []
        p = role.permissions
        if p.administrator      : key_perms.append("Administrator")
        if p.manage_guild       : key_perms.append("Manage Server")
        if p.manage_roles       : key_perms.append("Manage Roles")
        if p.manage_channels    : key_perms.append("Manage Channels")
        if p.manage_messages    : key_perms.append("Manage Messages")
        if p.kick_members       : key_perms.append("Kick Members")
        if p.ban_members        : key_perms.append("Ban Members")
        if p.mention_everyone   : key_perms.append("Mention Everyone")
        perm_str = ", ".join(key_perms) if key_perms else "None"

        mem_str = ", ".join(m.mention for m in role.members[:10])
        if len(role.members) > 10:
            mem_str += f" +{len(role.members)-10} more"

        container = discord.ui.Container(accent_color=BLACK)
        container.add_item(discord.ui.TextDisplay(
            content=f"{E.ROLE}  **{role.name}'s Info**"
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.INFO} About Role**"
        ))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"**Name        :** {role.mention}\n"
                f"**ID          :** `{role.id}`\n"
                f"**Color       :** `{color_str}`\n"
                f"**Position    :** `{position}`\n"
                f"**Members     :** `{members}`\n"
                f"**Hoisted     :** `{hoisted}`\n"
                f"**Mentionable :** `{mentionable}`\n"
                f"**Managed     :** `{managed}`\n"
                f"**Created     :** {created} ({created_r})"
            )
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.SHIELD} Key Permissions**"
        ))
        container.add_item(discord.ui.TextDisplay(content=perm_str))
        container.add_item(discord.ui.Separator())

        if mem_str:
            container.add_item(discord.ui.TextDisplay(
                content=f"**{E.MEMBERS} Members**"
            ))
            container.add_item(discord.ui.TextDisplay(content=mem_str))
            container.add_item(discord.ui.Separator())

        ts = discord.utils.format_dt(ctx.message.created_at, style="f")
        container.add_item(discord.ui.TextDisplay(
            content=f"Requested by {ctx.author.mention} | {ts}"
        ))

        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)


async def setup(bot):
    await bot.add_cog(RoleInfo(bot))
