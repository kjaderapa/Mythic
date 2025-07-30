# cogs/member_stats.py
"""Member stats management cog"""

import discord
from discord.ext import commands
from discord import ui
from typing import Dict, Any
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
                "character_name": "Character Name",
                "character_class": "Class",
                "server_name": "Server Name"
            },
            "combat": {
                "combat_rating": "Combat Rating",
                "resonance": "Resonance",
                "paragon_level": "Paragon Level",
                "server_rank": "Server Rank",
                "kills": "Kills"
            },
            "secondary": {
                "immortal_rank": "Immortal Rank",
                "shadow_rank": "Shadow Rank",
                "clan_contribution": "Clan Contribution"
            },
            "attributes": {
                "damage": "Damage",
                "life": "Life",
                "armor": "Armor",
                "armor_penetration": "Armor Penetration",
                "potency": "Potency",
                "resistance": "Resistance"
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
        