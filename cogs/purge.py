import discord
from discord.ext import commands
import asyncio
import re
from utils.ui import denied_container, action_container, confirmation_prompt
from utils import emojis as E
from utils.cmd_help import cmd_usage_view
from utils.category_help import CategoryHelpView, get_category

BLACK = discord.Colour(0x000000)


class Purge(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def _purge(self, ctx, limit: int, check=None):
        if not 1 <= limit <= 1000:
            return await ctx.send(
                **denied_container("Provide a number between `1` and `1000`!")
            )

        try:
            try:
                await ctx.message.delete()
            except Exception:
                pass

            purge_kwargs = {"limit": limit}
            if check is not None:
                purge_kwargs["check"] = check

            deleted = await ctx.channel.purge(**purge_kwargs)
            count   = len(deleted)

            m = await ctx.send(
                **action_container(
                    "Messages Cleared!",
                    [
                        f"{E.REMOVE} **Deleted:** `{count}` messages",
                        f"{E.CHANNEL} **Channel:** {ctx.channel.mention}",
                        f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                    ],
                )
            )
            await asyncio.sleep(5)
            try:
                await m.delete()
            except Exception:
                pass

        except discord.Forbidden:
            await ctx.send(
                **denied_container("I don't have permission to delete messages here!")
            )
        except discord.HTTPException as e:
            await ctx.send(**denied_container(f"HTTP error: `{e}`"))
        except Exception as e:
            import traceback
            traceback.print_exc()
            await ctx.send(**denied_container(f"An error occurred: `{e}`"))

    @commands.group(
        name="clear",
        aliases=["purge", "clean"],
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clear(self, ctx, amount: int = None):

        if amount is None:
            cat_key, cat_data = get_category("purge")
            view = CategoryHelpView(
                ctx           = ctx,
                category_key  = cat_key,
                category_data = cat_data,
                bot_name      = self.bot.BOT_NAME,
                prefix        = ctx.prefix,
            )
            return await ctx.send(view=view)

        await self._purge(ctx, amount)

    @commands.command(name="clearall", aliases=["purgeall"])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clearall(self, ctx):

        confirmed = await confirmation_prompt(ctx, self.bot.user)
        if not confirmed:
            return

        await self._purge(ctx, 1000)

    @commands.command(name="clearuser", aliases=["purgeuser"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clearuser(
        self,
        ctx,
        member: discord.Member = None,
        amount: int = 100,
    ):

        if member is None:
            return await ctx.send(view=cmd_usage_view(ctx.prefix, "clearuser"))

        await self._purge(ctx, amount, check=lambda m: m.author == member)

    @commands.command(name="clearbots", aliases=["purgebots"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clearbots(self, ctx, amount: int = 100):

        await self._purge(ctx, amount, check=lambda m: m.author.bot)

    @commands.command(name="clearembed", aliases=["clearembeds"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clearembed(self, ctx, amount: int = 100):

        await self._purge(ctx, amount, check=lambda m: bool(m.embeds))

    @commands.command(name="clearmentions")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clearmentions(self, ctx, amount: int = 100):

        await self._purge(
            ctx,
            amount,
            check=lambda m: bool(m.mentions or m.role_mentions),
        )

    @commands.command(name="clearreactions")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clearreactions(self, ctx, amount: int = 100):

        if not 1 <= amount <= 1000:
            return await ctx.send(
                **denied_container("Provide a number between `1` and `1000`!")
            )

        msg = await ctx.send(
            **action_container(
                f"{E.LOADING} Processing…",
                ["Removing reactions, please wait…"],
            )
        )

        n = 0
        try:
            async for message in ctx.channel.history(limit=amount + 1):
                if message.reactions:
                    try:
                        await message.clear_reactions()
                        n += 1
                    except Exception:
                        pass

            await msg.edit(
                **action_container(
                    "Reactions Cleared!",
                    [
                        f"{E.REMOVE} **Cleared from:** `{n}` messages",
                        f"{E.CHANNEL} **Channel:** {ctx.channel.mention}",
                        f"{E.MODERATOR} **Moderator:** {ctx.author.name}",
                    ],
                )
            )
            await asyncio.sleep(5)
            try:
                await msg.delete()
            except Exception:
                pass
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                await msg.edit(
                    **denied_container(f"An error occurred: `{e}`")
                )
            except Exception:
                pass

    @commands.command(name="clearfiles")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clearfiles(self, ctx, amount: int = 100):

        await self._purge(
            ctx,
            amount,
            check=lambda m: bool(m.attachments),
        )

    @commands.command(name="clearimages")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clearimages(self, ctx, amount: int = 100):

        exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
        await self._purge(
            ctx,
            amount,
            check=lambda m: any(
                a.filename.lower().endswith(exts) for a in m.attachments
            ),
        )

    @commands.command(name="clearemoji")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clearemoji(self, ctx, amount: int = 100):

        pattern = re.compile(r'<a?:\w+:\d+>')
        await self._purge(
            ctx,
            amount,
            check=lambda m: bool(pattern.search(m.content or "")),
        )

    @commands.command(name="clearcontain")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clearcontain(self, ctx, *, text: str = None):

        if not text:
            return await ctx.send(
                view=cmd_usage_view(ctx.prefix, "clearcontain")
            )

        await self._purge(
            ctx,
            100,
            check=lambda m: text.lower() in (m.content or "").lower(),
        )


async def setup(bot):
    await bot.add_cog(Purge(bot))
