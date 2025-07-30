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
        import random
        colors = [cls.BLOOD_RED, cls.GOLD, cls.SHADOW_PURPLE, 
                 cls.IMMORTAL_BLUE, cls.EMBER_ORANGE, cls.MYSTIC_GREEN]
        return random.choice(colors)
    
    @classmethod
    def get_gradient_color(cls):
        import random
        colors = [cls.CRIMSON, cls.RUBY, cls.SAPPHIRE, 
                 cls.EMERALD, cls.AMETHYST, cls.TOPAZ]
        return random.choice(colors)
