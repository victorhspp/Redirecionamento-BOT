import discord
from discord.ext import commands
from discord import app_commands

# Troque pela URL pública da página no GitHub Pages.
VERIFICATION_PAGE_URL = "https://SEU-USUARIO.github.io/SEU-REPOSITORIO/"

class VerificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="painel-verificacao", description="Publica o painel de verificação.")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_verificacao(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Verificação de conta",
            description=(
                "Clique no botão abaixo para confirmar sua conta Discord.\n\n"
                "Você será levado à nossa página de verificação e depois à página oficial do Discord "
                "para autorizar o acesso à sua identidade básica."
            ),
            color=discord.Color.from_rgb(88, 101, 242),
        )
        embed.set_footer(text="Nunca informe sua senha fora de discord.com.")
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(
            label="Verificar conta",
            style=discord.ButtonStyle.link,
            url=VERIFICATION_PAGE_URL,
            emoji="🔐",
        ))
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCog(bot))
