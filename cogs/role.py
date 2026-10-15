import discord
from discord.ext import commands
import asyncio
from utils.ui import (
    denied_container,
    action_container,
    confirmation_prompt,
)
from utils import emojis as E
from utils.category_help import CategoryHelpView, get_category


class Role(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def _role_check(self, ctx, role: discord.Role) -> tuple[bool, str]:
        if role >= ctx.guild.me.top_role:
            return False, "I cannot manage a role higher than or equal to mine!"
        if ctx.author != ctx.guild.owner and role >= ctx.author.top_role:
            return False, "You cannot manage a role higher than your own!"
        return True, ""

    @commands.group(name="role", aliases=["r"], invoke_without_command=True)
    @commands.guild_only()
    async def role(
        self,
        ctx,
        member: discord.Member = None,
        role: discord.Role = None,
    ):

        if member is None:
            cat_key, cat_data = get_category("role")
            view = CategoryHelpView(
                ctx          = ctx,
                category_key = cat_key,
                category_data= cat_data,
                bot_name     = self.bot.BOT_NAME,
                prefix       = ctx.prefix,
            )
            return await ctx.send(view=view)

        if role is None:
            from utils.cmd_help import cmd_usage_view
            view = cmd_usage_view(ctx.prefix, "role")
            return await ctx.send(view=view)

        ok, err = self._role_check(ctx, role)
        if not ok:
            return await ctx.send(**denied_container(err))

        if role in member.roles:
            await member.remove_roles(role)
            action, emoji = "removed from", E.ROLE_REM
        else:
            await member.add_roles(role)
            action, emoji = "added to", E.ROLE_ADD

        await ctx.send(
            **action_container(
                "Role Updated!",
                [
                    f"{emoji} {role.mention} {action} {member.mention}",
                    f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                ],
            )
        )

    @role.command(name="add")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_add(self, ctx, member: discord.Member = None, role: discord.Role = None):
        if not member or not role:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "role"))
        ok, err = self._role_check(ctx, role)
        if not ok:
            return await ctx.send(**denied_container(err))
        if role in member.roles:
            return await ctx.send(**denied_container(f"{member.display_name} already has that role!"))
        await member.add_roles(role)
        await ctx.send(**action_container("Role Added!", [
            f"{E.ROLE_ADD} {role.mention} → {member.mention}",
            f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
        ]))

    @role.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_remove(self, ctx, member: discord.Member = None, role: discord.Role = None):
        if not member or not role:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "role"))
        if role not in member.roles:
            return await ctx.send(**denied_container(f"{member.display_name} doesn't have that role!"))
        await member.remove_roles(role)
        await ctx.send(**action_container("Role Removed!", [
            f"{E.ROLE_REM} {role.mention} from {member.mention}",
            f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
        ]))

    @role.command(name="create")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_create(self, ctx, *, name: str = None):
        if not name:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "role"))
        r = await ctx.guild.create_role(name=name, reason=f"[{ctx.author}]")
        await ctx.send(**action_container("Role Created!", [
            f"{E.ROLE} **Role:** {r.mention}",
            f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
        ]))

    @role.command(name="delete")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_delete(self, ctx, role: discord.Role = None):
        if not role:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "role"))
        ok, err = self._role_check(ctx, role)
        if not ok:
            return await ctx.send(**denied_container(err))
        confirmed = await confirmation_prompt(ctx, self.bot.user)
        if not confirmed:
            return
        name = role.name
        await role.delete(reason=f"[{ctx.author}]")
        await ctx.send(**action_container("Role Deleted!", [
            f"{E.REMOVE} **Role:** `{name}`",
            f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
        ]))

    @role.command(name="rename")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_rename(self, ctx, role: discord.Role = None, *, name: str = None):
        if not role or not name:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "role"))
        old = role.name
        await role.edit(name=name)
        await ctx.send(**action_container("Role Renamed!", [
            f"**Old:** `{old}`",
            f"**New:** {role.mention}",
            f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
        ]))

    @role.command(name="colour", aliases=["color"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_colour(self, ctx, role: discord.Role = None, colour: str = None):
        if not role or not colour:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "role"))
        try:
            c = discord.Colour(int(colour.lstrip('#'), 16))
        except ValueError:
            return await ctx.send(**denied_container("Invalid hex! Example: `#ff0000`"))
        await role.edit(colour=c)
        await ctx.send(**action_container("Role Colour Changed!", [
            f"{E.ROLE} **Role:** {role.mention}",
            f"{E.COLOUR} **Colour:** `#{colour.lstrip('#').upper()}`",
            f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
        ]))

    async def _mass_role(self, ctx, role, filter_fn, label):
        msg = await ctx.send(**action_container(
            f"{E.LOADING} Processing…",
            [f"Adding {role.mention} to {label}…"],
            discord.Colour(0x000000),
        ))
        count = 0
        for member in ctx.guild.members:
            if filter_fn(member) and role not in member.roles:
                try:
                    await member.add_roles(role)
                    count += 1
                    await asyncio.sleep(0.4)
                except Exception:
                    pass
        await msg.edit(**action_container(f"Role Added to {label}!", [
            f"{E.ROLE} **Role:** {role.mention}",
            f"{E.SUCCESS} **Given to:** `{count}` {label}",
            f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
        ]))

    @role.command(name="all")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_all(self, ctx, role: discord.Role = None):
        if not role:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "role"))
        confirmed = await confirmation_prompt(ctx, self.bot.user)
        if not confirmed:
            return
        await self._mass_role(ctx, role, lambda m: True, "All Members")

    @role.command(name="humans")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_humans(self, ctx, role: discord.Role = None):
        if not role:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "role"))
        await self._mass_role(ctx, role, lambda m: not m.bot, "Humans")

    @role.command(name="bots")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_bots(self, ctx, role: discord.Role = None):
        if not role:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "role"))
        await self._mass_role(ctx, role, lambda m: m.bot, "Bots")

    async def _mass_remove(self, ctx, role, filter_fn, label):
        msg = await ctx.send(**action_container(
            f"{E.LOADING} Processing…",
            [f"Removing {role.mention} from {label}…"],
            discord.Colour(0x000000),
        ))
        count = 0
        for member in ctx.guild.members:
            if filter_fn(member) and role in member.roles:
                try:
                    await member.remove_roles(role)
                    count += 1
                    await asyncio.sleep(0.4)
                except Exception:
                    pass
        await msg.edit(**action_container(f"Role Removed from {label}!", [
            f"{E.ROLE} **Role:** {role.mention}",
            f"{E.ROLE_REM} **Removed from:** `{count}` {label}",
            f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
        ]))

    @commands.command(name="rrole")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def rrole(self, ctx, role: discord.Role = None):
        if not role:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "rrole"))
        await self._mass_remove(ctx, role, lambda m: True, "All Members")

    @commands.command(name="rrolehumans", aliases=["rrolehuman"])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def rrolehumans(self, ctx, role: discord.Role = None):
        if not role:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "rrolehumans"))
        await self._mass_remove(ctx, role, lambda m: not m.bot, "Humans")

    @commands.command(name="rrolebots", aliases=["rrolebot"])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def rrolebots(self, ctx, role: discord.Role = None):
        if not role:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "rrolebots"))
        await self._mass_remove(ctx, role, lambda m: m.bot, "Bots")

    @commands.command(name="rroleall")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def rroleall(self, ctx, role: discord.Role = None):
        if not role:
            from utils.cmd_help import cmd_usage_view
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "rroleall"))
        confirmed = await confirmation_prompt(ctx, self.bot.user)
        if not confirmed:
            return
        await self._mass_remove(ctx, role, lambda m: True, "Everyone")


async def setup(bot):
    await bot.add_cog(Role(bot))
