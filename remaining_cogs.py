# cogs/attendance.py
"""Attendance tracking cog"""

import discord
from discord.ext import commands
from discord import ui
from typing import List, Dict
from datetime import datetime

from config_utils import Colors, Emojis

class AttendanceMarkView(ui.View):
    def __init__(self, event_data: dict, rsvps: List[dict]):
        super().__init__(timeout=600)
        self.event_data = event_data
        self.rsvps = rsvps
        self.attended_members = set()
        
        # Create checkboxes for each RSVP
        for i, rsvp in enumerate(rsvps[:25]):  # Discord limit
            checkbox = ui.Button(
                label=rsvp['username'],
                style=discord.ButtonStyle.secondary,
                custom_id=f"attend_{rsvp['user_id']}",
                row=i // 5
            )
            checkbox.callback = self.toggle_attendance
            self.add_item(checkbox)
        
        # Add confirm button
        if len(rsvps) <= 25:
            confirm_btn = ui.Button(
                label="Confirm Attendance",
                style=discord.ButtonStyle.success,
                emoji=Emojis.CONFIRM,
                row=4
            )
            confirm_btn.callback = self.confirm_attendance
            self.add_item(confirm_btn)
    
    async def toggle_attendance(self, interaction: discord.Interaction):
        user_id = int(interaction.data['custom_id'].split('_')[1])
        
        if user_id in self.attended_members:
            self.attended_members.remove(user_id)
            style = discord.ButtonStyle.secondary
        else:
            self.attended_members.add(user_id)
            style = discord.ButtonStyle.success
        
        # Update button style
        for item in self.children:
            if hasattr(item, 'custom_id') and item.custom_id == interaction.data['custom_id']:
                item.style = style
                break
        
        await interaction.response.edit_message(view=self)
    
    async def confirm_attendance(self, interaction: discord.Interaction):
        bot = interaction.client
        
        # Mark attendance in database
        await bot.db.mark_attendance(
            interaction.guild.id,
            self.event_data['event_id'],
            list(self.attended_members),
            interaction.user.id
        )
        
        # Create summary embed
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} Attendance Marked",
            description=f"Attendance has been recorded for **{self.event_data['name']}**",
            color=Colors.SUCCESS
        )
        
        attended_count = len(self.attended_members)
        total_rsvps = len(self.rsvps)
        attendance_rate = (attended_count / total_rsvps * 100) if total_rsvps > 0 else 0
        
        embed.add_field(
            name="📊 Summary",
            value=f"**Attended:** {attended_count}/{total_rsvps} ({attendance_rate:.1f}%)",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class Attendance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="mark_attendance", description="Mark attendance for an event")
    async def mark_attendance(self, ctx, event_id: int):
        """Mark attendance for an event (officers only)"""
        # Check permissions
        if not any(role.name.lower() in ['officer', 'leader', 'admin'] for role in ctx.author.roles):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only officers can mark attendance!",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Get event data
        event_data = await self.bot.db.get_event(ctx.guild.id, event_id)
        if not event_data:
            embed = discord.Embed(
                title="❌ Event Not Found",
                description=f"No event found with ID `{event_id}`",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Get RSVPs for the event
        rsvps = await self.bot.db.get_event_rsvps(ctx.guild.id, event_id)
        if not rsvps:
            embed = discord.Embed(
                title="📭 No RSVPs Found",
                description="No RSVP responses found for this event.",
                color=Colors.INFO
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Create attendance marking interface
        embed = discord.Embed(
            title=f"📊 Mark Attendance: {event_data['name']}",
            description="Click on members who attended the event:",
            color=Colors.get_gradient_color()
        )
        
        embed.add_field(
            name="📅 Event Date",
            value=f"<t:{int(event_data['event_date'].timestamp())}:F>",
            inline=False
        )
        
        embed.add_field(
            name="👥 Total RSVPs",
            value=str(len(rsvps)),
            inline=True
        )
        
        view = AttendanceMarkView(dict(event_data), rsvps)
        await ctx.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Attendance(bot))


# cogs/voting.py
"""Anonymous voting system cog"""

import discord
from discord.ext import commands
from discord import ui
from datetime import datetime, timedelta
import json
from typing import List

from config_utils import Colors, Emojis

class VoteCreateModal(ui.Modal):
    def __init__(self):
        super().__init__(title="Create Anonymous Vote", timeout=300)
        
        self.title_input = ui.TextInput(
            label="Vote Title",
            placeholder="Enter the voting question...",
            max_length=200,
            required=True
        )
        
        self.description_input = ui.TextInput(
            label="Description (Optional)",
            placeholder="Additional details about the vote...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=False
        )
        
        self.options_input = ui.TextInput(
            label="Options (Max 10)",
            placeholder="Option 1\nOption 2\nOption 3\n...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        
        self.duration_input = ui.TextInput(
            label="Duration (Hours)",
            placeholder="How many hours should the vote run? (e.g., 24)",
            max_length=3,
            required=True
        )
        
        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.options_input)
        self.add_item(self.duration_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse options
            options = [opt.strip() for opt in self.options_input.value.split('\n') if opt.strip()]
            
            if len(options) < 2:
                await interaction.response.send_message(
                    "❌ You must provide at least 2 options!",
                    ephemeral=True
                )
                return
            
            if len(options) > 10:
                await interaction.response.send_message(
                    "❌ Maximum 10 options allowed!",
                    ephemeral=True
                )
                return
            
            # Parse duration
            try:
                hours = int(self.duration_input.value)
                if hours < 1 or hours > 168:  # Max 1 week
                    raise ValueError()
            except ValueError:
                await interaction.response.send_message(
                    "❌ Duration must be between 1 and 168 hours!",
                    ephemeral=True
                )
                return
            
            end_date = datetime.now() + timedelta(hours=hours)
            
            # Show role selection
            view = RoleSelectView(
                self.title_input.value,
                self.description_input.value,
                options,
                end_date
            )
            
            embed = discord.Embed(
                title="👥 Select Target Role",
                description="Choose which role can participate in this vote:",
                color=Colors.INFO
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error creating vote: {str(e)}",
                ephemeral=True
            )

class RoleSelectView(ui.View):
    def __init__(self, title: str, description: str, options: List[str], end_date: datetime):
        super().__init__(timeout=300)
        self.vote_title = title
        self.vote_description = description
        self.options = options
        self.end_date = end_date
    
    role_select = ui.RoleSelect(placeholder="Select a role to vote...")

    async def role_select_callback(self, interaction: discord.Interaction, select: ui.RoleSelect):
        target_role = select.values[0]
        
        # Create the vote in database
        bot = interaction.client
        vote_id = await bot.db.create_vote(
            interaction.guild.id,
            self.vote_title,
            self.vote_description,
            self.options,
            target_role.id,
            interaction.user.id,
            self.end_date,
            True  # Anonymous
        )
        
        # Create vote embed
        embed = discord.Embed(
            title=f"{Emojis.VOTE} {self.vote_title}",
            description=self.vote_description,
            color=Colors.get_random_primary()
        )
        
        # Add options
        options_text = ""
        for i, option in enumerate(self.options, 1):
            options_text += f"{i}️⃣ {option}\n"
        
        embed.add_field(
            name="📋 Options",
            value=options_text,
            inline=False
        )
        
        embed.add_field(
            name="⏰ Voting Ends",
            value=f"<t:{int(self.end_date.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="👥 Eligible Voters",
            value=target_role.mention,
            inline=True
        )
        
        embed.set_footer(text=f"Vote ID: {vote_id} • Anonymous voting")
        
        # Create voting view
        vote_view = VotingView(vote_id, self.options, target_role.id)
        
        # Send to channel and mention role
        await interaction.response.send_message(
            content=f"{target_role.mention} - New vote available!",
            embed=embed,
            view=vote_view
        )
        target_role = select.values[0]
        
        # Create the vote in database
        bot = interaction.client
        vote_id = await bot.db.create_vote(
            interaction.guild.id,
            self.vote_title,
            self.vote_description,
            self.options,
            target_role.id,
            interaction.user.id,
            self.end_date,
            True  # Anonymous
        )
        
        # Create vote embed
        embed = discord.Embed(
            title=f"{Emojis.VOTE} {self.vote_title}",
            description=self.vote_description,
            color=Colors.get_random_primary()
        )
        
        # Add options
        options_text = ""
        for i, option in enumerate(self.options, 1):
            options_text += f"{i}️⃣ {option}\n"
        
        embed.add_field(
            name="📋 Options",
            value=options_text,
            inline=False
        )
        
        embed.add_field(
            name="⏰ Voting Ends",
            value=f"<t:{int(self.end_date.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="👥 Eligible Voters",
            value=target_role.mention,
            inline=True
        )
        
        embed.set_footer(text=f"Vote ID: {vote_id} • Anonymous voting")
        
        # Create voting view
        vote_view = VotingView(vote_id, self.options, target_role.id)
        
        # Send to channel and mention role
        await interaction.response.send_message(
            content=f"{target_role.mention} - New vote available!",
            embed=embed,
            view=vote_view
        )

class VotingView(ui.View):
    def __init__(self, vote_id: int, options: List[str], target_role_id: int):
        super().__init__(timeout=None)  # Persistent view
        self.vote_id = vote_id
        self.options = options
        self.target_role_id = target_role_id
    
    @ui.button(label="Cast Vote", style=discord.ButtonStyle.primary, emoji=Emojis.VOTE)
    async def cast_vote(self, interaction: discord.Interaction, button: ui.Button):
        # Check if user has the required role
        target_role = interaction.guild.get_role(self.target_role_id)
        if target_role not in interaction.user.roles:
            await interaction.response.send_message(
                f"❌ You need the {target_role.name} role to vote!",
                ephemeral=True
            )
            return
        
        # Create option selection
        view = VoteOptionView(self.vote_id, self.options)
        
        embed = discord.Embed(
            title="🗳️ Cast Your Vote",
            description="Select your choice:",
            color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="View Results", style=discord.ButtonStyle.secondary, emoji="📊")
    async def view_results(self, interaction: discord.Interaction, button: ui.Button):
        # Check if user is officer or creator
        if not any(role.name.lower() in ['officer', 'leader', 'admin'] for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Only officers can view results!",
                ephemeral=True
            )
            return
        
        bot = interaction.client
        results = await bot.db.get_vote_results(interaction.guild.id, self.vote_id)
        
        if not results['results']:
            await interaction.response.send_message(
                "📭 No votes cast yet!",
                ephemeral=True
            )
            return
        
        # Create results embed
        vote_info = results['vote_info']
        vote_results = results['results']
        
        embed = discord.Embed(
            title=f"📊 Vote Results: {vote_info['title']}",
            color=Colors.get_gradient_color()
        )
        
        total_votes = sum(result['count'] for result in vote_results)
        
        results_text = ""
        for result in vote_results:
            option_index = result['selected_option']
            option_text = self.options[option_index]
            count = result['count']
            percentage = (count / total_votes * 100) if total_votes > 0 else 0
            
            # Create progress bar
            bar_length = 10
            filled = int(percentage / 10)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            results_text += f"{option_index + 1}️⃣ **{option_text}**\n"
            results_text += f"   {bar} {count} votes ({percentage:.1f}%)\n\n"
        
        embed.description = results_text
        embed.set_footer(text=f"Total votes: {total_votes}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class VoteOptionView(ui.View):
    def __init__(self, vote_id: int, options: List[str]):
        super().__init__(timeout=300)
        self.vote_id = vote_id
        
        # Create option buttons
        for i, option in enumerate(options):
            button = ui.Button(
                label=option[:80],  # Discord limit
                style=discord.ButtonStyle.secondary,
                custom_id=f"vote_{i}",
                emoji=f"{i+1}️⃣"
            )
            button.callback = self.option_selected
            self.add_item(button)
    
    async def option_selected(self, interaction: discord.Interaction):
        option_index = int(interaction.data['custom_id'].split('_')[1])
        
        # Save vote to database
        bot = interaction.client
        await bot.db.add_vote_response(
            interaction.guild.id,
            self.vote_id,
            interaction.user.id,
            option_index
        )
        
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} Vote Recorded!",
            description="Your anonymous vote has been recorded successfully.",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class Voting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="vote", description="Create an anonymous vote")
    async def create_vote(self, ctx):
        """Create an anonymous vote (officers only)"""
        # Check permissions
        if not any(role.name.lower() in ['officer', 'leader', 'admin'] for role in ctx.author.roles):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only officers can create votes!",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        modal = VoteCreateModal()
        await ctx.interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(Voting(bot))


# cogs/calendar_system.py
"""Calendar and reminder system cog"""

import discord
from discord.ext import commands, tasks
from discord import ui
from datetime import datetime, timedelta
import calendar

from utils.colors import Colors
from utils.emojis import Emojis

class CalendarView(ui.View):
    def __init__(self, guild_id: int, year: int, month: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.year = year
        self.month = month
    
    @ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_month(self, interaction: discord.Interaction, button: ui.Button):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        
        await self.update_calendar(interaction)
    
    @ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_month(self, interaction: discord.Interaction, button: ui.Button):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        
        await self.update_calendar(interaction)
    
    async def update_calendar(self, interaction: discord.Interaction):
        embed = await self.create_calendar_embed(interaction.client)
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def create_calendar_embed(self, bot):
        embed = discord.Embed(
            title=f"{Emojis.CALENDAR} {calendar.month_name[self.month]} {self.year}",
            color=Colors.get_gradient_color()
        )
        
        # Get events for this month
        start_date = datetime(self.year, self.month, 1)
        if self.month == 12:
            end_date = datetime(self.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(self.year, self.month + 1, 1) - timedelta(days=1)
        
        # Get events from database
        events = await bot.db.get_upcoming_events(self.guild_id, 365)  # Get all events
        month_events = [
            e for e in events 
            if start_date <= e['event_date'] <= end_date
        ]
        
        # Create calendar grid
        cal = calendar.monthcalendar(self.year, self.month)
        
        calendar_text = "```"
        calendar_text += "Mo Tu We Th Fr Sa Su\n"
        
        for week in cal:
            for day in week:
                if day == 0:
                    calendar_text += "   "
                else:
                    # Check if there's an event on this day
                    has_event = any(
                        e['event_date'].day == day for e in month_events
                    )
                    
                    if has_event:
                        calendar_text += f"{day:2}*"
                    else:
                        calendar_text += f"{day:2} "
            calendar_text += "\n"
        
        calendar_text += "```"
        embed.description = calendar_text
        
        # List events for this month
        if month_events:
            events_text = ""
            for event in month_events[:10]:  # Limit to 10
                event_date = event['event_date']
                events_text += f"**{event_date.day}** - {event['name']}\n"
            
            embed.add_field(
                name=f"{Emojis.EVENT} Events This Month",
                value=events_text,
                inline=False
            )
        
        embed.set_footer(text="* = Event scheduled")
        return embed

class CalendarSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="calendar", description="View the clan event calendar")
    async def calendar(self, ctx):
        """Display interactive calendar"""
        now = datetime.now()
        view = CalendarView(ctx.guild.id, now.year, now.month)
        embed = await view.create_calendar_embed(self.bot)
        
        await ctx.send(embed=embed, view=view)
    
    @commands.hybrid_command(name="set_reminder_channel", description="Set the channel for event reminders")
    async def set_reminder_channel(self, ctx, channel: discord.TextChannel = None):
        """Set reminder channel (admin only)"""
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only administrators can set the reminder channel!",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        channel = channel or ctx.channel
        
        # Update database
        async with self.bot.db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE guild_configs 
                SET reminder_channel_id = $1, updated_at = NOW()
                WHERE guild_id = $2
            """, channel.id, ctx.guild.id)
        
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} Reminder Channel Set",
            description=f"Event reminders will now be sent to {channel.mention}",
            color=Colors.SUCCESS
        )
        
        await ctx.send(embed=embed)
    
    async def check_reminders(self):
        """Check for events that need reminders (called by background task)"""
        try:
            # Get all guild configs
            async with self.bot.db.pool.acquire() as conn:
                guild_configs = await conn.fetch("""
                    SELECT guild_id, reminder_channel_id 
                    FROM guild_configs 
                    WHERE reminder_channel_id IS NOT NULL
                """)
            
            for config in guild_configs:
                guild_id = config['guild_id']
                channel_id = config['reminder_channel_id']
                
                # Get events in the next 24 hours
                events = await self.bot.db.get_upcoming_events(guild_id, 1)
                
                for event in events:
                    time_until = event['event_date'] - datetime.now()
                    
                    # Send reminder if event is in 1 hour
                    if timedelta(minutes=55) <= time_until <= timedelta(hours=1, minutes=5):
                        await self.send_reminder(guild_id, channel_id, event)
        
        except Exception as e:
            print(f"Error in check_reminders: {e}")
    
    async def send_reminder(self, guild_id: int, channel_id: int, event: dict):
        """Send reminder for an event"""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
            
            embed = discord.Embed(
                title=f"{Emojis.REMINDER} Event Reminder",
                description=f"**{event['name']}** is starting in approximately 1 hour!",
                color=Colors.WARNING
            )
            
            embed.add_field(
                name="📅 Event Time",
                value=f"<t:{int(event['event_date'].timestamp())}:F>",
                inline=False
            )
            
            if event['description']:
                embed.add_field(
                    name="📝 Description",
                    value=event['description'],
                    inline=False
                )
            
            await channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error sending reminder: {e}")

async def setup(bot):
    await bot.add_cog(CalendarSystem(bot))
