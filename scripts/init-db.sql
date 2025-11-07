-- Database initialization script for Ashiorid AI Manager
-- This runs automatically on first PostgreSQL container startup

\c ashiorid;

-- ============================================================================
-- Character Agent Service Tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS characters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    system_prompt TEXT NOT NULL,
    traits JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    character_name VARCHAR(100) NOT NULL,
    user_message TEXT NOT NULL,
    character_response TEXT NOT NULL,
    lore_sources JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_name) REFERENCES characters(name) ON DELETE CASCADE
);

CREATE INDEX idx_conversations_character ON conversations(character_name);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);

-- ============================================================================
-- Simulation Engine Tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    state VARCHAR(20) NOT NULL,
    position_x INTEGER NOT NULL,
    position_y INTEGER NOT NULL,
    hunger FLOAT NOT NULL DEFAULT 0.0,
    thirst FLOAT NOT NULL DEFAULT 0.0,
    energy FLOAT NOT NULL DEFAULT 1.0,
    health FLOAT NOT NULL DEFAULT 1.0,
    age INTEGER NOT NULL DEFAULT 0,
    inventory JSONB DEFAULT '[]',
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS simulation_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    agent_ids JSONB,
    description TEXT,
    location_x INTEGER,
    location_y INTEGER,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agents_state ON agents(state);
CREATE INDEX idx_agents_position ON agents(position_x, position_y);
CREATE INDEX idx_simulation_events_type ON simulation_events(event_type);
CREATE INDEX idx_simulation_events_created_at ON simulation_events(created_at DESC);

-- ============================================================================
-- Seed Data - Pre-defined Characters
-- ============================================================================

INSERT INTO characters (name, system_prompt, traits) VALUES
(
    'gandalf',
    'You are Gandalf the Grey, a wise and powerful wizard from Middle-earth. You speak with wisdom, use archaic language occasionally, and offer guidance with a mix of mystery and directness. You care deeply about the free peoples of Middle-earth.',
    '{"wisdom": 10, "power": 9, "patience": 8, "humor": 6}'::jsonb
),
(
    'paul_atreides',
    'You are Paul Atreides, also known as Muad''Dib. You possess prescient visions of possible futures and have been trained in the ways of the Bene Gesserit. You are thoughtful, strategic, and burdened by the weight of destiny.',
    '{"prescience": 10, "leadership": 9, "strategy": 10, "burden": 8}'::jsonb
),
(
    'master_chief',
    'You are Master Chief Petty Officer John-117, a Spartan-II super soldier. You are direct, mission-focused, and speak concisely. You are a natural leader but prefer action over words. You are loyal to your team and humanity.',
    '{"combat": 10, "leadership": 8, "loyalty": 10, "brevity": 9}'::jsonb
)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- Database Functions and Triggers
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
CREATE TRIGGER update_characters_updated_at BEFORE UPDATE ON characters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Grant Permissions
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ashiorid_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ashiorid_user;

-- Print success message
DO $$
BEGIN
    RAISE NOTICE '✓ Database initialized successfully';
    RAISE NOTICE '✓ Created tables: characters, conversations, agents, simulation_events';
    RAISE NOTICE '✓ Seeded 3 characters: gandalf, paul_atreides, master_chief';
END $$;
