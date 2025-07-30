import os
import asyncio
import discord
from discord.ext import commands, tasks
from datetime import datetime
import logging

from database_manager import DatabaseManager
from config_utils import Config, Colors, Emojis
from clan_management_cog import ClanManagement
from member_stats_complete import MemberStats
from events_cog import Events
from remaining_cogs import Attendance, Voting, CalendarSystem

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClanBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        
        self.db = None
        self.config = Config()
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        # Initialize database
        self.db = DatabaseManager()
        await self.db.initialize()
        
        # Load cogs
        await self.load_extension('clan_management_cog')
        await self.load_extension('member_stats_complete')
        await self.load_extension('events_cog')
        await self.load_extension('attendance_cog')
        await self.load_extension('voting_cog')
        await self.load_extension('calendar_system_cog')
        await self.load_extension('help_system_cog')
        
        logger.info("All cogs loaded successfully")
        
        # Sync commands to force update and remove old commands
        await self.tree.sync()
        
        # Start background tasks
        self.reminder_task.start()
        
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="over the Immortal clans ⚔️"
        )
        await self.change_presence(activity=activity)
        
    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        await self.db.create_guild_schema(guild.id)
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
        
    async def on_guild_remove(self, guild):
        """Called when bot leaves a guild"""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
        
    @tasks.loop(minutes=30)
    async def reminder_task(self):
        """Background task for event reminders"""
        try:
            calendar_cog = self.get_cog('CalendarSystem')
            if calendar_cog:
                await calendar_cog.check_reminders()
        except Exception as e:
            logger.error(f"Error in reminder task: {e}")
            
    @reminder_task.before_loop
    async def before_reminder_task(self):
        """Wait until bot is ready before starting reminder task"""
        await self.wait_until_ready()

async def main():
    """Main function to run the bot"""
    bot = ClanBot()
    
    try:
        # Get token from environment variable or config file
        token = os.getenv('DISCORD_BOT_TOKEN') or bot.config.DISCORD_BOT_TOKEN
        if not token:
            logger.error("Discord bot token not found in environment variable or config file!")
            return
            
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
    finally:
        if bot.db:
            await bot.db.close()

if __name__ == "__main__":
    asyncio.run(main())