import discord
from discord.ext import commands
from discord import ui
from XEON.emojis import E as _EMGR, partial


_KEYS = {"success": "SUCCESS", "error": "ERROR", "info": "INFO", "build": "INFO"}


def E(key: str) -> discord.PartialEmoji:
    return partial(_KEYS[key])


def ES(key: str) -> str:
    return _EMGR[_KEYS[key]]


DEFAULT_ACCENT = discord.Colour(0x000000)


class EmbedBuilderView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @ui.button(label="Open Builder", style=discord.ButtonStyle.primary)
    async def open_builder(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EmbedBuilderModal())


class EmbedBuilderModal(ui.Modal, title="Personalized Layout Builder"):
    name = ui.TextInput(
        label="Embed Title",
        placeholder="Enter the title of your embed...",
        required=False,
    )
    description = ui.TextInput(
        label="Embed Description",
        placeholder="Enter the content...",
        style=discord.TextStyle.paragraph,
        required=True,
    )
    color = ui.TextInput(
        label="Color (Hex)",
        placeholder="e.g. #000000",
        default="#000000",
        required=False,
    )
    footer = ui.TextInput(
        label="Footer Text",
        placeholder="Text at the bottom...",
        required=False,
    )
    thumbnail = ui.TextInput(
        label="Thumbnail URL",
        placeholder="e.g. https://example.com/image.png",
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        color_val = self.color.value.strip()
        if not color_val.startswith("#"):
            color_val = f"#{color_val}"
        try:
            accent_color = int(color_val.lstrip("#"), 16)
        except ValueError:
            accent_color = 0x000000

        view = ui.LayoutView()
        container = ui.Container(accent_color=accent_color)

        if self.thumbnail.value and self.thumbnail.value.startswith(("http://", "https://")):
            section = ui.Section(
                ui.TextDisplay(f"# {self.name.value}" if self.name.value else ""),
                ui.TextDisplay(self.description.value),
                accessory=ui.Thumbnail(
                    media=discord.UnfurledMediaItem(url=self.thumbnail.value)
                ),
            )
            container.add_item(section)
        else:
            if self.name.value:
                container.add_item(ui.TextDisplay(f"# {self.name.value}"))
                container.add_item(ui.Separator())
            container.add_item(ui.TextDisplay(self.description.value))

        if self.footer.value:
            container.add_item(ui.Separator(visible=True))
            container.add_item(ui.TextDisplay(f"-# {self.footer.value}"))

        view.add_item(container)
        await interaction.channel.send(
            view=view, allowed_mentions=discord.AllowedMentions.none()
        )

        confirm_view = ui.LayoutView()
        confirm_container = ui.Container(accent_color=DEFAULT_ACCENT)
        confirm_container.add_item(
            ui.TextDisplay(f"{ES('success')} Layout successfully created and sent!")
        )
        confirm_view.add_item(confirm_container)
        await interaction.response.send_message(view=confirm_view, ephemeral=True)


class Embeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="embed", help="Create and manage personalized embeds.")
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @embed.command(name="create", help="Open the embed builder modal.")
    @commands.has_permissions(manage_messages=True)
    async def create(self, ctx):
        await ctx.send(
            "### Embed Builder\nClick the button below to start building your layout.",
            view=EmbedBuilderView(),
        )


async def setup(bot):
    await bot.add_cog(Embeds(bot))
