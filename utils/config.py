class Config:
    # Database settings
    DATABASE_URL = "postgresql://postgres:gNSFmvlWAWfOEpeuiwxpAQCOFFoKAARG@tramway.proxy.rlwy.net:23459/railway"
    
    # Bot settings
    MAX_CURRENT_MEMBERS = 100
    DEFAULT_ROSTERS = ["Exalted", "Eminent", "Famed", "Proud"]
    
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
