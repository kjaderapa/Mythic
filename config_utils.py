# utils/config.py
"""Configuration settings for the bot"""

class Config:
    # Database settings
    DATABASE_URL = "postgresql://postgres:gNSFmvlWAWfOEpeuiwxpAQCOFFoKAARG@tramway.proxy.rlwy.net:23459/railway"
    
    # Bot settings
    MAX_CURRENT_MEMBERS = 100
    DEFAULT_ROSTERS = ["Exalted", "Eminent", "Famed", "Proud"]
    
    # Discord Bot Token (add your token here)
    DISCORD_BOT_TOKEN = "MTM5OTQ5ODE2ODUyOTU4NDE4OA.GpCGHi.Gl3kJgSd_t9vO2T5UfzEvHWIW4LMTzyvGY_nY8"
    DISCORD_TOKEN = "MTM5OTQ5ODE2ODUyOTU4NDE4OA.GpCGHi.Gl3kJgSd_t9vO2T5UfzEvHWIW4LMTzyvGY_nY8"
    
    # Emoji mappings for stats
    STAT_EMOJIS = {
        'combat_rating': '⚔️',
        'resonance': '💎',
        'paragon_level': '🌟',
        'server_rank': '🏆',
        'kills': '💀',
        'class': '🛡️',
        'immortal_rank': '👑',
        'shadow_rank': '🌙',
        'attendance': '📊',
        'damage': '💥',
        'life': '❤️',
        'armor': '🛡️',
        'resistance': '🔰'
    }
    
    # Background options for profiles
    PROFILE_BACKGROUNDS = [
        "hellforge", "sanctuary", "westmarch", "library", 
        "cathedral", "demon_hunter", "barbarian", "wizard",
        "monk", "necromancer", "crusader"
    ]


# utils/colors.py
"""Custom color palette for embeds"""

import discord

class Colors:
    # Primary Diablo-themed colors
    BLOOD_RED = discord.Color.from_rgb(139, 0, 0)
    GOLD = discord.Color.from_rgb(255, 215, 0)
    SHADOW_PURPLE = discord.Color.from_rgb(75, 0, 130)
    IMMORTAL_BLUE = discord.Color.from_rgb(0, 191, 255)
    
    # Secondary colors
    EMBER_ORANGE = discord.Color.from_rgb(255, 140, 0)
    MYSTIC_GREEN = discord.Color.from_rgb(50, 205, 50)
    VOID_BLACK = discord.Color.from_rgb(25, 25, 25)
    CELESTIAL_WHITE = discord.Color.from_rgb(248, 248, 255)
    
    # Gradient colors for variety
    CRIMSON = discord.Color.from_rgb(220, 20, 60)
    RUBY = discord.Color.from_rgb(224, 17, 95)
    SAPPHIRE = discord.Color.from_rgb(15, 82, 186)
    EMERALD = discord.Color.from_rgb(80, 200, 120)
    AMETHYST = discord.Color.from_rgb(153, 102, 204)
    TOPAZ = discord.Color.from_rgb(255, 200, 124)
    
    # Status colors
    SUCCESS = MYSTIC_GREEN
    ERROR = BLOOD_RED
    WARNING = EMBER_ORANGE
    INFO = IMMORTAL_BLUE
    
    @classmethod
    def get_random_primary(cls):
        """Get a random primary color"""
        import random
        colors = [cls.BLOOD_RED, cls.GOLD, cls.SHADOW_PURPLE, 
                 cls.IMMORTAL_BLUE, cls.EMBER_ORANGE, cls.MYSTIC_GREEN]
        return random.choice(colors)
    
    @classmethod
    def get_gradient_color(cls):
        """Get a random gradient color"""
        import random
        colors = [cls.CRIMSON, cls.RUBY, cls.SAPPHIRE, 
                 cls.EMERALD, cls.AMETHYST, cls.TOPAZ]
        return random.choice(colors)


# utils/emojis.py
"""Custom emoji definitions"""

class Emojis:
    # Combat stats
    COMBAT_RATING = "⚔️"
    RESONANCE = "💎"
    PARAGON = "🌟"
    RANK = "🏆"
    KILLS = "💀"
    
    # Classes
    BARBARIAN = "🪓"
    CRUSADER = "🛡️"
    DEMON_HUNTER = "🏹"
    MONK = "👊"
    NECROMANCER = "💀"
    WIZARD = "🔮"
    
    # Attributes
    DAMAGE = "💥"
    LIFE = "❤️"
    ARMOR = "🛡️"
    RESISTANCE = "🔰"
    
    # UI Elements
    EDIT = "✏️"
    DELETE = "🗑️"
    CONFIRM = "✅"
    CANCEL = "❌"
    NEXT = "➡️"
    PREVIOUS = "⬅️"
    UP = "⬆️"
    DOWN = "⬇️"
    
    # Status
    ONLINE = "🟢"
    OFFLINE = "🔴"
    AWAY = "🟡"
    
    # Roles
    MEMBER = "👤"
    OFFICER = "👮"
    ALUMNI = "🎓"
    LEADER = "👑"
    
    # Events
    EVENT = "📅"
    RSVP_YES = "✅"
    RSVP_NO = "❌"
    RSVP_MAYBE = "❔"
    
    # Calendar
    CALENDAR = "📅"
    REMINDER = "⏰"
    
    # Voting
    VOTE = "🗳️"
    POLL = "📊"