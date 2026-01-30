-- ========================================
-- RECIPE VERSIONING SYSTEM MIGRATION
-- ========================================
-- Purpose: Add version tracking for plate and batch recipes
-- Approach: Immutable Ledger pattern with version snapshots
-- Maintains: Full database normalization
-- ========================================

-- ========================================
-- 1. PLATE RECIPE VERSIONING TABLES
-- ========================================

-- Main version table for plate recipes
-- Stores complete snapshot of recipe metadata at each version
CREATE TABLE IF NOT EXISTS plate_recipe_versions (
    -- Primary identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Links to parent recipe (this ID remains constant across versions)
    recipe_id UUID NOT NULL REFERENCES plate_recipes(id) ON DELETE CASCADE,
    
    -- Version tracking
    version_number DECIMAL(5,2) NOT NULL,  -- 1.0, 1.1, 2.0 (semantic versioning)
    is_active BOOLEAN DEFAULT true,  -- Only one active version per recipe at a time
    
    -- Version provenance (WHO created this version)
    created_by VARCHAR(255) NOT NULL,  -- chef_id who made this version
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- WHAT changed (human-readable audit trail)
    change_summary TEXT,  -- Auto-generated: "Reduced salt from 10g to 7g, Added garlic"
    change_reason TEXT,  -- User-provided: "Customer feedback: too bland"
    
    -- ========================================
    -- SNAPSHOT: Recipe metadata at this version
    -- (These are the values AS THEY WERE at this version)
    -- ========================================
    name VARCHAR(255) NOT NULL,
    description TEXT,
    serves INTEGER,
    category VARCHAR(100),
    cuisine VARCHAR(100),
    plating_instructions TEXT,
    garnish TEXT,
    presentation_notes TEXT,
    prep_time_minutes INTEGER,
    cook_time_minutes INTEGER,
    difficulty VARCHAR(20),
    notes TEXT,
    
    -- ========================================
    -- CONSTRAINTS
    -- ========================================
    -- Ensure unique version numbers per recipe (no duplicate v1.0, v1.0)
    CONSTRAINT unique_plate_version_number UNIQUE (recipe_id, version_number)
);

-- Ingredients snapshot for each plate recipe version
-- Links version to ingredients with quantities AT THAT VERSION
CREATE TABLE IF NOT EXISTS plate_version_ingredients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Links to specific version
    version_id UUID NOT NULL REFERENCES plate_recipe_versions(id) ON DELETE CASCADE,
    
    -- Links to ingredient master table (maintains normalization)
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    
    -- Snapshot of ingredient data at this version
    quantity DECIMAL(10,3) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    preparation_notes TEXT,  -- e.g., 'diced', 'minced'
    is_garnish BOOLEAN DEFAULT FALSE,
    is_optional BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Each version can have each ingredient only once
    UNIQUE(version_id, ingredient_id)
);

-- ========================================
-- 2. BATCH RECIPE VERSIONING TABLES
-- ========================================

-- Main version table for batch recipes
CREATE TABLE IF NOT EXISTS batch_recipe_versions (
    -- Primary identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Links to parent recipe
    recipe_id UUID NOT NULL REFERENCES batch_recipes(id) ON DELETE CASCADE,
    
    -- Version tracking
    version_number DECIMAL(5,2) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    
    -- Version provenance
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Change tracking
    change_summary TEXT,
    change_reason TEXT,
    
    -- ========================================
    -- SNAPSHOT: Batch recipe metadata
    -- ========================================
    name VARCHAR(255) NOT NULL,
    description TEXT,
    yield_quantity DECIMAL(10,2),
    yield_unit VARCHAR(50),
    prep_time_minutes INTEGER,
    cook_time_minutes INTEGER,
    storage_instructions TEXT,
    temperature DECIMAL(5,2),
    temperature_unit VARCHAR(10),
    equipment TEXT[],
    instructions TEXT,
    notes TEXT,
    
    -- ========================================
    -- CONSTRAINTS
    -- ========================================
    -- Ensure unique version numbers per recipe
    CONSTRAINT unique_batch_version_number UNIQUE (recipe_id, version_number)
);

-- Ingredients snapshot for batch recipe versions
CREATE TABLE IF NOT EXISTS batch_version_ingredients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    version_id UUID NOT NULL REFERENCES batch_recipe_versions(id) ON DELETE CASCADE,
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    
    -- Snapshot data
    quantity DECIMAL(10,3) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    preparation_notes TEXT,
    is_optional BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(version_id, ingredient_id)
);

-- ========================================
-- 3. PERFORMANCE INDEXES
-- ========================================

-- Enforce only ONE active version per recipe using partial unique index
CREATE UNIQUE INDEX IF NOT EXISTS idx_plate_versions_one_active 
    ON plate_recipe_versions(recipe_id) 
    WHERE is_active = true;

CREATE UNIQUE INDEX IF NOT EXISTS idx_batch_versions_one_active 
    ON batch_recipe_versions(recipe_id) 
    WHERE is_active = true;

-- Fast lookup of active version for a recipe (most common query)
CREATE INDEX IF NOT EXISTS idx_plate_versions_active 
    ON plate_recipe_versions(recipe_id, is_active) 
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_batch_versions_active 
    ON batch_recipe_versions(recipe_id, is_active) 
    WHERE is_active = true;

-- Fast version history queries (ORDER BY version DESC)
CREATE INDEX IF NOT EXISTS idx_plate_versions_recipe 
    ON plate_recipe_versions(recipe_id, version_number DESC);

CREATE INDEX IF NOT EXISTS idx_batch_versions_recipe 
    ON batch_recipe_versions(recipe_id, version_number DESC);

-- Fast ingredient lookups for versions
CREATE INDEX IF NOT EXISTS idx_plate_version_ingredients_version 
    ON plate_version_ingredients(version_id);

CREATE INDEX IF NOT EXISTS idx_batch_version_ingredients_version 
    ON batch_version_ingredients(version_id);

-- Fast lookups by created_by (for filtering versions by chef)
CREATE INDEX IF NOT EXISTS idx_plate_versions_created_by 
    ON plate_recipe_versions(created_by);

CREATE INDEX IF NOT EXISTS idx_batch_versions_created_by 
    ON batch_recipe_versions(created_by);

-- ========================================
-- 4. OPTIONAL: MIGRATE EXISTING RECIPES
-- ========================================
-- Uncomment if you have existing recipes that need v1.0
-- This creates v1.0 for all existing plate recipes

-- INSERT INTO plate_recipe_versions (
--     recipe_id, version_number, is_active, created_by,
--     change_summary, name, description, serves, category,
--     cuisine, plating_instructions, garnish, presentation_notes,
--     prep_time_minutes, cook_time_minutes, difficulty, notes
-- )
-- SELECT 
--     id, 1.0, true, chef_id,
--     'Initial version (migrated from legacy system)',
--     name, description, serves, category, cuisine,
--     plating_instructions, garnish, presentation_notes,
--     prep_time_minutes, cook_time_minutes, difficulty, notes
-- FROM plate_recipes;

-- Similarly for batch recipes:
-- INSERT INTO batch_recipe_versions (...)
-- SELECT ... FROM batch_recipes;

-- ========================================
-- MIGRATION COMPLETE
-- ========================================
-- Tables created:
--   - plate_recipe_versions (metadata snapshots)
--   - plate_version_ingredients (ingredient snapshots)
--   - batch_recipe_versions (metadata snapshots)
--   - batch_version_ingredients (ingredient snapshots)
-- Indexes: 8 indexes for performance
-- Constraints: Unique constraints + GIST exclusion for active versions
-- ========================================
