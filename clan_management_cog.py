# cogs/clan_management.py
"""Clan management cog for member administration"""

import discord
from discord.ext import commands
from discord import ui
from typing import List, Dict, Any
import asyncio

from config_utils import Colors, Emojis, Config

class MemberSelectView(ui.View):
    def __init__(self, members: List[Dict], action: str):
        super().__init__(timeout=300)
        self.members = members
        self.action = action
        self.selected_members = []
        
        # Create select menu with members
        options = []
        for member in members[:25]:  # Discord limit
            status_emoji = {
                'Member': Emojis.MEMBER,
                'Officer': Emojis.OFFICER,
                'Alumni': Emojis.ALUMNI,
                'Leader': Emojis.LEADER
            }.get(member.get('status', 'Member'), Emojis.MEMBER)
            
            options.append(discord.SelectOption(
                label=member['username'][:100],
                value=str(member['user_id']),
                description=f"Status: {member.get('status', 'Member')}",
                emoji=status_emoji
            ))
        
        if options:
            self.member_select = ui.Select(
                placeholder=f"Select members to {action}...",
                options=options,
                max_values=min(len(options), 25)
            )
            self.member_select.callback = self.member_selected
            self.add_item(self.member_select)
    
    async def member_selected(self, interaction: discord.Interaction):
        self.selected_members = [int(user_id) for user_id in self.member_select.values]
        
        if self.action == "promote":
            await self.show_status_select(interaction)
        elif self.action == "demote":
            await self.demote_members(interaction)
        elif self.action == "request_edit":
            await self.send_edit_requests(interaction)
    
    async def show_status_select(self, interaction: discord.Interaction):
        """Show status selection for promotion"""
        view = StatusSelectView(self.selected_members)
        
        embed = discord.Embed(
            title="👑 Select New Status",
            description=f"Choose the new status for {len(self.selected_members)} selected member(s):",
            color=Colors.GOLD
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def demote_members(self, interaction: discord.Interaction):
        """Demote selected members to regular members"""
        bot = interaction.client
        
        for user_id in self.selected_members:
            await bot.db.add_member(interaction.guild.id, user_id, "temp", "Member")
        
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} Members Demoted",
            description=f"Successfully demoted {len(self.selected_members)} member(s) to regular Member status.",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def send_edit_requests(self, interaction: discord.Interaction):
        """Send edit requests to selected members"""
        bot = interaction.client
        sent_count = 0
        failed_count = 0
        
        for user_id in self.selected_members:
            try:
                user = interaction.guild.get_member(user_id)
                if user:
                    embed = discord.Embed(
                        title=f"{Emojis.EDIT} Stats Update Request",
                        description=f"An officer has requested that you update your clan member stats.",
                        color=Colors.INFO
                    )
                    
                    embed.add_field(
                        name="📝 Instructions",
                        value="Please use the `/profile` command in the server to update your stats.",
                        inline=False
                    )
                    
                    embed.set_footer(text=f"Request sent by {interaction.user.display_name}")
                    
                    await user.send(embed=embed)
                    sent_count += 1
                    await asyncio.sleep(0.5)  # Rate limiting
            except discord.Forbidden:
                failed_count += 1
            except Exception:
                failed_count += 1
        
        # Send confirmation
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} Edit Requests Sent",
            description=f"Successfully sent edit requests to **{sent_count}** member(s).",
            color=Colors.SUCCESS
        )
        
        if failed_count > 0:
            embed.add_field(
                name="⚠️ Failed to Send",
                value=f"{failed_count} member(s) couldn't be reached (DMs disabled)",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class StatusSelectView(ui.View):
    def __init__(self, selected_members: List[int]):
        super().__init__(timeout=300)
        self.selected_members = selected_members
    
    @ui.select(
        placeholder="Choose new status...",
        options=[
            discord.SelectOption(label="Member", value="Member", emoji=Emojis.MEMBER),
            discord.SelectOption(label="Officer", value="Officer", emoji=Emojis.OFFICER),
            discord.SelectOption(label="Alumni", value="Alumni", emoji=Emojis.ALUMNI),
            discord.SelectOption(label="Leader", value="Leader", emoji=Emojis.LEADER)
        ]
    )
    async def status_select(self, interaction: discord.Interaction, select: ui.Select):
        new_status = select.values[0]
        bot = interaction.client
        
        # Update all selected members
        for user_id in self.selected_members:
            user = interaction.guild.get_member(user_id)
            if user:
                await bot.db.add_member(interaction.guild.id, user_id, user.display_name, new_status)
        
        embed = discord.Embed(
            title=f"{Emojis.CONFIRM} Status Updated",
            description=f"Successfully updated {len(self.selected_members)} member(s) to **{new_status}** status.",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class LeaderboardView(ui.View):
    def __init__(self, members: List[Dict]):
        super().__init__(timeout=300)
        self.members = members
        self.current_sort = "combat_rating"
        self.page = 0
        self.per_page = 10
    
    @ui.select(
        placeholder="Sort leaderboard by...",
        options=[
            discord.SelectOption(label="Combat Rating", value="combat_rating", emoji=Emojis.COMBAT_RATING),
            discord.SelectOption(label="Resonance", value="resonance", emoji=Emojis.RESONANCE),
            discord.SelectOption(label="Paragon Level", value="paragon_level", emoji=Emojis.PARAGON),
            discord.SelectOption(label="Server Rank", value="server_rank", emoji=Emojis.RANK),
            discord.SelectOption(label="Kills", value="kills", emoji=Emojis.KILLS),
            discord.SelectOption(label="Attendance", value="attendance", emoji="📊"),
            discord.SelectOption(label="Join Date", value="join_date", emoji="📅")
        ]
    )
    async def sort_select(self, interaction: discord.Interaction, select: ui.Select):
        self.current_sort = select.values[0]
        self.page = 0
        await self.update_leaderboard(interaction)
    
    @ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji=Emojis.PREVIOUS)
    async def previous_page(self, interaction: discord.Interaction, button: ui.Button):
        if self.page > 0:
            self.page -= 1
            await self.update_leaderboard(interaction)
        else:
            await interaction.response.send_message("Already on first page!", ephemeral=True)
    
    @ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji=Emojis.NEXT)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        max_pages = (len(self.members) - 1) // self.per_page
        if self.page < max_pages:
            self.page += 1
            await self.update_leaderboard(interaction)
        else:
            await interaction.response.send_message("Already on last page!", ephemeral=True)
    
    async def update_leaderboard(self, interaction: discord.Interaction):
        # Sort members
        if self.current_sort == "attendance":
            # TODO: Implement attendance sorting when attendance system is complete
            sorted_members = self.members
        else:
            reverse = self.current_sort not in ["server_rank"]  # Lower rank number is better
            sorted_members = sorted(
                self.members,
                key=lambda x: x.get(self.current_sort) or 0,
                reverse=reverse
            )
        
        # Create leaderboard embed
        embed = discord.Embed(
            title=f"🏆 Clan Leaderboard - {self.current_sort.replace('_', ' ').title()}",
            color=Colors.GOLD
        )
        
        start_idx = self.page * self.per_page
        end_idx = start_idx + self.per_page
        page_members = sorted_members[start_idx:end_idx]
        
        leaderboard_text = ""
        for i, member in enumerate(page_members, start=start_idx + 1):
            # Get medal emoji for top 3
            if i == 1:
                rank_emoji = "🥇"
            elif i == 2:
                rank_emoji = "🥈"
            elif i == 3:
                rank_emoji = "🥉"
            else:
                rank_emoji = f"{i}."
            
            value = member.get(self.current_sort)
            if value is None:
                value_str = "Not Set"
            elif isinstance(value, int):
                value_str = f"{value:,}"
            else:
                value_str = str(value)
            
            leaderboard_text += f"{rank_emoji} **{member['username']}** - {value_str}\n"
        
        embed.description = leaderboard_text
        
        # Add pagination info
        total_pages = (len(sorted_members) - 1) // self.per_page + 1
        embed.set_footer(text=f"Page {self.page + 1} of {total_pages} • {len(sorted_members)} total members")
        
        await interaction.response.edit_message(embed=embed, view=self)

async def setup(bot):
    await bot.add_cog(ClanManagement(bot))

class ClanManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_group(name="clan", description="Clan management commands")
    async def clan(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🏛️ Clan Management",
                description="Available clan management commands:",
                color=Colors.get_random_primary()
            )
            
            embed.add_field(
                name="📋 `/clan manifest`",
                value="View all clan members with sorting options",
                inline=False
            )
            
            embed.add_field(
                name="👑 `/clan promote`",
                value="Promote members to officer status (officers only)",
                inline=False
            )
            
            embed.add_field(
                name="📉 `/clan demote`",
                value="Demote officers to member status (officers only)",
                inline=False
            )
            
            embed.add_field(
                name="✏️ `/clan request_edit`",
                value="Request members to update their stats (officers only)",
                inline=False
            )
            
            embed.add_field(
                name="🏆 `/clan leaderboard`",
                value="View clan leaderboard with various sorting options",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    @clan.command(name="manifest", description="View all clan members")
    async def manifest(self, ctx, filter_type: str = "all"):
        """View clan member manifest with filtering"""
        valid_filters = ["all", "current", "alumni"]
        if filter_type.lower() not in valid_filters:
            embed = discord.Embed(
                title="❌ Invalid Filter",
                description=f"Valid filters are: {', '.join(valid_filters)}",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Ensure guild schema exists before querying
        await self.bot.db.create_guild_schema(ctx.guild.id)
        
        # Get members based on filter
        if filter_type.lower() == "all":
            members = await self.bot.db.get_all_members(ctx.guild.id)
        else:
            members = await self.bot.db.get_all_members(ctx.guild.id, filter_type.lower())
        
        if not members:
            embed = discord.Embed(
                title="📭 No Members Found",
                description=f"No {filter_type} members found in the database.",
                color=Colors.INFO
            )
            await ctx.send(embed=embed)
            return
        
        # Create manifest embed
        embed = discord.Embed(
            title=f"📋 Clan Manifest - {filter_type.title()} Members",
            description=f"Total: {len(members)} members",
            color=Colors.get_gradient_color()
        )
        
        # Group members by status
        status_groups = {}
        for member in members:
            status = member.get('status', 'Member')
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(member)
        
        # Display each status group
        for status, group_members in status_groups.items():
            status_emoji = {
                'Leader': Emojis.LEADER,
                'Officer': Emojis.OFFICER,
                'Member': Emojis.MEMBER,
                'Alumni': Emojis.ALUMNI
            }.get(status, Emojis.MEMBER)
            
            member_list = []
            for member in group_members[:15]:  # Limit to 15 per group
                combat_rating = member.get('combat_rating')
                cr_text = f" ({combat_rating:,} CR)" if combat_rating else ""
                member_list.append(f"• {member['username']}{cr_text}")
            
            if len(group_members) > 15:
                member_list.append(f"• ... and {len(group_members) - 15} more")
            
            if member_list:
                embed.add_field(
                    name=f"{status_emoji} {status} ({len(group_members)})",
                    value="\n".join(member_list),
                    inline=True
                )
        
        # Add leaderboard button for officers
        view = None
        if any(role.name.lower() in ['officer', 'leader', 'admin'] for role in ctx.author.roles):
            view = ManifestView(members)
        
        await ctx.send(embed=embed, view=view)
    
    @clan.command(name="promote", description="Promote members to higher status")
    async def promote(self, ctx):
        """Promote members (officers only)"""
        # Check permissions
        if not any(role.name.lower() in ['officer', 'leader', 'admin'] for role in ctx.author.roles):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only officers can promote members!",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Get current members who can be promoted
        members = await self.bot.db.get_all_members(ctx.guild.id, "current")
        promotable_members = [m for m in members if m.get('status') in ['Member', 'Officer']]
        
        if not promotable_members:
            embed = discord.Embed(
                title="📭 No Members to Promote",
                description="No promotable members found.",
                color=Colors.INFO
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        view = MemberSelectView(promotable_members, "promote")
        
        embed = discord.Embed(
            title="👑 Promote Members",
            description="Select members to promote to a higher status:",
            color=Colors.GOLD
        )
        
        await ctx.send(embed=embed, view=view, ephemeral=True)
    
    @clan.command(name="demote", description="Demote officers to member status")
    async def demote(self, ctx):
        """Demote officers (officers only)"""
        # Check permissions
        if not any(role.name.lower() in ['officer', 'leader', 'admin'] for role in ctx.author.roles):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only officers can demote members!",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Get officers who can be demoted
        members = await self.bot.db.get_all_members(ctx.guild.id)
        officers = [m for m in members if m.get('status') == 'Officer']
        
        if not officers:
            embed = discord.Embed(
                title="📭 No Officers to Demote",
                description="No officers found to demote.",
                color=Colors.INFO
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        view = MemberSelectView(officers, "demote")
        
        embed = discord.Embed(
            title="📉 Demote Officers",
            description="Select officers to demote to member status:",
            color=Colors.WARNING
        )
        
        await ctx.send(embed=embed, view=view, ephemeral=True)
    
    @clan.command(name="request_edit", description="Request members to update their stats")
    async def request_edit(self, ctx):
        embed = discord.Embed(
            title="✏️ Request Edit",
            description="This command will send a request to selected members to update their stats.",
            color=Colors.INFO
        )
        await ctx.send(embed=embed, ephemeral=True)
