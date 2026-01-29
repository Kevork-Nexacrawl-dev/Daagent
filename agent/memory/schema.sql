-- SQLite schema for hybrid memory system
-- Three-layer architecture: working (in-memory), episodic, semantic

-- Episodic memory: time-based conversation events
CREATE TABLE IF NOT EXISTS episodic_memory (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    content TEXT NOT NULL,
    metadata JSON,
    importance REAL DEFAULT 0.5 CHECK(importance >= 0.0 AND importance <= 1.0),
    access_count INTEGER DEFAULT 0,
    embedding_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Semantic memory: long-term facts and patterns
CREATE TABLE IF NOT EXISTS semantic_memory (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL DEFAULT 0.8 CHECK(confidence >= 0.0 AND confidence <= 1.0),
    source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    metadata JSON,
    embedding_id TEXT
);

-- Memory consolidation tracking
CREATE TABLE IF NOT EXISTS consolidation_log (
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,  -- 'extract', 'decay', 'promote'
    affected_count INTEGER DEFAULT 0,
    notes TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_episodic_session ON episodic_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_episodic_timestamp ON episodic_memory(timestamp);
CREATE INDEX IF NOT EXISTS idx_episodic_importance ON episodic_memory(importance);

CREATE INDEX IF NOT EXISTS idx_semantic_category ON semantic_memory(category);
CREATE INDEX IF NOT EXISTS idx_semantic_confidence ON semantic_memory(confidence);
CREATE INDEX IF NOT EXISTS idx_semantic_created ON semantic_memory(created_at);