# cogs/member_stats.py
"""Member stats management cog"""

import discord
from discord.ext import commands
from discord import ui
from typing import Dict, Any, Optional
import asyncio

from config_utils import Colors, Emojis, Config

class StatsModal(ui.Modal):
    def __init__(self, category: str, current_stats: Dict[str, Any] = None):
        super().__init__(title=f"Edit {category.title()} Stats", timeout=300)
        self.category = category
        self.current_stats = current_stats or {}
        
        # Define stat fields for each category
        self.stat_fields = {
            "basic": {
                "discord_id": "Discord ID",
                "character_name": "Character Name",
                "character_class": "Class",
                "shadow_rank": "Shadow Rank",
                "clan_role": "Clan Role"
            },
            "combat": {
                "combat_rating": "Combat Rating",
                "resonance": "Resonance",
                "paragon_level": "Paragon Level",
                "damage": "Damage",
                "life": "Life"
            },
            "secondary": {
                "armor": "Armor",
                "armor_penetration": "Armor Penetration",
                "potency": "Potency",
                "resistance": "Resistance"
            },
            "core_attributes": {
                "strength": "Strength",
                "intelligence": "Intelligence",
                "fortitude": "Fortitude",
                "willpower": "Willpower",
                "vitality": "Vitality"
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
        if updated_stats:
            bot = interaction.client
            await bot.db.update_member_stats(interaction.guild.id, interaction.user.id, updated_stats)
            
            # Also ensure user is in members table
            await bot.db.add_member(interaction.guild.id, interaction.user.id, interaction.user.display_name)
        
        # Create success embed
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} {self.category.title()} Stats Updated!",
            description=f"Successfully updated your {self.category} statistics.",
            color=Colors.SUCCESS
        )
        
        # Show updated fields
        if updated_stats:
            stats_text = ""
            for field_name, value in updated_stats.items():
                field_label = self.stat_fields[self.category][field_name]
                if isinstance(value, int):
                    stats_text += f"**{field_label}:** {value:,}\n"
                else:
                    stats_text += f"**{field_label}:** {value}\n"
            
            embed.add_field(name="Updated Fields", value=stats_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BackgroundSelectView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        
        # Create background options
        backgrounds = Config.PROFILE_BACKGROUNDS
        options = []
        
        for bg in backgrounds:
            options.append(
                discord.SelectOption(
                    label=bg.replace("_", " ").title(),
                    value=bg,
                    description=f"Set {bg.replace('_', ' ')} as your profile background"
                )
            )
        
        self.background_select = ui.Select(
            placeholder="Choose your profile background...",
            options=options
        )
        self.background_select.callback = self.background_selected
        self.add_item(self.background_select)
    
    async def background_selected(self, interaction: discord.Interaction):
        selected_bg = self.background_select.values[0]
        
        # Update background in database
        bot = interaction.client
        async with bot.db.pool.acquire() as conn:
            schema_name = f"guild_{interaction.guild.id}"
            await conn.execute(f"""
                UPDATE {schema_name}.members 
                SET profile_background = $1, last_updated = NOW()
                WHERE user_id = $2
            """, selected_bg, self.user_id)
        
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} Background Updated!",
            description=f"Your profile background has been set to **{selected_bg.replace('_', ' ').title()}**",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ProfileView(ui.View):
    def __init__(self, member_data: dict):
        super().__init__(timeout=300)
        self.member_data = member_data
        self.user_id = member_data.get('user_id')
    
    @ui.button(label="Edit Basic Stats", style=discord.ButtonStyle.primary, emoji=Emojis.EDIT)
    async def edit_basic(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can only edit your own profile!", ephemeral=True)
            return
        
        modal = StatsModal("basic", dict(self.member_data))
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Edit Combat Stats", style=discord.ButtonStyle.primary, emoji=Emojis.COMBAT_RATING)
    async def edit_combat(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can only edit your own profile!", ephemeral=True)
            return
        
        modal = StatsModal("combat", dict(self.member_data))
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Edit Secondary Stats", style=discord.ButtonStyle.primary, emoji=Emojis.DAMAGE)
    async def edit_secondary(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can only edit your own profile!", ephemeral=True)
            return
        
        modal = StatsModal("secondary", dict(self.member_data))
        await interaction.response.send_modal(modal)

    @ui.button(label="Edit Core Attributes", style=discord.ButtonStyle.primary, emoji="🧠")
    async def edit_core_attributes(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can only edit your own profile!", ephemeral=True)
            return
        
        modal = StatsModal("core_attributes", dict(self.member_data))
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Change Background", style=discord.ButtonStyle.secondary, emoji="🎨")
    async def change_background(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can only edit your own profile!", ephemeral=True)
            return
        
        view = BackgroundSelectView(self.user_id)
        embed = discord.Embed(
            title="🎨 Choose Profile Background",
            description="Select a new background for your profile:",
            color=Colors.get_gradient_color()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="View Attendance", style=discord.ButtonStyle.secondary, emoji="📊")
    async def view_attendance(self, interaction: discord.Interaction, button: ui.Button):
        bot = interaction.client
        attendance_data = await bot.db.get_member_attendance(interaction.guild.id, self.user_id)
        
        stats = attendance_data['stats']
        recent = attendance_data['recent']
        
        embed = discord.Embed(
            title=f"📊 Attendance Record",
            color=Colors.get_gradient_color()
        )
        
        # Calculate attendance percentage
        total_events = stats['total_events'] or 0
        attended_events = stats['attended_events'] or 0
        percentage = (attended_events / total_events * 100) if total_events > 0 else 0
        
        embed.add_field(
            name="📈 Overall Stats",
            value=f"**Attended:** {attended_events}/{total_events} events\n**Percentage:** {percentage:.1f}%",
            inline=False
        )
        
        # Recent events
        if recent:
            recent_text = ""
            for event in recent:
                status_emoji = "✅" if event['attended'] else "❌"
                event_date = event['event_date'].strftime("%Y-%m-%d")
                recent_text += f"{status_emoji} **{event['name']}** ({event_date})\n"
            
            embed.add_field(
                name="📅 Recent Events",
                value=recent_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📅 Recent Events",
                value="No events attended yet.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class MemberStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="profile", description="View or edit your member profile")
    async def profile(self, ctx, member: discord.Member = None):
        """View member profile with stats"""
        target_user = member or ctx.author
        
        # Get member data from database
        member_data = await self.bot.db.get_member(ctx.guild.id, target_user.id)
        
        if not member_data:
            if target_user == ctx.author:
                # Create new member entry
                await self.bot.db.add_member(ctx.guild.id, target_user.id, target_user.display_name)
                member_data = await self.bot.db.get_member(ctx.guild.id, target_user.id)
            else:
                embed = discord.Embed(
                    title="❌ Member Not Found",
                    description=f"{target_user.mention} is not registered in the clan database.",
                    color=Colors.ERROR
                )
                await ctx.send(embed=embed, ephemeral=True)
                return
        
        # Create profile embed
        embed = self.create_profile_embed(target_user, dict(member_data))
        
        # Add view for profile owner
        view = None
        if target_user == ctx.author:
            view = ProfileView(dict(member_data))
        
        await ctx.send(embed=embed, view=view)

    def create_profile_embed(self, user: discord.Member, member_data: dict) -> discord.Embed:
        """Create profile embed with member stats"""
        # Get background-based color and image URL
        background = member_data.get('profile_background', 'hellforge')
        background_colors = {
            'hellforge': Colors.BLOOD_RED,
            'sanctuary': Colors.GOLD,
            'westmarch': Colors.IMMORTAL_BLUE,
            'library': Colors.SHADOW_PURPLE,
            'cathedral': Colors.CELESTIAL_WHITE,
            'demon_hunter': Colors.EMERALD,
            'barbarian': Colors.CRIMSON,
            'wizard': Colors.SAPPHIRE,
            'monk': Colors.TOPAZ,
            'necromancer': Colors.VOID_BLACK,
            'crusader': Colors.AMETHYST
        }
        
        color = background_colors.get(background, Colors.get_random_primary())
        
        embed = discord.Embed(
            title=f"👤 {user.display_name}'s Profile",
            color=color
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Set image for profile background if available
        from utils.config import Config
        bg_images = Config.PROFILE_BACKGROUNDS
        bg_image_url = bg_images.get(background)
        if bg_image_url:
            embed.set_image(url=bg_image_url)
        
        # Status and basic info
        status_emoji = {
            'Leader': Emojis.LEADER,
            'Officer': Emojis.OFFICER,
            'Member': Emojis.MEMBER,
            'Alumni': Emojis.ALUMNI
        }.get(member_data.get('status', 'Member'), Emojis.MEMBER)
        
        embed.add_field(
            name="🏷️ Clan Status",
            value=f"{status_emoji} {member_data.get('status', 'Member')}",
            inline=True
        )
        
        join_date = member_data.get('join_date')
        if join_date:
            embed.add_field(
                name="📅 Joined",
                value=f"<t:{int(join_date.timestamp())}:D>",
                inline=True
            )
        
        embed.add_field(
            name="🎨 Background",
            value=background.replace('_', ' ').title(),
            inline=True
        )
        
        # Basic Stats
        basic_stats = []
        if member_data.get('character_name'):
            basic_stats.append(f"**Character:** {member_data['character_name']}")
        if member_data.get('character_class'):
            class_emoji = getattr(Emojis, member_data['character_class'].upper(), "🛡️")
            basic_stats.append(f"**Class:** {class_emoji} {member_data['character_class']}")
        if member_data.get('server_name'):
            basic_stats.append(f"**Server:** {member_data['server_name']}")
        
        if basic_stats:
            embed.add_field(
                name="ℹ️ Basic Info",
                value="\n".join(basic_stats),
                inline=False
            )
        
        # Combat Stats
        combat_stats = []
        if member_data.get('combat_rating'):
            combat_stats.append(f"{Emojis.COMBAT_RATING} **Combat Rating:** {member_data['combat_rating']:,}")
        if member_data.get('resonance'):
            combat_stats.append(f"{Emojis.RESONANCE} **Resonance:** {member_data['resonance']:,}")
        if member_data.get('paragon_level'):
            combat_stats.append(f"{Emojis.PARAGON} **Paragon:** {member_data['paragon_level']:,}")
        if member_data.get('server_rank'):
            combat_stats.append(f"{Emojis.RANK} **Server Rank:** #{member_data['server_rank']:,}")
        if member_data.get('kills'):
            combat_stats.append(f"{Emojis.KILLS} **Kills:** {member_data['kills']:,}")
        
        if combat_stats:
            embed.add_field(
                name="⚔️ Combat Stats",
                value="\n".join(combat_stats),
                inline=True
            )
        
        # Secondary Stats
        secondary_stats = []
        if member_data.get('immortal_rank'):
            secondary_stats.append(f"👑 **Immortal:** {member_data['immortal_rank']}")
        if member_data.get('shadow_rank'):
            secondary_stats.append(f"🌙 **Shadow:** {member_data['shadow_rank']}")
        if member_data.get('clan_contribution'):
            secondary_stats.append(f"🏛️ **Contribution:** {member_data['clan_contribution']:,}")
        
        if secondary_stats:
            embed.add_field(
                name="🎖️ Secondary Stats",
                value="\n".join(secondary_stats),
                inline=True
            )
        
        # Secondary
        secondary = []
        if member_data.get('armor'):
            secondary.append(f"{Emojis.ARMOR} **Armor:** {member_data['armor']:,}")
        if member_data.get('resistance'):
            secondary.append(f"{Emojis.RESISTANCE} **Resistance:** {member_data['resistance']:,}")
        
        if secondary:
            embed.add_field(
                name="📊 Secondary Stats",
                value="\n".join(secondary),
                inline=False
            )
        
        # Combat Stats
        combat_stats = []
        if member_data.get('combat_rating'):
            combat_stats.append(f"{Emojis.COMBAT_RATING} **Combat Rating:** {member_data['combat_rating']:,}")
        if member_data.get('resonance'):
            combat_stats.append(f"{Emojis.RESONANCE} **Resonance:** {member_data['resonance']:,}")
        if member_data.get('paragon_level'):
            combat_stats.append(f"{Emojis.PARAGON} **Paragon:** {member_data['paragon_level']:,}")
        if member_data.get('damage'):
            combat_stats.append(f"{Emojis.DAMAGE} **Damage:** {member_data['damage']:,}")
        if member_data.get('life'):
            combat_stats.append(f"{Emojis.LIFE} **Life:** {member_data['life']:,}")
        
        # Core Attributes
        core_attributes = []
        if member_data.get('strength'):
            core_attributes.append(f"🧠 **Strength:** {member_data['strength']:,}")
        if member_data.get('intelligence'):
            core_attributes.append(f"🧠 **Intelligence:** {member_data['intelligence']:,}")
        if member_data.get('fortitude'):
            core_attributes.append(f"🧠 **Fortitude:** {member_data['fortitude']:,}")
        if member_data.get('willpower'):
            core_attributes.append(f"🧠 **Willpower:** {member_data['willpower']:,}")
        if member_data.get('vitality'):
            core_attributes.append(f"🧠 **Vitality:** {member_data['vitality']:,}")
        
        if core_attributes:
            embed.add_field(
                name="🧠 Core Attributes",
                value="\n".join(core_attributes),
                inline=False
            )
        
        # Footer with last update
        last_updated = member_data.get('updated_at') or member_data.get('last_updated')
        if last_updated:
            embed.set_footer(text=f"Last updated: {last_updated.strftime('%Y-%m-%d %H:%M UTC')}")
        
        return embed

async def setup(bot):
    await bot.add_cog(MemberStats(bot))
