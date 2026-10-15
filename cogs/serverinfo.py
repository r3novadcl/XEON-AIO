import discord
from discord.ext import commands
from utils import emojis as E

BLACK = discord.Colour(0x000000)

VER_LEVELS = {
    discord.VerificationLevel.none    : "None",
    discord.VerificationLevel.low     : "Low",
    discord.VerificationLevel.medium  : "Medium",
    discord.VerificationLevel.high    : "High",
    discord.VerificationLevel.highest : "Highest",
}

MFA_LEVELS = {
    0: "Disabled",
    1: "Enabled",
}

FILTER_LEVELS = {
    discord.ContentFilter.disabled              : "Disabled",
    discord.ContentFilter.no_role               : "No Role",
    discord.ContentFilter.all_members           : "All Members",
}


class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="serverinfo", aliases=["si", "guildinfo", "server"])
    @commands.guild_only()
    async def serverinfo(self, ctx):
        guild = ctx.guild

        total_members = guild.member_count
        humans        = sum(1 for m in guild.members if not m.bot)
        bots          = sum(1 for m in guild.members if m.bot)
        text_ch       = len(guild.text_channels)
        voice_ch      = len(guild.voice_channels)
        stage_ch      = len(guild.stage_channels)
        categories    = len(guild.categories)
        roles         = guild.roles[1:]
        emojis_reg    = sum(1 for e in guild.emojis if not e.animated)
        emojis_anim   = sum(1 for e in guild.emojis if e.animated)
        stickers      = len(guild.stickers)
        boost_level   = guild.premium_tier
        boost_count   = guild.premium_subscription_count
        boosters      = guild.premium_subscribers
        booster_role  = guild.premium_subscriber_role

        owner         = guild.owner
        created_at    = discord.utils.format_dt(guild.created_at, style="R")
        ver_level     = VER_LEVELS.get(guild.verification_level, "Unknown")
        mfa_level     = MFA_LEVELS.get(guild.mfa_level, "Unknown")
        content_filt  = FILTER_LEVELS.get(guild.explicit_content_filter, "Unknown")
        features      = guild.features

        role_str = ", ".join(r.mention for r in reversed(roles[:10]))
        if len(roles) > 10:
            role_str += f" +{len(roles)-10} more"

        feat_str = "\n".join(
            f"> {E.SUCCESS}  {f.replace('_', ' ').title()}"
            for f in features
        ) or f"> {E.DENIED}  None"

        icon_url = guild.icon.url if guild.icon else None

        container = discord.ui.Container(accent_color=BLACK)

        if icon_url:
            section = discord.ui.Section(
                accessory=discord.ui.Thumbnail(media=icon_url)
            )
            section.add_item(discord.ui.TextDisplay(
                content=f"{E.SERVER}  **{guild.name}'s Info**"
            ))
            container.add_item(section)
        else:
            container.add_item(discord.ui.TextDisplay(
                content=f"{E.SERVER}  **{guild.name}'s Info**"
            ))

        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.INFO} About Server**"
        ))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"**Name :** {guild.name}\n"
                f"**Server ID :** {guild.id}\n"
                f"**Owner {E.CROWN} :** {owner.mention if owner else 'Unknown'}\n"
                f"**Created At :** {created_at}\n"
                f"**Total Members :** {total_members}"
            )
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.SHIELD} Extras**"
        ))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"**Verification Level :** {ver_level}\n"
                f"**MFA Level :** {MFA_LEVELS.get(guild.mfa_level, 'Unknown')}\n"
                f"**Content Filter :** {content_filt}"
            )
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.GLOBE} Features**"
        ))
        container.add_item(discord.ui.TextDisplay(content=feat_str))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.MEMBERS} Members**"
        ))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"**Total Members :** {total_members}\n"
                f"**Humans :** {humans}\n"
                f"**Bots :** {bots}"
            )
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.CHANNEL} Channels**"
        ))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"**Categories :** {categories}\n"
                f"**Text Channels :** {text_ch}\n"
                f"**Voice Channels :** {voice_ch}\n"
                f"**Stage Channels :** {stage_ch}"
            )
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.EMOJI_ICO} Emojis**"
        ))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"**Regular emojis :** {emojis_reg}\n"
                f"**Animated emojis :** {emojis_anim}\n"
                f"**Stickers :** {stickers}\n"
                f"**Total :** {emojis_reg + emojis_anim}"
            )
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.BOOST} Boosts**"
        ))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"**Boost Level :** {boost_level} Level\n"
                f"**Boost count :** {boost_count}\n"
                f"**Boosters :** {len(boosters)}\n"
                f"**Booster Role :** "
                f"{booster_role.mention if booster_role else 'None'}"
            )
        ))
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            content=f"**{E.ROLE} Roles**"
        ))
        container.add_item(discord.ui.TextDisplay(content=role_str or "None"))
        container.add_item(discord.ui.Separator())

        ts = discord.utils.format_dt(ctx.message.created_at, style="f")
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"Requested by {ctx.author.mention} | {ts}"
            )
        ))

        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)


async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
