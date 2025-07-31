import discord
from discord.ext import commands
from discord import ui

class HelpMenu(ui.View):
    def __init__(self, bot, ctx, commands_by_category):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.commands_by_category = commands_by_category
        self.categories = list(commands_by_category.keys())
        self.current_page = 0
        self.message = None
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if len(self.categories) > 1:
            if self.current_page > 0:
                self.add_item(self.PrevButton(self))
            if self.current_page < len(self.categories) - 1:
                self.add_item(self.NextButton(self))

    class PrevButton(ui.Button):
        def __init__(self, parent):
            super().__init__(label="Previous", style=discord.ButtonStyle.secondary)
            self.parent = parent

        async def callback(self, interaction: discord.Interaction):
            self.parent.current_page -= 1
            await self.parent.update_message(interaction)

    class NextButton(ui.Button):
        def __init__(self, parent):
            super().__init__(label="Next", style=discord.ButtonStyle.secondary)
            self.parent = parent

        async def callback(self, interaction: discord.Interaction):
            self.parent.current_page += 1
            await self.parent.update_message(interaction)

    async def update_message(self, interaction: discord.Interaction):
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self):
        category = self.categories[self.current_page]
        commands = self.commands_by_category[category]

        embed = discord.Embed(
            title=f"Help - {category} Commands",
            description=f"List of {category.lower()} commands",
            color=discord.Color.blue()
        )

        for cmd in commands:
            embed.add_field(name=f"/{cmd.name}", value=cmd.description or "No description", inline=False)

        embed.set_footer(text=f"Page {self.current_page + 1} of {len(self.categories)}")
        return embed

class HelpSystemCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Show the help menu with command categories")
    async def help(self, ctx):
        """Show the help menu with categorized commands and pagination"""
        # Categorize commands
        commands_by_category = {
            "Member": [],
            "Officer": [],
            "Utility": []
        }

        for command in self.bot.commands:
            # Skip hidden commands
            if command.hidden:
                continue

            # Determine category based on command name or custom attribute
            # For this example, we use command name prefixes or check for a custom attribute
            name = command.name.lower()
            if name in ["mark_attendance", "create_vote"]:
                commands_by_category["Officer"].append(command)
            elif name in ["ping"]:
                commands_by_category["Utility"].append(command)
            else:
                commands_by_category["Member"].append(command)

        view = HelpMenu(self.bot, ctx, commands_by_category)
        embed = view.create_embed()
        message = await ctx.send(embed=embed, view=view)
        view.message = message

async def setup(bot):
    await bot.add_cog(HelpSystemCog(bot))
