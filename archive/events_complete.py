# cogs/events.py
"""Events management cog for clan events"""

import discord
from discord.ext import commands
from discord import ui
from datetime import datetime, timedelta
import asyncio
import json
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
    def __init__(self, event_id: int, event_name: str, response: str):
        super().__init__(title=f"RSVP for {event_name}", timeout=300)
        self.event_id = event_id
        self.response = response
        
        self.notes_input = ui.TextInput(
            label="Additional Notes (Optional)",
            placeholder="Any additional information or comments...",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        
        self.add_item(self.notes_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Save RSVP to database
        bot = interaction.client
        await bot.db.add_rsvp(
            interaction.guild.id,
            self.event_id,
            interaction.user.id,
            self.response,
            self.notes_input.value if self.notes_input.value else None
        )
        
        # Send confirmation
        color_map = {
            "Yes": Colors.SUCCESS,
            "No": Colors.ERROR,
            "Maybe": Colors.WARNING
        }
        
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} RSVP Recorded!",
            description=f"Your response has been recorded as: **{self.response}**",
            color=color_map[self.response]
        )
        
        if self.notes_input.value:
            embed.add_field(name="Your Notes", value=self.notes_input.value, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RSVPView(ui.View):
    def __init__(self, event_id: int, event_name: str):
        super().__init__(timeout=None)  # Persistent view
        self.event_id = event_id
        self.event_name = event_name
    
    @ui.button(label="Yes, I'll Attend", style=discord.ButtonStyle.success, emoji=Emojis.RSVP_YES)
    async def rsvp_yes(self, interaction: discord.Interaction, button: ui.Button):
        modal = RSVPModal(self.event_id, self.event_name, "Yes")
        await interaction.response.send_modal(modal)
    
    @ui.button(label="No, Can't Attend", style=discord.ButtonStyle.danger, emoji=Emojis.RSVP_NO)
    async def rsvp_no(self, interaction: discord.Interaction, button: ui.Button):
        modal = RSVPModal(self.event_id, self.event_name, "No")
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Maybe", style=discord.ButtonStyle.secondary, emoji=Emojis.RSVP_MAYBE)
    async def rsvp_maybe(self, interaction: discord.Interaction, button: ui.Button):
        modal = RSVPModal(self.event_id, self.event_name, "Maybe")
        await interaction.response.send_modal(modal)

class RosterCreateModal(ui.Modal):
    def __init__(self, event_id: int, event_name: str, rsvp_data: List[dict]):
        super().__init__(title="Create Custom Roster", timeout=300)
        self.event_id = event_id
        self.event_name = event_name
        self.rsvp_data = rsvp_data
        
        self.roster_name_input = ui.TextInput(
            label="Roster Name",
            placeholder="Enter roster name...",
            max_length=100,
            required=True
        )
        
        self.rooms_input = ui.TextInput(
            label="Number of Rooms",
            placeholder="How many rooms? (e.g., 4)",
            max_length=2,
            required=True
        )
        
        self.members_per_room_input = ui.TextInput(
            label="Members per Room",
            placeholder="How many members per room? (e.g., 8)",
            max_length=3,
            required=True
        )
        
        self.add_item(self.roster_name_input)
        self.add_item(self.rooms_input)
        self.add_item(self.members_per_room_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            num_rooms = int(self.rooms_input.value)
            members_per_room = int(self.members_per_room_input.value)
            
            if num_rooms <= 0 or members_per_room <= 0:
                await interaction.response.send_message("❌ Numbers must be positive!", ephemeral=True)
                return
            
            if num_rooms > 20 or members_per_room > 50:
                await interaction.response.send_message("❌ Numbers too large!", ephemeral=True)
                return
            
            # Get Yes RSVPs
            yes_rsvps = [r for r in self.rsvp_data if r['response'] == 'Yes']
            
            if len(yes_rsvps) < num_rooms * members_per_room:
                embed = discord.Embed(
                    title="⚠️ Insufficient RSVPs",
                    description=f"You need {num_rooms * members_per_room} confirmed attendees but only have {len(yes_rsvps)}.",
                    color=Colors.WARNING
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Create roster data
            roster_data = {"rooms": [], "total_rooms": num_rooms, "members_per_room": members_per_room}
            
            for room_num in range(1, num_rooms + 1):
                start_idx = (room_num - 1) * members_per_room
                end_idx = start_idx + members_per_room
                room_members = yes_rsvps[start_idx:end_idx]
                
                roster_data["rooms"].append({
                    "room_number": room_num,
                    "members": [{"username": m['username'], "user_id": m['user_id']} for m in room_members]
                })
            
            # Save to database
            bot = interaction.client
            async with bot.db.pool.acquire() as conn:
                schema_name = f"guild_{interaction.guild.id}"
                await conn.execute(f"""
                    INSERT INTO {schema_name}.rosters (event_id, roster_name, roster_data, created_by)
                    VALUES ($1, $2, $3, $4)
                """, self.event_id, self.roster_name_input.value, json.dumps(roster_data), interaction.user.id)
            
            # Create roster embed
            embed = await self.create_roster_embed(roster_data, self.roster_name_input.value)
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Please enter valid numbers!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating roster: {str(e)}", ephemeral=True)
    
    async def create_roster_embed(self, roster_data: dict, roster_name: str):
        embed = discord.Embed(
            title=f"📋 {roster_name}",
            description=f"Event: **{self.event_name}**",
            color=Colors.get_gradient_color()
        )
        
        for room in roster_data["rooms"]:
            member_list = []
            for member in room["members"]:
                member_list.append(f"• {member['username']}")
            
            embed.add_field(
                name=f"🏠 Room {room['room_number']}",
                value="\n".join(member_list) if member_list else "Empty",
                inline=True
            )
        
        embed.set_footer(text=f"Total: {len(roster_data['rooms'])} rooms • {roster_data['members_per_room']} members each")
        return embed

class EventManagementView(ui.View):
    def __init__(self, event_data: dict):
        super().__init__(timeout=300)
        self.event_data = event_data
    
    @ui.button(label="Send RSVP", style=discord.ButtonStyle.primary, emoji=Em