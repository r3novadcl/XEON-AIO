import discord
from discord.ext import commands
from utils import emojis as E

BLACK = discord.Colour(0x000000)


class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="userinfo", aliases=["ui", "whois", "who"])
    @commands.guild_only()
    async def userinfo(self, ctx, member: discord.Member = None):
        member   = member or ctx.author
        av_url   = member.display_avatar.url

        joined   = discord.utils.format_dt(member.joined_at, style="F") if member.joined_at else "Unknown"
        joined_r = discord.utils.format_dt(member.joined_at, style="R") if member.joined_at else ""
        created  = discord.utils.format_dt(member.created_at, style="F")
        created_r= discord.utils.format_dt(member.created_at, style="R")

        roles    = [r for r in member.roles if r.name != "@everyone"]
        role_str = ", ".join(r.mention for r in reversed(roles[:10]))
        if len(roles) > 10:
            role_str += f" +{len(roles)-10} more"

        badges = []
        flags  = member.public_flags
        if flags.staff              : badges.append("Discord Staff")
        if flags.partner            : badges.append("Partnered Server Owner")
        if flags.hypesquad          : badges.append("HypeSquad Events")
        if flags.bug_hunter         : badges.append("Bug Hunter")
        if flags.hypesquad_bravery  : badges.append("HypeSquad Bravery")
        if flags.hypesquad_brilliance: badges.append("HypeSquad Brilliance")
        if flags.hypesquad_balance  : badges.append("HypeSquad Balance")
        if flags.early_supporter    : badges.append("Early Supporter")
        if flags.bug_hunter_level_2 : badges.append("Bug Hunter Level 2")
        if flags.verified_bot_developer: badges.append("Verified Bot Developer")
        if flags.active_developer   : badges.append("Active Developer")
        badge_str = ", ".join(badges) if badges else "None"

        status_map = {
            discord.Status.online   : f"{E.ONLINE} Online",
            discord.Status.idle     : f"{E.IDLE} Idle",
            discord.Status.dnd      : " Do Not Disturb",
            discord.Status.offline  : f"{E.OFFLINE} Offline",
        }
        status_str = status_map.get(member.status, "Unknown")

        key_perms = []
        p = member.guild_permissions
        if p.administrator      : key_perms.append("Administrator")
        if p.manage_guild       : key_perms.append("Manage Server")
        if p.manage_roles       : key_perms.append("Manage Roles")
        if p.manage_channels    : key_perms.append("Manage Channels")
        if p.manage_messages    : key_perms.append("Manage Messages")
        if p.kick_members       : key_perms.append("Kick Members")
        if p.ban_members        : key_perms.append("Ban Members")
        perm_str = ", ".join(key_perms) if key_perms else "None"

        container = discord.ui.Container(accent_color=BLACK)

        section = discord.ui.Section(
            accessory=discord.ui.Thumbnail(media=av_url)
        )
        section.add_item(discord.ui.TextDisplay(
            content=f"{E.USER}  **{member.display_name}'s Info**"
        ))
        section.add_item(discord.ui.TextDisplay(
            content=(
                f"**Username :** {member.name}\n"
                f"**Display  :** {member.display_name}\n"
                f"**ID       :** `{member.id}`"
            )
        ))
        container.add_item(section)
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.CALENDAR} Dates**"
        ))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"**Joined  :** {joined} ({joined_r})\n"
                f"**Created :** {created} ({created_r})"
            )
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.INFO} Status & Badges**"
        ))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"**Status :** {status_str}\n"
                f"**Bot    :** {'Yes' if member.bot else 'No'}\n"
                f"**Badges :** {badge_str}"
            )
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.ROLE} Roles [{len(roles)}]**"
        ))
        container.add_item(discord.ui.TextDisplay(
            content=role_str or "None"
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.SHIELD} Key Permissions**"
        ))
        container.add_item(discord.ui.TextDisplay(content=perm_str))
        container.add_item(discord.ui.Separator())

        ts = discord.utils.format_dt(ctx.message.created_at, style="f")
        container.add_item(discord.ui.TextDisplay(
            content=f"Requested by {ctx.author.mention} | {ts}"
        ))

        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)


async def setup(bot):
    await bot.add_cog(UserInfo(bot))
