# cogs/events.py
"""Events management cog for clan events"""

import discord
from discord.ext import commands
from discord import ui
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Any

from config_utils import Colors, Emojis, Config

class EventCreateModal(ui.Modal):
    def __init__(self):
        super().__init__(title="Create New Event", timeout=300)
        
        self.name_input = ui.TextInput(
            label="Event Name",
            placeholder="Enter the event name (e.g., Clan War, Raid Night)",
            max_length=100,
            required=True
        )
        
        self.description_input = ui.TextInput(
            label="Event Description",
            placeholder="Describe the event details...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=False
        )
        
        self.date_input = ui.TextInput(
            label="Event Date & Time",
            placeholder="YYYY-MM-DD HH:MM (e.g., 2024-12-25 19:00)",
            max_length=50,
            required=True
        )
        
        self.add_item(self.name_input)
        self.add_item(self.description_input)
        self.add_item(self.date_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse the date
            event_date = datetime.strptime(self.date_input.value, "%Y-%m-%d %H:%M")
            
            # Check if date is in the future
            if event_date <= datetime.now():
                await interaction.response.send_message(
                    "❌ Event date must be in the future!",
                    ephemeral=True
                )
                return
            
            # Create the event in database
            bot = interaction.client
            event_id = await bot.db.create_event(
                interaction.guild.id,
                self.name_input.value,
                self.description_input.value,
                event_date,
                interaction.user.id
            )
            
            # Create success embed
            embed = discord.Embed(
                title=f"{Emojis.EVENT} Event Created Successfully!",
                description=f"**{self.name_input.value}** has been scheduled.",
                color=Colors.SUCCESS
            )
            
            embed.add_field(
                name="📅 Date & Time",
                value=f"<t:{int(event_date.timestamp())}:F>",
                inline=False
            )
            
            if self.description_input.value:
                embed.add_field(
                    name="📝 Description",
                    value=self.description_input.value,
                    inline=False
                )
            
            embed.add_field(
                name="🆔 Event ID",
                value=f"`{event_id}`",
                inline=True
            )
            
            embed.set_footer(text=f"Created by {interaction.user.display_name}")
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format! Please use YYYY-MM-DD HH:MM (24-hour format)",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error creating event: {str(e)}",
                ephemeral=True
            )

class RSVPModal(ui.Modal):
    def __init__(self, event_id: int, event_name: str):
        super().__init__(title=f"RSVP for {event_name}", timeout=300)
        self.event_id = event_id
        
        self.notes_input = ui.TextInput(
            label="Additional Notes (Optional)",
            placeholder="Any additional information or comments...",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        
        self.add_item(self.notes_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # This will be called after the user selects their response
        pass

class RSVPView(ui.View):
    def __init__(self, event_id: int, event_name: str):
        super().__init__(timeout=None)  # Persistent view
        self.event_id = event_id
        self.event_name = event_name
    
    @ui.button(label="Yes, I'll Attend", style=discord.ButtonStyle.success, emoji=Emojis.RSVP_YES)
    async def rsvp_yes(self, interaction: discord.Interaction, button: ui.Button):
        await self.handle_rsvp(interaction, "Yes")
    
    @ui.button(label="No, Can't Attend", style=discord.ButtonStyle.danger, emoji=Emojis.RSVP_NO)
    async def rsvp_no(self, interaction: discord.Interaction, button: ui.Button):
        await self.handle_rsvp(interaction, "No")
    
    @ui.button(label="Maybe", style=discord.ButtonStyle.secondary, emoji=Emojis.RSVP_MAYBE)
    async def rsvp_maybe(self, interaction: discord.Interaction, button: ui.Button):
        await self.handle_rsvp(interaction, "Maybe")
    
    async def handle_rsvp(self, interaction: discord.Interaction, response: str):
        modal = RSVPModal(self.event_id, self.event_name)
        await interaction.response.send_modal(modal)
        
        # Wait for modal submission
        await modal.wait()
        
        # Save RSVP to database
        bot = interaction.client
        await bot.db.add_rsvp(
            interaction.guild.id,
            self.event_id,
            interaction.user.id,
            response,
            modal.notes_input.value if modal.notes_input.value else None
        )
        
        # Send confirmation
        color_map = {
            "Yes": Colors.SUCCESS,
            "No": Colors.ERROR,
            "Maybe": Colors.WARNING
        }
        
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} RSVP Recorded!",
            description=f"Your response for **{self.event_name}** has been recorded as: **{response}**",
            color=color_map[response]
        )
        
        if modal.notes_input.value:
            embed.add_field(name="Your Notes", value=modal.notes_input.value, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class EventManagementView(ui.View):
    def __init__(self, event_data: dict):
        super().__init__(timeout=300)
        self.event_data = event_data
    
    @ui.button(label="Send RSVP", style=discord.ButtonStyle.primary, emoji=Emojis.EVENT)
    async def send_rsvp(self, interaction: discord.Interaction, button: ui.Button):
        # Check if user has officer permissions
        if not any(role.name.lower() in ['officer', 'leader', 'admin'] for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Only officers can send RSVP requests!",
                ephemeral=True
            )
            return
        
        # Get all current members
        bot = interaction.client
        members = await bot.db.get_all_members(interaction.guild.id, "current")
        
        if not members:
            await interaction.response.send_message(
                "❌ No current members found to send RSVPs to!",
                ephemeral=True
            )
            return
        
        # Create RSVP embed
        rsvp_embed = discord.Embed(
            title=f"{Emojis.EVENT} RSVP Request",
            description=f"You've been invited to participate in **{self.event_data['name']}**",
            color=Colors.get_gradient_color()
        )
        
        event_date = self.event_data['event_date']
        rsvp_embed.add_field(
            name="📅 Event Date",
            value=f"<t:{int(event_date.timestamp())}:F>",
            inline=False
        )
        
        if self.event_data['description']:
            rsvp_embed.add_field(
                name="📝 Description",
                value=self.event_data['description'],
                inline=False
            )
        
        rsvp_embed.set_footer(text="Please respond by clicking one of the buttons below")
        
        # Create RSVP view
        rsvp_view = RSVPView(self.event_data['event_id'], self.event_data['name'])
        
        # Send DMs to all members
        sent_count = 0
        failed_count = 0
        
        for member_data in members:
            try:
                user = interaction.guild.get_member(member_data['user_id'])
                if user:
                    await user.send(embed=rsvp_embed, view=rsvp_view)
                    sent_count += 1
                    await asyncio.sleep(0.5)  # Rate limiting
            except discord.Forbidden:
                failed_count += 1
            except Exception:
                failed_count += 1
        
        # Send confirmation
        confirm_embed = discord.Embed(
            title=f"{Emojis.CONFIRM} RSVP Requests Sent!",
            description=f"Successfully sent RSVP requests to **{sent_count}** members.",
            color=Colors.SUCCESS
        )
        
        if failed_count > 0:
            confirm_embed.add_field(
                name="⚠️ Failed to Send",
                value=f"{failed_count} members couldn't be reached (DMs disabled)",
                inline=False
            )
        
        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
    
    @ui.button(label="View RSVPs", style=discord.ButtonStyle.secondary, emoji="📊")
    async def view_rsvps(self, interaction: discord.Interaction, button: ui.Button):
        # Check permissions
        if not any(role.name.lower() in ['officer', 'leader', 'admin'] for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Only officers can view RSVP responses!",
                ephemeral=True
            )
            return
        
        bot = interaction.client
        rsvps = await bot.db.get_event_rsvps(interaction.guild.id, self.event_data['event_id'])
        
        if not rsvps:
            await interaction.response.send_message(
                "📭 No RSVP responses yet for this event.",
                ephemeral=True
            )
            return
        
        # Create RSVP summary embed
        embed = discord.Embed(
            title=f"📊 RSVP Summary: {self.event_data['name']}",
            color=Colors.get_gradient_color()
        )
        
        # Count responses
        yes_count = len([r for r in rsvps if r['response'] == 'Yes'])
        no_count = len([r for r in rsvps if r['response'] == 'No'])
        maybe_count = len([r for r in rsvps if r['response'] == 'Maybe'])
        
        embed.add_field(
            name="📈 Response Summary",
            value=f"{Emojis.RSVP_YES} **Yes:** {yes_count}\n{Emojis.RSVP_NO} **No:** {no_count}\n{Emojis.RSVP_MAYBE} **Maybe:** {maybe_count}",
            inline=False
        )
        
        # List responses by category
        for response_type in ['Yes', 'No', 'Maybe']:
            responses = [r for r in rsvps if r['response'] == response_type]
            if responses:
                user_list = []
                for rsvp in responses[:10]:  # Limit to 10 per category
                    user_list.append(f"• {rsvp['username']}")
                
                if len(responses) > 10:
                    user_list.append(f"• ... and {len(responses) - 10} more")
                
                if user_list:
                    embed.add_field(
                        name=f"{response_type} ({len(responses)})",
                        value="\n".join(user_list),
                        inline=True
                    )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Events(bot))

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_group(name="event", description="Event management commands")
    async def event(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="📅 Event Management",
                description="Available event commands:",
                color=Colors.INFO
            )
            
            embed.add_field(
                name="📝 `/event create`",
                value="Create a new event",
                inline=False
            )
            
            embed.add_field(
                name="📋 `/event list`",
                value="List upcoming events",
                inline=False
            )
            
            embed.add_field(
                name="👁️ `/event view <event_id>`",
                value="View event details",
                inline=False
            )
            
            embed.add_field(
                name="✏️ `/event edit <event_id>`",
                value="Edit an event (officers only)",
                inline=False
            )
            
            embed.add_field(
                name="🗑️ `/event delete <event_id>`",
                value="Delete an event (officers only)",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    @event.command(name="create", description="Create a new event")
    async def event_create(self, ctx):
        """Create a new event"""
        # Check permissions
        if not any(role.name.lower() in ['officer', 'leader', 'admin'] for role in ctx.author.roles):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only officers can create events!",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        modal = EventCreateModal()
        await ctx.interaction.response.send_modal(modal)
    
    @event.command(name="list", description="List upcoming events")
    async def event_list(self, ctx, days: int = 30):
        # List upcoming events
        events = await self.bot.db.get_upcoming_events(ctx.guild.id, days)
        
        if not events:
            embed = discord.Embed(
                title="📭 No Upcoming Events",
                description=f"No events scheduled in the next {days} days.",
                color=Colors.INFO
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"📅 Upcoming Events (Next {days} Days)",
            color=Colors.get_gradient_color()
        )
        
        for event in events:
            embed.add_field(
                name=f"{event['name']} (ID: {event['event_id']})",
                value=f"<t:{int(event['event_date'].timestamp())}:F>",
                inline=False
            )
        
        await ctx.send(embed=embed)
        