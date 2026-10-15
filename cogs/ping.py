from discord.ext import commands
import time
from utils.ui import ping_container, info_container
from utils import emojis as E


class Ping(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping", aliases=["latency", "ms"])
    async def ping(self, ctx):

        ws_ms = round(self.bot.latency * 1000)

        t   = time.perf_counter()
        tmp = await ctx.send(f"{E.LOADING} Pinging…")
        msg_ms = round((time.perf_counter() - t) * 1000)
        api_ms = round(self.bot.latency * 1000)

        kwargs = ping_container(
            ws_ms      = ws_ms,
            msg_ms     = msg_ms,
            api_ms     = api_ms,
            bot_avatar = self.bot.user.display_avatar.url,
        )
        await tmp.edit(content=None, **kwargs)

    @commands.command(name="pong")
    async def pong(self, ctx):
        ws_ms  = round(self.bot.latency * 1000)
        kwargs = info_container(
            f"Pong! {E.PONG}",
            f"Latency: `{ws_ms}ms`",
        )
        await ctx.send(**kwargs)


async def setup(bot):
    await bot.add_cog(Ping(bot))
