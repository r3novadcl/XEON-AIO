import discord
from discord.ext import commands
import time
import asyncio
import traceback
from utils import emojis as E

BLACK = discord.Colour(0x000000)


MediaGallery     = None
MediaGalleryItem = None

try:
    MediaGallery     = discord.ui.MediaGallery
    MediaGalleryItem = discord.ui.MediaGalleryItem
except AttributeError:
    pass

if MediaGalleryItem is None:
    try:
        MediaGalleryItem = discord.MediaGalleryItem
    except AttributeError:
        pass

if MediaGallery is None:
    try:
        MediaGallery = discord.MediaGallery
    except AttributeError:
        pass

if MediaGalleryItem is None:
    try:
        from discord.components import MediaGalleryItem as _MGI
        MediaGalleryItem = _MGI
    except (ImportError, AttributeError):
        pass

if MediaGallery is None:
    try:
        from discord.components import MediaGallery as _MG
        MediaGallery = _MG
    except (ImportError, AttributeError):
        pass

UnfurledMediaItem = None
try:
    UnfurledMediaItem = discord.UnfurledMediaItem
except AttributeError:
    try:
        UnfurledMediaItem = discord.ui.UnfurledMediaItem
    except AttributeError:
        pass

HAS_MEDIA_GALLERY = MediaGallery is not None and MediaGalleryItem is not None

print(f"[general.py] MediaGallery available: {HAS_MEDIA_GALLERY}")


def _fmt_duration(seconds: int) -> str:
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _make_media_item(url: str):
    if MediaGalleryItem is None:
        return None
    try:
        return MediaGalleryItem(media=url)
    except TypeError:
        pass
    try:
        if UnfurledMediaItem is not None:
            return MediaGalleryItem(media=UnfurledMediaItem(url=url))
    except Exception:
        pass
    try:
        return MediaGalleryItem(url)
    except Exception:
        pass
    return None


def _build_image_container(
    title      : str,
    fmt_str    : str,
    image_url  : str,
    requester  : discord.Member,
) -> discord.ui.Container:
    container = discord.ui.Container(accent_color=BLACK)
    container.add_item(discord.ui.TextDisplay(
        content=f"**{title}**\n{fmt_str}"
    ))

    added_image = False
    if HAS_MEDIA_GALLERY:
        try:
            item = _make_media_item(image_url)
            if item is not None:
                gallery = MediaGallery(item)
                container.add_item(gallery)
                added_image = True
        except Exception as e:
            print(f"[_build_image_container] MediaGallery failed: {e}")

    if not added_image:
        container.add_item(discord.ui.TextDisplay(
            content=f"[Click here to view image]({image_url})"
        ))

    container.add_item(discord.ui.TextDisplay(
        content=f"Requested by {requester.mention}"
    ))
    return container


def _get_fmt_links(asset: discord.Asset) -> str:
    try:
        base = str(asset.url).split("?")[0]
        parts = []
        if asset.is_animated():
            parts.append(f"[GIF]({base}?size=4096&format=gif)")
        parts.append(f"[PNG]({base}?size=4096&format=png)")
        parts.append(f"[JPG]({base}?size=4096&format=jpg)")
        parts.append(f"[WEBP]({base}?size=4096&format=webp)")
        return " | ".join(parts)
    except Exception:
        return f"[Link]({asset.url})"


def _get_best_url(asset: discord.Asset) -> str:
    try:
        if asset.is_animated():
            return asset.replace(size=4096, format="gif").url
        return asset.replace(size=4096, format="png").url
    except Exception:
        return str(asset.url)


def _no_asset_view(title: str, message: str) -> discord.ui.LayoutView:
    container = discord.ui.Container(accent_color=BLACK)
    container.add_item(discord.ui.TextDisplay(content=f"**{title}**"))
    container.add_item(discord.ui.Separator(visible=False))
    container.add_item(discord.ui.TextDisplay(content=message))
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(container)
    return view


class General(commands.Cog):
    def __init__(self, bot):
        self.bot     = bot
        self.afk_map = {}

    @commands.command(name="afk", aliases=["away"])
    async def afk(self, ctx, *, reason: str = "AFK"):
        self.afk_map[ctx.author.id] = {
            "reason": reason,
            "time"  : time.time(),
        }

        container = discord.ui.Container(accent_color=BLACK)
        container.add_item(discord.ui.TextDisplay(
            content=f"{E.AFK}  **AFK Set !**"
        ))
        container.add_item(discord.ui.Separator(visible=False))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"> {E.USER}  **User   :** {ctx.author.mention}\n"
                f"> {E.REASON}  **Reason :** `{reason}`"
            )
        ))
        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        if message.author.id in self.afk_map:
            data     = self.afk_map.pop(message.author.id)
            reason   = data["reason"]
            duration = _fmt_duration(int(time.time() - data["time"]))

            container = discord.ui.Container(accent_color=BLACK)
            container.add_item(discord.ui.TextDisplay(
                content=f"{E.SUCCESS}  **Welcome Back, {message.author.display_name} !**"
            ))
            container.add_item(discord.ui.Separator(visible=False))
            container.add_item(discord.ui.TextDisplay(
                content=(
                    f"> {E.AFK}  **AFK Reason   :** `{reason}`\n"
                    f"> {E.CLOCK}  **AFK Duration :** `{duration}`"
                )
            ))
            view = discord.ui.LayoutView(timeout=None)
            view.add_item(container)
            try:
                msg = await message.channel.send(view=view)
                await asyncio.sleep(5)
                await msg.delete()
            except Exception:
                pass
            return

        for mentioned in message.mentions:
            if mentioned.id in self.afk_map and mentioned.id != message.author.id:
                data     = self.afk_map[mentioned.id]
                reason   = data["reason"]
                duration = _fmt_duration(int(time.time() - data["time"]))

                container = discord.ui.Container(accent_color=BLACK)
                container.add_item(discord.ui.TextDisplay(
                    content=f"{E.AFK}  **User is AFK !**"
                ))
                container.add_item(discord.ui.Separator(visible=False))
                container.add_item(discord.ui.TextDisplay(
                    content=(
                        f"> {E.USER}  **User      :** {mentioned.mention}\n"
                        f"> {E.REASON}  **Reason    :** `{reason}`\n"
                        f"> {E.CLOCK}  **AFK Since :** `{duration} ago`"
                    )
                ))
                view = discord.ui.LayoutView(timeout=None)
                view.add_item(container)
                try:
                    await message.channel.send(view=view)
                except Exception:
                    pass

    @commands.command(name="membercount", aliases=["mc", "members"])
    @commands.guild_only()
    async def membercount(self, ctx):
        guild   = ctx.guild
        humans  = sum(1 for m in guild.members if not m.bot)
        bots    = sum(1 for m in guild.members if m.bot)
        total   = guild.member_count
        online  = sum(
            1 for m in guild.members
            if m.status != discord.Status.offline
        )
        offline = total - online

        icon_url  = guild.icon.url if guild.icon else None
        container = discord.ui.Container(accent_color=BLACK)

        if icon_url:
            section = discord.ui.Section(
                accessory=discord.ui.Thumbnail(media=icon_url)
            )
            section.add_item(discord.ui.TextDisplay(
                content=f"{E.MEMBERS}  **Member Count**"
            ))
            section.add_item(discord.ui.TextDisplay(
                content=(
                    f"__**Humans :**__ `{humans}`\n"
                    f"__**Bots   :**__ `{bots}`\n"
                    f"__**Total  :**__ `{total}`"
                )
            ))
            container.add_item(section)
        else:
            container.add_item(discord.ui.TextDisplay(
                content=f"{E.MEMBERS}  **Member Count**"
            ))
            container.add_item(discord.ui.TextDisplay(
                content=(
                    f"__**Humans :**__ `{humans}`\n"
                    f"__**Bots   :**__ `{bots}`\n"
                    f"__**Total  :**__ `{total}`"
                )
            ))

        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"{E.ONLINE}  **Online  :** `{online}`\n"
                f"{E.OFFLINE}  **Offline :** `{offline}`"
            )
        ))

        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="boostcount", aliases=["boosts", "bc"])
    @commands.guild_only()
    async def boostcount(self, ctx):
        guild        = ctx.guild
        boost_count  = guild.premium_subscription_count
        boost_level  = guild.premium_tier
        boosters     = guild.premium_subscribers
        booster_role = guild.premium_subscriber_role

        container = discord.ui.Container(accent_color=BLACK)
        container.add_item(discord.ui.TextDisplay(
            content=f"{E.BOOST}  **Boost Count**"
        ))
        container.add_item(discord.ui.Separator(visible=False))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"> {E.BOOST}  **Boost Level  :** `{boost_level}`\n"
                f"> {E.BOOST}  **Boost Count  :** `{boost_count}`\n"
                f"> {E.MEMBERS}  **Boosters     :** `{len(boosters)}`\n"
                f"> {E.ROLE}  **Booster Role :** "
                f"{booster_role.mention if booster_role else '`None`'}"
            )
        ))

        if boosters:
            booster_list = ", ".join(b.mention for b in boosters[:10])
            if len(boosters) > 10:
                booster_list += f" **+{len(boosters) - 10} more**"
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.TextDisplay(
                content=f"> {E.MEMBERS}  **Boosters :** {booster_list}"
            ))

        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="joinedat", aliases=["joined", "joindate"])
    @commands.guild_only()
    async def joinedat(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        joined = member.joined_at

        if not joined:
            return await ctx.send(
                view=_no_asset_view(
                    "Joined At",
                    f"{E.DENIED} Could not get join date!"
                )
            )

        ts_full = discord.utils.format_dt(joined, style="F")
        ts_rel  = discord.utils.format_dt(joined, style="R")

        container = discord.ui.Container(accent_color=BLACK)
        section   = discord.ui.Section(
            accessory=discord.ui.Thumbnail(media=member.display_avatar.url)
        )
        section.add_item(discord.ui.TextDisplay(
            content=f"{E.JOINED}  **Joined At**"
        ))
        section.add_item(discord.ui.TextDisplay(
            content=(
                f"> {E.USER}  **Member   :** {member.mention}\n"
                f"> {E.CALENDAR}  **Joined   :** {ts_full}\n"
                f"> {E.CLOCK}  **Relative :** {ts_rel}"
            )
        ))
        container.add_item(section)

        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="avatar", aliases=["av", "pfp"])
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await self._send_avatar(ctx, member)

    async def _send_avatar(self, ctx, member: discord.Member):
        try:
            av       = member.display_avatar
            fmt_str  = _get_fmt_links(av)
            img_url  = _get_best_url(av)

            container = _build_image_container(
                title     = f"{member.display_name}'s Avatar",
                fmt_str   = fmt_str,
                image_url = img_url,
                requester = ctx.author,
            )

            has_server_av = bool(member.guild_avatar)
            row = discord.ui.ActionRow(
                discord.ui.Button(
                    label    = "Server Avatar",
                    style    = discord.ButtonStyle.secondary,
                    custom_id= f"av_server_{member.id}",
                    disabled = not has_server_av,
                ),
                discord.ui.Button(
                    label    = "Banner",
                    style    = discord.ButtonStyle.secondary,
                    custom_id= f"av_banner_{member.id}",
                ),
            )

            async def _server_av(inter: discord.Interaction):
                if not member.guild_avatar:
                    return await inter.response.send_message(
                        f"{E.DENIED} No server avatar!", ephemeral=True
                    )
                s_av  = member.guild_avatar
                c2    = _build_image_container(
                    title     = f"{member.display_name}'s Server Avatar",
                    fmt_str   = _get_fmt_links(s_av),
                    image_url = _get_best_url(s_av),
                    requester = ctx.author,
                )
                v2 = discord.ui.LayoutView(timeout=None)
                v2.add_item(c2)
                await inter.response.send_message(view=v2, ephemeral=True)

            async def _banner(inter: discord.Interaction):
                await inter.response.defer(ephemeral=True)
                user_banner = member.banner
                if not user_banner:
                    try:
                        fetched = await self.bot.fetch_user(member.id)
                        user_banner = fetched.banner
                    except Exception:
                        user_banner = None
                if not user_banner:
                    return await inter.followup.send(
                        f"{E.DENIED} This user has no banner!", ephemeral=True
                    )
                c3   = _build_image_container(
                    title     = f"{member.display_name}'s Banner",
                    fmt_str   = _get_fmt_links(user_banner),
                    image_url = _get_best_url(user_banner),
                    requester = ctx.author,
                )
                v3 = discord.ui.LayoutView(timeout=None)
                v3.add_item(c3)
                await inter.followup.send(view=v3, ephemeral=True)

            row.children[0].callback = _server_av
            row.children[1].callback = _banner
            container.add_item(row)

            view = discord.ui.LayoutView(timeout=None)
            view.add_item(container)
            await ctx.send(view=view)
        except Exception as e:
            traceback.print_exc()
            await ctx.send(
                view=_no_asset_view(
                    "Avatar Error",
                    f"{E.ERROR} `{e}`"
                )
            )

    @commands.command(name="banner", aliases=["userbanner", "ub"])
    async def banner(self, ctx, member: discord.Member = None):
        member = member or ctx.author

        try:
            user_banner = member.banner

            if not user_banner:
                try:
                    fetched     = await self.bot.fetch_user(member.id)
                    user_banner = fetched.banner
                except Exception as fetch_err:
                    print(f"[banner] fetch_user failed: {fetch_err}")
                    user_banner = None

            if not user_banner:
                return await ctx.send(
                    view=_no_asset_view(
                        f"{member.display_name}'s Banner",
                        f"{E.DENIED}  This user has no banner set!"
                    )
                )

            container = _build_image_container(
                title     = f"{member.display_name}'s Banner",
                fmt_str   = _get_fmt_links(user_banner),
                image_url = _get_best_url(user_banner),
                requester = ctx.author,
            )

            row = discord.ui.ActionRow(
                discord.ui.Button(
                    label    = "Avatar",
                    style    = discord.ButtonStyle.secondary,
                    custom_id= f"ban_avatar_{member.id}",
                ),
            )

            async def _av_cb(inter: discord.Interaction):
                av = member.display_avatar
                c2 = _build_image_container(
                    title     = f"{member.display_name}'s Avatar",
                    fmt_str   = _get_fmt_links(av),
                    image_url = _get_best_url(av),
                    requester = ctx.author,
                )
                v2 = discord.ui.LayoutView(timeout=None)
                v2.add_item(c2)
                await inter.response.send_message(view=v2, ephemeral=True)

            row.children[0].callback = _av_cb
            container.add_item(row)

            view = discord.ui.LayoutView(timeout=None)
            view.add_item(container)
            await ctx.send(view=view)

        except Exception as e:
            traceback.print_exc()
            await ctx.send(
                view=_no_asset_view(
                    "Banner Error",
                    f"{E.ERROR} `{e}`"
                )
            )

    @commands.command(name="servericon", aliases=["sicon", "icon", "guildicon"])
    @commands.guild_only()
    async def servericon(self, ctx):
        guild = ctx.guild

        if not guild.icon:
            return await ctx.send(
                view=_no_asset_view(
                    f"{guild.name}'s Icon",
                    f"{E.DENIED}  This server has no icon!"
                )
            )

        try:
            ic        = guild.icon
            container = _build_image_container(
                title     = f"{guild.name}'s Icon",
                fmt_str   = _get_fmt_links(ic),
                image_url = _get_best_url(ic),
                requester = ctx.author,
            )

            row = discord.ui.ActionRow(
                discord.ui.Button(
                    label    = "Server Banner",
                    style    = discord.ButtonStyle.secondary,
                    custom_id= f"sic_banner_{guild.id}",
                    disabled = not bool(guild.banner),
                ),
            )

            async def _ban_cb(inter: discord.Interaction):
                if not guild.banner:
                    return await inter.response.send_message(
                        f"{E.DENIED} Server has no banner!", ephemeral=True
                    )
                sb = guild.banner
                c2 = _build_image_container(
                    title     = f"{guild.name}'s Banner",
                    fmt_str   = _get_fmt_links(sb),
                    image_url = _get_best_url(sb),
                    requester = ctx.author,
                )
                v2 = discord.ui.LayoutView(timeout=None)
                v2.add_item(c2)
                await inter.response.send_message(view=v2, ephemeral=True)

            row.children[0].callback = _ban_cb
            container.add_item(row)

            view = discord.ui.LayoutView(timeout=None)
            view.add_item(container)
            await ctx.send(view=view)
        except Exception as e:
            traceback.print_exc()
            await ctx.send(
                view=_no_asset_view(
                    "Server Icon Error",
                    f"{E.ERROR} `{e}`"
                )
            )

    @commands.command(name="serverbanner", aliases=["sbanner", "guildbanner"])
    @commands.guild_only()
    async def serverbanner(self, ctx):
        guild = ctx.guild

        guild_banner = guild.banner
        if not guild_banner:
            try:
                fetched      = await self.bot.fetch_guild(guild.id)
                guild_banner = fetched.banner
            except Exception as fe:
                print(f"[serverbanner] fetch_guild failed: {fe}")
                guild_banner = None

        if not guild_banner:
            return await ctx.send(
                view=_no_asset_view(
                    f"{guild.name}'s Banner",
                    f"{E.DENIED}  This server has no banner!"
                )
            )

        try:
            container = _build_image_container(
                title     = f"{guild.name}'s Banner",
                fmt_str   = _get_fmt_links(guild_banner),
                image_url = _get_best_url(guild_banner),
                requester = ctx.author,
            )

            row = discord.ui.ActionRow(
                discord.ui.Button(
                    label    = "Server Icon",
                    style    = discord.ButtonStyle.secondary,
                    custom_id= f"sb_icon_{guild.id}",
                    disabled = not bool(guild.icon),
                ),
            )

            async def _ic_cb(inter: discord.Interaction):
                if not guild.icon:
                    return await inter.response.send_message(
                        f"{E.DENIED} Server has no icon!", ephemeral=True
                    )
                ic = guild.icon
                c2 = _build_image_container(
                    title     = f"{guild.name}'s Icon",
                    fmt_str   = _get_fmt_links(ic),
                    image_url = _get_best_url(ic),
                    requester = ctx.author,
                )
                v2 = discord.ui.LayoutView(timeout=None)
                v2.add_item(c2)
                await inter.response.send_message(view=v2, ephemeral=True)

            row.children[0].callback = _ic_cb
            container.add_item(row)

            view = discord.ui.LayoutView(timeout=None)
            view.add_item(container)
            await ctx.send(view=view)
        except Exception as e:
            traceback.print_exc()
            await ctx.send(
                view=_no_asset_view(
                    "Server Banner Error",
                    f"{E.ERROR} `{e}`"
                )
            )

    @commands.command(name="invite", aliases=["inv", "botinvite"])
    async def invite(self, ctx):
        bot_id  = self.bot.user.id
        perms   = discord.Permissions(administrator=True)
        inv_url = discord.utils.oauth_url(bot_id, permissions=perms)
        support = self.bot.SUPPORT_SERVER
        website = self.bot.WEBSITE

        container = discord.ui.Container(accent_color=BLACK)
        container.add_item(discord.ui.TextDisplay(
            content=f"**Invite {self.bot.BOT_NAME} !**"
        ))
        container.add_item(discord.ui.Separator(visible=False))
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"{E.ARROW}  Thank you for your interest in using "
                f"**{self.bot.BOT_NAME}**, get ready to maximize the "
                f"security for your server & visit our "
                f"[Website]({website}) for more information."
            )
        ))
        container.add_item(discord.ui.Separator())

        row = discord.ui.ActionRow(
            discord.ui.Button(
                label="Invite Me",
                style=discord.ButtonStyle.link,
                url=inv_url,
            ),
            discord.ui.Button(
                label="Support Server",
                style=discord.ButtonStyle.link,
                url=support,
            ),
        )
        container.add_item(row)

        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="users", aliases=["totalusers", "botusers"])
    async def users(self, ctx):
        guilds      = len(self.bot.guilds)
        total_users = sum(g.member_count for g in self.bot.guilds)

        container = discord.ui.Container(accent_color=BLACK)
        section   = discord.ui.Section(
            accessory=discord.ui.Thumbnail(
                media=self.bot.user.display_avatar.url
            )
        )
        section.add_item(discord.ui.TextDisplay(
            content=f"**{self.bot.BOT_NAME}'s Users !**"
        ))
        section.add_item(discord.ui.TextDisplay(
            content=(
                f"> {E.ARROW}  Total of **__{total_users}__** users"
                f" in **__{guilds}__** servers"
            )
        ))
        container.add_item(section)

        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)


async def setup(bot):
    await bot.add_cog(General(bot))
