-- ============================================================
-- BRAHMO Governance Engine — DATABASE SCHEMA
-- Assessment 03: Cascade Health Score
-- Run this FIRST in Supabase SQL Editor, then run seed.sql
-- ============================================================

-- Clean slate (safe to re-run) ------------------------------
DROP TABLE IF EXISTS pulse_alerts CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS edges CASCADE;
DROP TABLE IF EXISTS knowledge_nodes CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS hierarchy_levels CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

-- ============================================================
-- 1. ORGANIZATIONS — top-level tenant + config
-- ============================================================
CREATE TABLE organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config JSONB DEFAULT '{}'
);

-- ============================================================
-- 2. HIERARCHY LEVELS — the knowledge "shelves" (for Coverage)
-- ============================================================
CREATE TABLE hierarchy_levels (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id),
    level_number INTEGER NOT NULL,
    level_name TEXT NOT NULL,
    department TEXT
);

-- ============================================================
-- 3. KNOWLEDGE NODES — every piece of clinical knowledge
-- ============================================================
CREATE TABLE knowledge_nodes (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id),
    hierarchy_level_id TEXT REFERENCES hierarchy_levels(id),
    type TEXT NOT NULL CHECK (type IN ('CONSTRAINT', 'DECISION', 'ANTI_PATTERN', 'FACT')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    importance DECIMAL(3,2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN (
        'ACTIVE', 'REVIEW_REQUIRED', 'SUPERSEDED', 'EXPIRED', 'LEGAL_HOLD'
    )),
    superseded_by TEXT REFERENCES knowledge_nodes(id),
    -- stores the status a node had BEFORE going on LEGAL_HOLD, so we can restore it
    prev_status TEXT,
    department TEXT,
    valid_until TIMESTAMPTZ,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4. EDGES — typed relationships between nodes
--    Cascade follows DERIVED_FROM only.
-- ============================================================
CREATE TABLE edges (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    source_id TEXT NOT NULL REFERENCES knowledge_nodes(id),
    target_id TEXT NOT NULL REFERENCES knowledge_nodes(id),
    edge_type TEXT NOT NULL CHECK (edge_type IN (
        'SUPPORTS', 'CONTRADICTS', 'SUPERSEDES', 'DERIVED_FROM', 'REQUIRES'
    )),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 5. USERS — hospital staff with roles + departments
-- ============================================================
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'HOD', 'EDITOR', 'VIEWER')),
    department TEXT NOT NULL
);

-- ============================================================
-- 6. AUDIT LOG — append-only history of every change
-- ============================================================
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    node_id TEXT REFERENCES knowledge_nodes(id),
    action TEXT NOT NULL CHECK (action IN (
        'CREATE', 'SUPERSEDE', 'STATUS_CHANGE', 'CASCADE_TRIGGER',
        'CASCADE_SKIP', 'LEGAL_HOLD', 'LEGAL_RELEASE', 'REVIEW_CONFIRMED'
    )),
    old_value TEXT,
    new_value TEXT,
    actor_id TEXT NOT NULL,
    org_id TEXT NOT NULL,
    reason TEXT,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 7. PULSE ALERTS — targeted notifications to users
-- ============================================================
CREATE TABLE pulse_alerts (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id),
    alert_type TEXT NOT NULL CHECK (alert_type IN (
        'CASCADE', 'HEALTH_DROP', 'STALE_NODE', 'REVIEW_COMPLETED'
    )),
    severity TEXT NOT NULL CHECK (severity IN ('URGENT', 'WARNING', 'INFO')),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    link TEXT,
    -- groups all alerts from one cascade event (for aggregation)
    cascade_id TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES — make cascade BFS and routing queries fast
-- ============================================================
CREATE INDEX idx_edges_target  ON edges(target_id);
CREATE INDEX idx_edges_source  ON edges(source_id);
CREATE INDEX idx_edges_type    ON edges(edge_type);
CREATE INDEX idx_nodes_status  ON knowledge_nodes(status);
CREATE INDEX idx_nodes_dept    ON knowledge_nodes(department);
CREATE INDEX idx_nodes_org     ON knowledge_nodes(org_id);
CREATE INDEX idx_audit_node    ON audit_log(node_id);
CREATE INDEX idx_audit_action  ON audit_log(action);
CREATE INDEX idx_audit_time    ON audit_log(timestamp);
CREATE INDEX idx_alerts_user   ON pulse_alerts(user_id);
CREATE INDEX idx_alerts_read   ON pulse_alerts(is_read);
CREATE INDEX idx_alerts_casc   ON pulse_alerts(cascade_id);

-- ============================================================
-- DONE. Verify with:
--   SELECT table_name FROM information_schema.tables
--   WHERE table_schema = 'public';
-- Expect 7 tables. Then run seed.sql.
-- ============================================================
