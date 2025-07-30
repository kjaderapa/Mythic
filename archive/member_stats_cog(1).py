# cogs/member_stats.py
"""Member stats management cog"""

import discord
from discord.ext import commands
from discord import ui
from typing import Dict, Any
import asyncio

from utils.colors import Colors
from utils.emojis import Emojis
from utils.config import Config

class StatsModal(ui.Modal):
    def __init__(self, category: str, current_stats: Dict[str, Any] = None):
        super().__init__(title=f"Edit {category.title()} Stats", timeout=300)
        self.category = category
        self.current_stats = current_stats or {}
        
        # Define stat fields for each category
        self.stat_fields = {
            "basic": {
                "character_name": "Character Name",
                "character_class": "Class",
                "server_name": "Server Name"
            },
            "combat": {
                "combat_rating": "Combat Rating",
                "resonance": "Resonance",
                "paragon_level": "Paragon Level",
                "server_rank": "Server Rank",
                "kills": "Kills"
            },
            "secondary": {
                "immortal_rank": "Immortal Rank",
                "shadow_rank": "Shadow Rank",
                "clan_contribution": "Clan Contribution"
            },
            "attributes": {
                "damage": "Damage",
                "life": "Life",
                "armor": "Armor",
                "armor_penetration": "Armor Penetration",
                "potency": "Potency",
                "resistance": "Resistance"
            }
        }
        
        # Add input fields for this category
        for field_name, field_label in self.stat_fields[category].items():
            current_value = str(self.current_stats.get(field_name, "")) if self.current_stats.get(field_name) else ""
            
            self.add_item(ui.TextInput(
                label=field_label,
                placeholder=f"Enter your {field_label.lower()}",
                default=current_value,
                required=False,
                max_length=100
            ))
    
    async def on_submit(self, interaction: discord.Interaction):
        # Process the submitted data
        updated_stats = {}
        
        for i, (field_name, _) in enumerate(self.stat_fields[self.category].items()):
            value = self.children[i].value
            if value:
                # Try to convert to int for numeric fields
                if field_name in ["combat_rating", "resonance", "paragon_level", 
                                "server_rank", "kills", "clan_contribution", 
                                "damage", "life", "armor", "armor_penetration", 
                                "potency", "resistance"]:
                    try:
                        updated_stats[field_name] = int(value.replace(",", ""))
                    except ValueError:
                        await interaction.response.send_message(
                            f"❌ Invalid number format for {field_name}: {value}",
                            ephemeral=True
                        )
                        return
                else:
                    updated_stats[field_name] = value
        
        # Update database
        bot = interaction.client
        await bot.db.update_member_stats(interaction.guild.id, interaction.user.id, updated_stats)
        
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} Stats Updated!",
            description=f"Your {self.category} stats have been successfully updated.",
            color=Colors.SUCCESS
        )
        


class BackgroundSelectView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        
    @ui.select(
        placeholder="Choose your profile background...",
        options=[
            discord.SelectOption(label="Hellforge", value="hellforge", emoji="🔥"),
            discord.SelectOption(label="Sanctuary", value="sanctuary", emoji="🏛️"),
            discord.SelectOption(label="Westmarch", value="westmarch", emoji="🏰"),
            discord.SelectOption(label="Library", value="library", emoji="📚"),
            discord.SelectOption(label="Cathedral", value="cathedral", emoji="⛪"),
            discord.SelectOption(label="Demon Hunter", value="demon_hunter", emoji="🏹"),
            discord.SelectOption(label="Barbarian", value="barbarian", emoji="🪓"),
            discord.SelectOption(label="Wizard", value="wizard", emoji="🔮"),
            discord.SelectOption(label="Monk", value="monk", emoji="👊"),
            discord.SelectOption(label="Necromancer", value="necromancer", emoji="💀"),
            discord.SelectOption(label="Crusader", value="crusader", emoji="🛡️")
        ]
    )
    async def background_select(self, interaction: discord.Interaction, select: ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can only change your own background!", ephemeral=True)
            return
            
        # Update database with new background
        bot = interaction.client
        async with bot.db.pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE guild_{interaction.guild.id}.members 
                SET profile_background = $1, last_updated = NOW()
                WHERE user_id = $2
            """, select.values[0], interaction.user.id)
        
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} Background Updated!",
            description=f"Your profile background has been changed to **{select.values[0].replace('_', ' ').title()}**",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()


class ProfileView(ui.View):
    def __init__(self, member_data: dict, user_id: int):
        super().__init__(timeout=300)
        self.member_data = member_data
        self.user_id = user_id
        
    @ui.button(label="Edit Basic", style=discord.ButtonStyle.primary, emoji=Emojis.EDIT)
    async def edit_basic(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can only edit your own stats!", ephemeral=True)
            return
            
        modal = StatsModal("basic", self.member_data)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Edit Combat", style=discord.ButtonStyle.primary, emoji=Emojis.COMBAT_RATING)
    async def edit_combat(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can only edit your own stats!", ephemeral=True)
            return
            
        modal = StatsModal("combat", self.member_data)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Edit Secondary", style=discord.ButtonStyle.primary, emoji=Emojis.RANK)
    async def edit_secondary(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can only edit your own stats!", ephemeral=True)
            return
            
        modal = StatsModal("secondary", self.member_data)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Edit Attributes", style=discord.ButtonStyle.primary, emoji=Emojis.DAMAGE)
    async def edit_attributes(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can only edit your own stats!", ephemeral=True)
            return
            
        modal = StatsModal("attributes", self.member_data)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Change Background", style=discord.ButtonStyle.secondary, emoji="🎨")
    async def change_background(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can only change your own background!", ephemeral=True)
            return
            
        view = BackgroundSelectView(self.user_id)
        embed = discord.Embed(
            title="Choose Profile Background",
            description="Select a background theme for your profile:",
            color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class MemberStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def format_stat_value(self, value, is_numeric=True):
        """Format stat values for display"""
        if value is None:
            return "Not Set"
        if is_numeric and isinstance(value, int):
            return f"{value:,}"
        return str(value)
    
    def create_profile_embed(self, member_data: dict, user: discord.Member):
        """Create a beautiful profile embed"""
        # Choose color based on class or default
        class_colors = {
            "Barbarian": Colors.BLOOD_RED,
            "Crusader": Colors.GOLD,
            "Demon Hunter": Colors.EMERALD,
            "Monk": Colors.EMBER_ORANGE,
            "Necromancer": Colors.SHADOW_PURPLE,
            "Wizard": Colors.IMMORTAL_BLUE
        }
        
        character_class = member_data.get('character_class', '')
        embed_color = class_colors.get(character_class, Colors.get_random_primary())
        
        embed = discord.Embed(
            title=f"{Emojis.MEMBER} {user.display_name}'s Profile",
            color=embed_color
        )
        
        # Set thumbnail to user avatar
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Basic Info
        character_name = member_data.get('character_name') or 'Not Set'
        server_name = member_data.get('server_name') or 'Not Set'
        status = member_data.get('status', 'Member')
        
        basic_info = f"""
        **Character:** {character_name}
        **Class:** {character_class or 'Not Set'} {self.get_class_emoji(character_class)}
        **Server:** {server_name}
        **Status:** {status} {self.get_status_emoji(status)}
        """
        embed.add_field(name="📋 Basic Information", value=basic_info, inline=False)
        
        # Combat Stats
        combat_rating = self.format_stat_value(member_data.get('combat_rating'))
        resonance = self.format_stat_value(member_data.get('resonance'))
        paragon = self.format_stat_value(member_data.get('paragon_level'))
        server_rank = self.format_stat_value(member_data.get('server_rank'))
        kills = self.format_stat_value(member_data.get('kills'))
        
        combat_stats = f"""
        {Emojis.COMBAT_RATING} **Combat Rating:** {combat_rating}
        {Emojis.RESONANCE} **Resonance:** {resonance}
        {Emojis.PARAGON} **Paragon Level:** {paragon}
        {Emojis.RANK} **Server Rank:** {server_rank}
        {Emojis.KILLS} **Kills:** {kills}
        """
        embed.add_field(name="⚔️ Combat Stats", value=combat_stats, inline=True)
        
        # Attributes
        damage = self.format_stat_value(member_data.get('damage'))
        life = self.format_stat_value(member_data.get('life'))
        armor = self.format_stat_value(member_data.get('armor'))
        resistance = self.format_stat_value(member_data.get('resistance'))
        
        attributes = f"""
        {Emojis.DAMAGE} **Damage:** {damage}
        {Emojis.LIFE} **Life:** {life}
        {Emojis.ARMOR} **Armor:** {armor}
        {Emojis.RESISTANCE} **Resistance:** {resistance}
        """
        embed.add_field(name="📊 Attributes", value=attributes, inline=True)
        
        # Secondary Stats
        immortal_rank = member_data.get('immortal_rank') or 'Not Set'
        shadow_rank = member_data.get('shadow_rank') or 'Not Set'
        contribution = self.format_stat_value(member_data.get('clan_contribution'))
        
        secondary = f"""
        👑 **Immortal Rank:** {immortal_rank}
        🌙 **Shadow Rank:** {shadow_rank}
        🏛️ **Clan Contribution:** {contribution}
        """
        embed.add_field(name="🎖️ Secondary Stats", value=secondary, inline=False)
        
        # Attendance (if available)
        # This will be implemented when we add the attendance system
        
        # Footer
        join_date = member_data.get('join_date')
        if join_date:
            embed.set_footer(text=f"Member since {join_date.strftime('%B %d, %Y')}")
        
        return embed
    
    def get_class_emoji(self, character_class):
        """Get emoji for character class"""
        class_emojis = {
            "Barbarian": Emojis.BARBARIAN,
            "Crusader": Emojis.CRUSADER,
            "Demon Hunter": Emojis.DEMON_HUNTER,
            "Monk": Emojis.MONK,
            "Necromancer": Emojis.NECROMANCER,
            "Wizard": Emojis.WIZARD
        }
        return class_emojis.get(character_class, "")
    
    def get_status_emoji(self, status):
        """Get emoji for member status"""
        status_emojis = {
            "Member": Emojis.MEMBER,
            "Officer": Emojis.OFFICER,
            "Alumni": Emojis.ALUMNI,
            "Leader": Emojis.LEADER
        }
        return status_emojis.get(status, Emojis.MEMBER)
    
    @commands.hybrid_command(name="profile", description="View a member's profile")
    async def profile(self, ctx, member: discord.Member = None):
        """Display member profile with stats"""
        target_member = member or ctx.author
        
        # Get member data from database
        member_data = await self.bot.db.get_member(ctx.guild.id, target_member.id)
        
        if not member_data:
            # If member doesn't exist, create them
            await self.bot.db.add_member(ctx.guild.id, target_member.id, target_member.display_name)
            member_data = await self.bot.db.get_member(ctx.guild.id, target_member.id)
        
        # Create profile embed
        embed = self.create_profile_embed(dict(member_data), target_member)
        
        # Create view with edit buttons (only for own profile)
        view = None
        if target_member.id == ctx.author.id:
            view = ProfileView(dict(member_data), target_member.id)
        
        await ctx.send(embed=embed, view=view)
    
    @commands.hybrid_command(name="register", description="Register as a clan member")
    async def register(self, ctx):
        """Register as a clan member"""
        # Check if already registered
        member_data = await self.bot.db.get_member(ctx.guild.id, ctx.author.id)
        
        if member_data:
            embed = discord.Embed(
                title=f"{Emojis.CONFIRM} Already Registered!",
                description="You are already registered as a clan member. Use `/profile` to view and edit your stats.",
                color=Colors.INFO
            )
        else:
            # Register new member
            await self.bot.db.add_member(ctx.guild.id, ctx.author.id, ctx.author.display_name)
            
            embed = discord.Embed(
                title=f"{Emojis.CONFIRM} Registration Complete!",
                description=f"Welcome to the clan, {ctx.author.mention}! You can now use `/profile` to view and edit your stats.",
                color=Colors.SUCCESS
            )
            embed.add_field(
                name="Next Steps",
                value="• Use `/profile` to view your profile\n• Click the edit buttons to add your stats\n• Choose a background theme for your profile",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="setstats", description="Quick command to set multiple stats")
    async def setstats(self, ctx):
        """Open stats editing interface"""
        # Check if member is registered
        member_data = await self.bot.db.get_member(ctx.guild.id, ctx.author.id)
        
        if not member_data:
            await self.bot.db.add_member(ctx.guild.id, ctx.author.id, ctx.author.display_name)
            member_data = {}
        
        embed = discord.Embed(
            title="📊 Edit Your Stats",
            description="Choose which category of stats you'd like to edit:",
            color=Colors.get_gradient_color()
        )
        
        embed.add_field(
            name="📋 Basic Stats",
            value="Character name, class, server",
            inline=True
        )
        
        embed.add_field(
            name="⚔️ Combat Stats", 
            value="Combat rating, resonance, paragon level",
            inline=True
        )
        
        embed.add_field(
            name="🎖️ Secondary Stats",
            value="Immortal rank, shadow rank, contribution",
            inline=True
        )
        
        embed.add_field(
            name="📊 Attributes",
            value="Damage, life, armor, resistance",
            inline=True
        )
        
        view = ProfileView(dict(member_data) if member_data else {}, ctx.author.id)
        await ctx.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MemberStats(bot))