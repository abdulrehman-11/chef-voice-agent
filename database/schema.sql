-- Database Schema for Chef Voice AI Agent
-- Supports Many-to-Many relationships: Ingredients <-> Batch Recipes <-> Plate Recipes

-- Enable required extensions first
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For full-text search

-- Ingredients Table
CREATE TABLE IF NOT EXISTS ingredients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chef_id VARCHAR(255) NOT NULL,  -- For multi-tenant support
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(50),  -- e.g., 'grams', 'ml', 'cups', 'each'
    category VARCHAR(100),  -- e.g., 'vegetable', 'protein', 'spice', 'dairy'
    allergens TEXT[],  -- Array of allergens (e.g., {'gluten', 'dairy'})
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Batch Recipes Table (Large scale components)
CREATE TABLE IF NOT EXISTS batch_recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chef_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    yield_quantity DECIMAL(10,2),  -- e.g., 5000 for 5kg
    yield_unit VARCHAR(50),  -- e.g., 'grams', 'liters'
    prep_time_minutes INTEGER,
    cook_time_minutes INTEGER,
    storage_instructions TEXT,
    temperature DECIMAL(5,2),  -- Cooking/storage temperature
    temperature_unit VARCHAR(10) DEFAULT 'C',  -- 'C' or 'F'
    equipment TEXT[],  -- Array of equipment needed
    instructions TEXT,  -- Step-by-step instructions
    notes TEXT,
    is_complete BOOLEAN DEFAULT FALSE,  -- Draft status
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Plate Recipes Table (Final plated dishes)
CREATE TABLE IF NOT EXISTS plate_recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chef_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    serves INTEGER,  -- Number of servings
    category VARCHAR(100),  -- e.g., 'appetizer', 'main', 'dessert'
    cuisine VARCHAR(100),  -- e.g., 'Italian', 'French', 'Asian'
    plating_instructions TEXT,
    garnish TEXT,
    presentation_notes TEXT,
    prep_time_minutes INTEGER,
    cook_time_minutes INTEGER,
    difficulty VARCHAR(20),  -- e.g., 'easy', 'medium', 'hard'
    notes TEXT,
    is_complete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Junction Table: Batch Recipes <-> Ingredients (Many-to-Many)
CREATE TABLE IF NOT EXISTS batch_ingredients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_recipe_id UUID NOT NULL REFERENCES batch_recipes(id) ON DELETE CASCADE,
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    quantity DECIMAL(10,3) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    preparation_notes TEXT,  -- e.g., 'diced', 'minced', 'blanched'
    is_optional BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(batch_recipe_id, ingredient_id)
);

-- Junction Table: Plate Recipes <-> Batch Recipes (Many-to-Many)
CREATE TABLE IF NOT EXISTS plate_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plate_recipe_id UUID NOT NULL REFERENCES plate_recipes(id) ON DELETE CASCADE,
    batch_recipe_id UUID NOT NULL REFERENCES batch_recipes(id) ON DELETE CASCADE,
    quantity DECIMAL(10,3) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    assembly_order INTEGER,  -- Order of assembly
    preparation_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(plate_recipe_id, batch_recipe_id)
);

-- Junction Table: Plate Recipes <-> Ingredients (Many-to-Many)
-- For direct ingredients (not part of a batch)
CREATE TABLE IF NOT EXISTS plate_ingredients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plate_recipe_id UUID NOT NULL REFERENCES plate_recipes(id) ON DELETE CASCADE,
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    quantity DECIMAL(10,3) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    preparation_notes TEXT,
    is_garnish BOOLEAN DEFAULT FALSE,  -- Distinguish garnish from main ingredients
    is_optional BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(plate_recipe_id, ingredient_id)
);

-- Conversations Table (Session tracking for resuming)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chef_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    current_context JSONB,  -- Store current working recipe draft
    message_history JSONB,  -- Store conversation turns for context
    status VARCHAR(50) DEFAULT 'active',  -- 'active', 'paused', 'completed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_ingredients_chef_id ON ingredients(chef_id);
CREATE INDEX IF NOT EXISTS idx_ingredients_name ON ingredients(name);
CREATE INDEX IF NOT EXISTS idx_batch_recipes_chef_id ON batch_recipes(chef_id);
CREATE INDEX IF NOT EXISTS idx_batch_recipes_name ON batch_recipes(name);
CREATE INDEX IF NOT EXISTS idx_plate_recipes_chef_id ON plate_recipes(chef_id);
CREATE INDEX IF NOT EXISTS idx_plate_recipes_name ON plate_recipes(name);
CREATE INDEX IF NOT EXISTS idx_conversations_chef_id ON conversations(chef_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_batch_recipes_name_trgm ON batch_recipes USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_plate_recipes_name_trgm ON plate_recipes USING gin(name gin_trgm_ops);

-- Trigger to auto-update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at column
CREATE TRIGGER update_ingredients_updated_at BEFORE UPDATE ON ingredients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_batch_recipes_updated_at BEFORE UPDATE ON batch_recipes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_plate_recipes_updated_at BEFORE UPDATE ON plate_recipes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
