class Config:
    # Database settings
    DATABASE_URL = "postgresql://postgres:gNSFmvlWAWfOEpeuiwxpAQCOFFoKAARG@tramway.proxy.rlwy.net:23459/railway"
    
    # Bot settings
    MAX_CURRENT_MEMBERS = 100
    DEFAULT_ROSTERS = ["Exalted", "Eminent", "Famed", "Proud"]
    
    # Discord bot token placeholder removed for security reasons
    # Please set your Discord bot token as an environment variable named DISCORD_BOT_TOKEN
    
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
    
    # Background options for profiles with image URLs added
    PROFILE_BACKGROUNDS = {
        "hellforge": "https://example.com/images/hellforge.jpg",
        "sanctuary": "https://example.com/images/sanctuary.jpg",
        "westmarch": "https://example.com/images/westmarch.jpg",
        "library": "https://example.com/images/library.jpg",
        "cathedral": "https://example.com/images/cathedral.jpg",
        "demon_hunter": "https://example.com/images/demon_hunter.jpg",
        "barbarian": "https://example.com/images/barbarian.jpg",
        "wizard": "https://example.com/images/wizard.jpg",
        "monk": "https://example.com/images/monk.jpg",
        "necromancer": "https://example.com/images/necromancer.jpg",
        "crusader": "https://example.com/images/crusader.jpg"
    }
