-- =============================================================================
-- Ad Studio Database Schema & Migration for Supabase PostgreSQL
-- Run this script in the Supabase SQL Editor:
-- https://supabase.com/dashboard/project/mtwmemljlnoivdnstqbx/sql/new
-- =============================================================================

-- 1. Create or update saved_creatives table
CREATE TABLE IF NOT EXISTS public.saved_creatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    user_email TEXT,
    type TEXT NOT NULL DEFAULT 'image',
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    media_url TEXT NOT NULL,
    aspect_ratio TEXT DEFAULT '9:16',
    model_params JSONB DEFAULT '{}'::jsonb,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    reference_images JSONB DEFAULT '[]'::jsonb,
    folder_id TEXT DEFAULT '',
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ensure all new columns exist on existing table instances
ALTER TABLE public.saved_creatives ADD COLUMN IF NOT EXISTS reference_images JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.saved_creatives ADD COLUMN IF NOT EXISTS folder_id TEXT DEFAULT '';
ALTER TABLE public.saved_creatives ADD COLUMN IF NOT EXISTS user_email TEXT;
ALTER TABLE public.saved_creatives ADD COLUMN IF NOT EXISTS aspect_ratio TEXT DEFAULT '9:16';
ALTER TABLE public.saved_creatives ADD COLUMN IF NOT EXISTS model_params JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.saved_creatives ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT ARRAY[]::TEXT[];
ALTER TABLE public.saved_creatives ADD COLUMN IF NOT EXISTS is_favorite BOOLEAN DEFAULT FALSE;

-- 2. Create projects / folders table for asset management
CREATE TABLE IF NOT EXISTS public.projects (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id UUID,
    user_email TEXT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    color TEXT DEFAULT '#8d3624',
    icon TEXT DEFAULT 'folder',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. High-performance indexes
CREATE INDEX IF NOT EXISTS idx_saved_creatives_user ON public.saved_creatives(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_creatives_email ON public.saved_creatives(user_email);
CREATE INDEX IF NOT EXISTS idx_saved_creatives_created ON public.saved_creatives(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_saved_creatives_folder ON public.saved_creatives(folder_id);
CREATE INDEX IF NOT EXISTS idx_saved_creatives_fav ON public.saved_creatives(is_favorite);

CREATE INDEX IF NOT EXISTS idx_projects_user ON public.projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_email ON public.projects(user_email);
CREATE INDEX IF NOT EXISTS idx_projects_updated ON public.projects(updated_at DESC);

-- 4. Enable Row Level Security (RLS)
ALTER TABLE public.saved_creatives ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

-- 5. Permissive policies for full CRUD access
-- Service Role: Full access for server-side operations
DROP POLICY IF EXISTS "Allow service_role full access saved_creatives" ON public.saved_creatives;
CREATE POLICY "Allow service_role full access saved_creatives" ON public.saved_creatives
    FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow service_role full access projects" ON public.projects;
CREATE POLICY "Allow service_role full access projects" ON public.projects
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Authenticated Users: Read and write access
DROP POLICY IF EXISTS "Allow authenticated full access saved_creatives" ON public.saved_creatives;
CREATE POLICY "Allow authenticated full access saved_creatives" ON public.saved_creatives
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow authenticated full access projects" ON public.projects;
CREATE POLICY "Allow authenticated full access projects" ON public.projects
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- Anonymous Users: Read and write access (supports guest generations)
DROP POLICY IF EXISTS "Allow anon full access saved_creatives" ON public.saved_creatives;
CREATE POLICY "Allow anon full access saved_creatives" ON public.saved_creatives
    FOR ALL TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow anon full access projects" ON public.projects;
CREATE POLICY "Allow anon full access projects" ON public.projects
    FOR ALL TO anon USING (true) WITH CHECK (true);
