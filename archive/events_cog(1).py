# cogs/events.py
"""Events management cog for clan events"""

import discord
from discord.ext import commands
from discord import ui
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Any

from utils.colors import Colors
from utils.emojis import Emojis
from utils.config import Config

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
        """List upcoming events"""
        events = await self.bot.db.get_upcoming_events(ctx.guild.id, days)
        
        if not events:
            embed = discord.Embed(
                title="📅 No Upcoming Events",
                description=f"No events scheduled for the next {days} days.",
                color=Colors.INFO
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"📅 Upcoming Events ({len(events)})",
            description=f"Events in the next {days} days:",
            color=Colors.get_gradient_color()
        )
        
        for event in events[:10]:  # Limit to 10 events
            event_date = event['event_date']
            time_until = event_date - datetime.now()
            
            if time_until.days > 0:
                time_str = f"in {time_until.days} days"
            elif time_until.seconds > 3600:
                hours = time_until.seconds // 3600
                time_str = f"in {hours} hours"
            else:
                time_str = "soon"
            
            embed.add_field(
                name=f"{Emojis.EVENT} {event['name']}",
                value=f"**ID:** `{event['event_id']}`\n**Date:** <t:{int(event_date.timestamp())}:R> ({time_str})",
                inline=True
            )
        
        if len(events) > 10:
            embed.set_footer(text=f"... and {len(events) - 10} more events")
        
        await ctx.send(embed=embed)
    
    @event.command(name="view", description="View event details")
    async def event_view(self, ctx, event_id: int):
        """View detailed information about an event"""
        event_data = await self.bot.db.get_event(ctx.guild.id, event_id)
        
        if not event_data:
            embed = discord.Embed(
                title="❌ Event Not Found",
                description=f"No event found with ID `{event_id}`",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Create detailed event embed
        embed = discord.Embed(
            title=f"{Emojis.EVENT} {event_data['name']}",
            color=Colors.get_random_primary()
        )
        
        # Event details
        event_date = event_data['event_date']
        embed.add_field(
            name="📅 Date & Time",
            value=f"<t:{int(event_date.timestamp())}:F>\n<t:{int(event_date.timestamp())}:R>",
            inline=False
        )
        
        if event_data['description']:
            embed.add_field(
                name="📝 Description",
                value=event_data['description'],
                inline=False
            )
        
        # Creator info
        creator = ctx.guild.get_member(event_data['created_by'])
        creator_name = creator.display_name if creator else "Unknown"
        
        embed.add_field(
            name="👤 Created By",
            value=creator_name,
            inline=True
        )
        
        embed.add_field(
            name="🆔 Event ID",
            value=f"`{event_id}`",
            inline=True
        )
        
        # Get RSVP summary
        rsvps = await self.bot.db.get_event_rsvps(ctx.guild.id, event_id)
        if rsvps:
            yes_count = len([r for r in rsvps if r['response'] == 'Yes'])
            no_count = len([r for r in rsvps if r['response'] == 'No'])
            maybe_count = len([r for r in rsvps if r['response'] == 'Maybe'])
            
            embed.add_field(
                name="📊 RSVP Status",
                value=f"{Emojis.RSVP_YES} {yes_count} • {Emojis.RSVP_NO} {no_count} • {Emojis.RSVP_MAYBE} {maybe_count}",
                inline=False
            )
        
        embed.set_footer(text=f"Created on {event_data['created_at'].strftime('%B %d, %Y')}")
        
        # Add management view for officers
        view = None
        if any(role.name.lower() in ['officer', 'leader', 'admin'] for role in ctx.author.roles):
            view = EventManagementView(dict(event_data))
        
        await ctx.send(embed=embed, view=view)
    
    @event.command(name="edit", description="Edit an event")
    async def event_edit(self, ctx, event_id: int):
        """Edit an existing event"""
        # Check permissions
        if not any(role.name.lower() in ['officer', 'leader', 'admin'] for role in ctx.author.roles):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only officers can edit events!",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Check if event exists
        event_data = await self.bot.db.get_event(ctx.guild.id, event_id)
        if not event_data:
            embed = discord.Embed(
                title="❌ Event Not Found",
                description=f"No event found with ID `{event_id}`",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Create edit modal with current values
        modal = EventEditModal(event_data)
        await ctx.interaction.response.send_modal(modal)
    
    @event.command(name="delete", description="Delete an event")
    async def event_delete(self, ctx, event_id: int):
        """Delete an event"""
        # Check permissions
        if not any(role.name.lower() in ['officer', 'leader', 'admin'] for role in ctx.author.roles):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only officers can delete events!",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Check if event exists
        event_data = await self.bot.db.get_event(ctx.guild.id, event_id)
        if not event_data:
            embed = discord.Embed(
                title="❌ Event Not Found",
                description=f"No event found with ID `{event_id}`",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Create confirmation view
        view = EventDeleteConfirmView(event_id, event_data['name'])
        
        embed = discord.Embed(
            title="⚠️ Confirm Event Deletion",
            description=f"Are you sure you want to delete the event **{event_data['name']}**?",
            color=Colors.WARNING
        )
        
        embed.add_field(
            name="📅 Event Date",
            value=f"<t:{int(event_data['event_date'].timestamp())}:F>",
            inline=False
        )
        
        embed.set_footer(text="This action cannot be undone!")
        
        await ctx.send(embed=embed, view=view, ephemeral=True)

class EventEditModal(ui.Modal):
    def __init__(self, event_data):
        super().__init__(title="Edit Event", timeout=300)
        self.event_id = event_data['event_id']
        
        self.name_input = ui.TextInput(
            label="Event Name",
            default=event_data['name'],
            max_length=100,
            required=True
        )
        
        self.description_input = ui.TextInput(
            label="Event Description",
            default=event_data['description'] or "",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=False
        )
        
        # Format current date for display
        current_date = event_data['event_date'].strftime("%Y-%m-%d %H:%M")
        self.date_input = ui.TextInput(
            label="Event Date & Time",
            default=current_date,
            placeholder="YYYY-MM-DD HH:MM",
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
            
            # Update the event in database
            bot = interaction.client
            schema_name = f"guild_{interaction.guild.id}"
            
            async with bot.db.pool.acquire() as conn:
                await conn.execute(f"""
                    UPDATE {schema_name}.events
                    SET name = $1, description = $2, event_date = $3
                    WHERE event_id = $4
                """, self.name_input.value, self.description_input.value, event_date, self.event_id)
            
            # Create success embed
            embed = discord.Embed(
                title=f"{Emojis.CONFIRM} Event Updated!",
                description=f"**{self.name_input.value}** has been updated successfully.",
                color=Colors.SUCCESS
            )
            
            embed.add_field(
                name="📅 New Date & Time",
                value=f"<t:{int(event_date.timestamp())}:F>",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format! Please use YYYY-MM-DD HH:MM (24-hour format)",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error updating event: {str(e)}",
                ephemeral=True
            )

class EventDeleteConfirmView(ui.View):
    def __init__(self, event_id: int, event_name: str):
        super().__init__(timeout=60)
        self.event_id = event_id
        self.event_name = event_name
    
    @ui.button(label="Yes, Delete", style=discord.ButtonStyle.danger, emoji=Emojis.DELETE)
    async def confirm_delete(self, interaction: discord.Interaction, button: ui.Button):
        # Delete the event
        bot = interaction.client
        schema_name = f"guild_{interaction.guild.id}"
        
        async with bot.db.pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE {schema_name}.events
                SET is_active = FALSE
                WHERE event_id = $1
            """, self.event_id)
        
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} Event Deleted",
            description=f"The event **{self.event_name}** has been deleted.",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()
    
    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji=Emojis.CANCEL)
    async def cancel_delete(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="❌ Deletion Cancelled",
            description="The event was not deleted.",
            color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()

async def setup(bot):
    await bot.add_cog(Events(bot))
        