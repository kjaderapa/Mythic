import discord
from discord.ext import commands
import random

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Placeholder random phrases for /ping response
        self.ping_responses = [
            "Pong! I'm online and ready.",
            "Yes, I'm here!",
            "All systems operational.",
            "At your service!",
            "Ready and waiting."
        ]

    @commands.hybrid_command(name="ping", description="Check if the bot is online and working")
    async def ping(self, ctx):
        """Responds with a random phrase to indicate the bot is online."""
        response = random.choice(self.ping_responses)
        await ctx.send(response)

async def setup(bot):
    await bot.add_cog(GeneralCog(bot))
