# utils/database.py
"""Database management for PostgreSQL"""

import asyncpg
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.pool = None
        self.database_url = "postgresql://postgres:gNSFmvlWAWfOEpeuiwxpAQCOFFoKAARG@tramway.proxy.rlwy.net:23459/railway"
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            await self.create_base_tables()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
    
    async def create_base_tables(self):
        """Create base tables that don't require guild-specific schemas"""
        async with self.pool.acquire() as conn:
            # Guild configuration table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS guild_configs (
                    guild_id BIGINT PRIMARY KEY,
                    reminder_channel_id BIGINT,
                    timezone VARCHAR(50) DEFAULT 'UTC',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
    
    async def create_guild_schema(self, guild_id: int):
        """Create guild-specific schema and tables"""
        schema_name = f"guild_{guild_id}"
        
        async with self.pool.acquire() as conn:
            # Create schema
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            
            # Members table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.members (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    status VARCHAR(20) DEFAULT 'Member',
                    profile_background VARCHAR(50) DEFAULT 'hellforge',
                    join_date TIMESTAMP DEFAULT NOW(),
                    last_updated TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Member stats table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.member_stats (
                    user_id BIGINT PRIMARY KEY REFERENCES {schema_name}.members(user_id),
                    -- Basic Stats
                    discord_id VARCHAR(255),
                    character_name VARCHAR(255),
                    character_class VARCHAR(50),
                    shadow_rank VARCHAR(50),
                    clan_role VARCHAR(255),
                    
                    -- Combat Stats
                    combat_rating INTEGER DEFAULT 0,
                    resonance INTEGER DEFAULT 0,
                    paragon_level INTEGER DEFAULT 0,
                    
                    -- Secondary Stats
                    damage INTEGER DEFAULT 0,
                    life INTEGER DEFAULT 0,
                    armor INTEGER DEFAULT 0,
                    armor_penetration INTEGER DEFAULT 0,
                    potency INTEGER DEFAULT 0,
                    resistance INTEGER DEFAULT 0,

                    -- Core Attributes
                    strength INTEGER DEFAULT 0,
                    intelligence INTEGER DEFAULT 0,
                    fortitude INTEGER DEFAULT 0,
                    willpower INTEGER DEFAULT 0,
                    vitality INTEGER DEFAULT 0,
                    
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Events table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.events (
                    event_id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    event_date TIMESTAMP NOT NULL,
                    created_by BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # RSVP table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.rsvp (
                    rsvp_id SERIAL PRIMARY KEY,
                    event_id INTEGER REFERENCES {schema_name}.events(event_id),
                    user_id BIGINT REFERENCES {schema_name}.members(user_id),
                    response VARCHAR(20) NOT NULL,
                    notes TEXT,
                    responded_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Attendance table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.attendance (
                    attendance_id SERIAL PRIMARY KEY,
                    event_id INTEGER REFERENCES {schema_name}.events(event_id),
                    user_id BIGINT REFERENCES {schema_name}.members(user_id),
                    attended BOOLEAN DEFAULT FALSE,
                    marked_by BIGINT,
                    marked_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Rosters table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.rosters (
                    roster_id SERIAL PRIMARY KEY,
                    event_id INTEGER REFERENCES {schema_name}.events(event_id),
                    roster_name VARCHAR(255) NOT NULL,
                    roster_data JSONB NOT NULL,
                    created_by BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Voting table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.votes (
                    vote_id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    options JSONB NOT NULL,
                    target_role BIGINT,
                    created_by BIGINT NOT NULL,
                    end_date TIMESTAMP NOT NULL,
                    is_anonymous BOOLEAN DEFAULT TRUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Vote responses table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.vote_responses (
                    response_id SERIAL PRIMARY KEY,
                    vote_id INTEGER REFERENCES {schema_name}.votes(vote_id),
                    user_id BIGINT,
                    selected_option INTEGER NOT NULL,
                    responded_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Insert guild config
            await conn.execute("""
                INSERT INTO guild_configs (guild_id) 
                VALUES ($1) 
                ON CONFLICT (guild_id) DO NOTHING
            """, guild_id)
            
            logger.info(f"Created schema for guild {guild_id}")
    
    # Member management methods
    async def add_member(self, guild_id: int, user_id: int, username: str, status: str = "Member"):
        """Add a new member"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO {schema_name}.members (user_id, username, status)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = $2,
                    status = $3,
                    last_updated = NOW()
            """, user_id, username, status)
    
    async def get_member(self, guild_id: int, user_id: int):
        """Get member information"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(f"""
                SELECT m.*, ms.*
                FROM {schema_name}.members m
                LEFT JOIN {schema_name}.member_stats ms ON m.user_id = ms.user_id
                WHERE m.user_id = $1
            """, user_id)
    
    async def get_all_members(self, guild_id: int, status_filter: str = None):
        """Get all members, optionally filtered by status"""
        schema_name = f"guild_{guild_id}"
        query = f"""
            SELECT m.*, ms.*
            FROM {schema_name}.members m
            LEFT JOIN {schema_name}.member_stats ms ON m.user_id = ms.user_id
        """
        params = []
        
        if status_filter:
            if status_filter.lower() == "current":
                query += " WHERE m.status IN ('Member', 'Officer')"
            elif status_filter.lower() == "alumni":
                query += " WHERE m.status = 'Alumni'"
            else:
                query += " WHERE m.status = $1"
                params.append(status_filter)
        
        query += " ORDER BY m.join_date"
        
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *params)
    
    async def update_member_stats(self, guild_id: int, user_id: int, stats: Dict[str, Any]):
        """Update member stats"""
        schema_name = f"guild_{guild_id}"
        
        # Build dynamic query based on provided stats
        set_clauses = []
        values = []
        param_count = 1
        
        for key, value in stats.items():
            set_clauses.append(f"{key} = ${param_count}")
            values.append(value)
            param_count += 1
        
        set_clauses.append(f"updated_at = NOW()")
        values.extend([user_id])
        
        query = f"""
            INSERT INTO {schema_name}.member_stats (user_id, {', '.join(stats.keys())})
            VALUES (${param_count}, {', '.join([f'${i+1}' for i in range(len(stats))])})
            ON CONFLICT (user_id) DO UPDATE SET
                {', '.join(set_clauses)}
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(query, *values)
    
    # Event management methods
    async def create_event(self, guild_id: int, name: str, description: str, 
                          event_date: datetime, created_by: int):
        """Create a new event"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            return await conn.fetchval(f"""
                INSERT INTO {schema_name}.events (name, description, event_date, created_by)
                VALUES ($1, $2, $3, $4)
                RETURNING event_id
            """, name, description, event_date, created_by)
    
    async def get_event(self, guild_id: int, event_id: int):
        """Get event information"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(f"""
                SELECT * FROM {schema_name}.events
                WHERE event_id = $1 AND is_active = TRUE
            """, event_id)
    
    async def get_upcoming_events(self, guild_id: int, days_ahead: int = 30):
        """Get upcoming events"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            return await conn.fetch(f"""
                SELECT * FROM {schema_name}.events
                WHERE event_date >= NOW() 
                AND event_date <= NOW() + INTERVAL '{days_ahead} days'
                AND is_active = TRUE
                ORDER BY event_date
            """)
    
    # RSVP methods
    async def add_rsvp(self, guild_id: int, event_id: int, user_id: int, 
                      response: str, notes: str = None):
        """Add or update RSVP response"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO {schema_name}.rsvp (event_id, user_id, response, notes)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (event_id, user_id) DO UPDATE SET
                    response = $3,
                    notes = $4,
                    responded_at = NOW()
            """, event_id, user_id, response, notes)
    
    async def get_event_rsvps(self, guild_id: int, event_id: int):
        """Get all RSVPs for an event"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            return await conn.fetch(f"""
                SELECT r.*, m.username
                FROM {schema_name}.rsvp r
                JOIN {schema_name}.members m ON r.user_id = m.user_id
                WHERE r.event_id = $1
                ORDER BY r.responded_at
            """, event_id)
    
    # Attendance methods
    async def mark_attendance(self, guild_id: int, event_id: int, 
                            attendees: List[int], marked_by: int):
        """Mark attendance for an event"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            # First, get all RSVPs for the event
            rsvps = await conn.fetch(f"""
                SELECT user_id FROM {schema_name}.rsvp WHERE event_id = $1
            """, event_id)
            
            # Mark attendance for all RSVP users
            for rsvp in rsvps:
                attended = rsvp['user_id'] in attendees
                await conn.execute(f"""
                    INSERT INTO {schema_name}.attendance (event_id, user_id, attended, marked_by)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (event_id, user_id) DO UPDATE SET
                        attended = $3,
                        marked_by = $4,
                        marked_at = NOW()
                """, event_id, rsvp['user_id'], attended, marked_by)
    
    async def get_member_attendance(self, guild_id: int, user_id: int, limit: int = 5):
        """Get member's attendance history"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            # Get attendance percentage
            attendance_stats = await conn.fetchrow(f"""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(*) FILTER (WHERE attended = TRUE) as attended_events
                FROM {schema_name}.attendance
                WHERE user_id = $1
            """, user_id)
            
            # Get recent attendance
            recent_events = await conn.fetch(f"""
                SELECT e.name, e.created_at as event_date, a.attended
                FROM {schema_name}.attendance a
                JOIN {schema_name}.events e ON a.event_id = e.event_id
                WHERE a.user_id = $1
                ORDER BY e.created_at DESC
                LIMIT $2
            """, user_id, limit)
            
            return {
                "stats": attendance_stats,
                "recent": recent_events
            }
    
    # Voting methods
    async def create_vote(self, guild_id: int, title: str, description: str,
                         options: List[str], target_role: int, created_by: int,
                         end_date: datetime, is_anonymous: bool = True):
        """Create a new vote"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            return await conn.fetchval(f"""
                INSERT INTO {schema_name}.votes 
                (title, description, options, target_role, created_by, end_date, is_anonymous)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING vote_id
            """, title, description, json.dumps(options), target_role, created_by, end_date, is_anonymous)
    
    async def add_vote_response(self, guild_id: int, vote_id: int, user_id: int, option: int):
        """Add a vote response"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO {schema_name}.vote_responses (vote_id, user_id, selected_option)
                VALUES ($1, $2, $3)
                ON CONFLICT (vote_id, user_id) DO UPDATE SET
                    selected_option = $3,
                    responded_at = NOW()
            """, vote_id, user_id, option)
    
    async def get_vote_results(self, guild_id: int, vote_id: int):
        """Get vote results"""
        schema_name = f"guild_{guild_id}"
        async with self.pool.acquire() as conn:
            # Get vote info
            vote_info = await conn.fetchrow(f"""
                SELECT * FROM {schema_name}.votes WHERE vote_id = $1
            """, vote_id)
            
            # Get response counts
            results = await conn.fetch(f"""
                SELECT selected_option, COUNT(*) as count
                FROM {schema_name}.vote_responses
                WHERE vote_id = $1
                GROUP BY selected_option
                ORDER BY selected_option
            """, vote_id)
            
            return {
                "vote_info": vote_info,
                "results": results
            }