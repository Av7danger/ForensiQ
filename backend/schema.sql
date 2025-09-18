-- ForensiQ Database Schema
-- UFDR Forensic Investigation Platform

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Cases table
CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id VARCHAR(255) UNIQUE NOT NULL,
    investigator VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    description TEXT,
    metadata JSONB DEFAULT '{}'
);

-- UFDR files table
CREATE TABLE IF NOT EXISTS ufdr_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_size BIGINT NOT NULL,
    upload_path TEXT NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_status VARCHAR(50) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Contacts table
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    source_file_id UUID REFERENCES ufdr_files(id) ON DELETE CASCADE,
    contact_id VARCHAR(255),
    name VARCHAR(255),
    phone_numbers TEXT[],
    email_addresses TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    source_file_id UUID REFERENCES ufdr_files(id) ON DELETE CASCADE,
    message_id VARCHAR(255),
    thread_id VARCHAR(255),
    sender VARCHAR(255),
    recipient VARCHAR(255),
    message_type VARCHAR(50), -- SMS, chat, email, etc.
    platform VARCHAR(100), -- WhatsApp, Telegram, etc.
    content TEXT,
    timestamp_sent TIMESTAMP WITH TIME ZONE,
    timestamp_received TIMESTAMP WITH TIME ZONE,
    direction VARCHAR(20), -- incoming, outgoing
    status VARCHAR(50), -- sent, delivered, read, etc.
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Call logs table
CREATE TABLE IF NOT EXISTS call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    source_file_id UUID REFERENCES ufdr_files(id) ON DELETE CASCADE,
    call_id VARCHAR(255),
    caller VARCHAR(255),
    callee VARCHAR(255),
    call_type VARCHAR(50), -- voice, video, missed
    direction VARCHAR(20), -- incoming, outgoing
    duration_seconds INTEGER,
    timestamp_start TIMESTAMP WITH TIME ZONE,
    timestamp_end TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Attachments table
CREATE TABLE IF NOT EXISTS attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    source_file_id UUID REFERENCES ufdr_files(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    attachment_id VARCHAR(255),
    filename VARCHAR(255),
    file_type VARCHAR(100),
    file_size BIGINT,
    file_hash VARCHAR(64),
    storage_path TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Entities table (for extracted entities)
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    entity_type VARCHAR(100) NOT NULL, -- phone_number, email, url, crypto_address, etc.
    entity_value TEXT NOT NULL,
    normalized_value TEXT,
    confidence FLOAT DEFAULT 1.0,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    frequency INTEGER DEFAULT 1,
    sources JSONB DEFAULT '[]', -- Array of source references
    metadata JSONB DEFAULT '{}'
);

-- Entity occurrences (linking entities to messages/calls)
CREATE TABLE IF NOT EXISTS entity_occurrences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    source_type VARCHAR(50), -- message, call_log, contact, attachment
    source_id UUID NOT NULL,
    position_start INTEGER,
    position_end INTEGER,
    context TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings table (for semantic search)
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    source_type VARCHAR(50), -- message, contact, etc.
    source_id UUID NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    embedding vector(384), -- Adjust dimension based on model
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Search queries log
CREATE TABLE IF NOT EXISTS search_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    query_type VARCHAR(50), -- keyword, semantic, hybrid
    filters JSONB DEFAULT '{}',
    results_count INTEGER,
    execution_time_ms INTEGER,
    investigator VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Processing jobs table
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    job_type VARCHAR(100) NOT NULL, -- ufdr_parse, embedding_generation, entity_extraction
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    progress FLOAT DEFAULT 0.0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cases_case_id ON cases(case_id);
CREATE INDEX IF NOT EXISTS idx_messages_case_id ON messages(case_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp_sent);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender);
CREATE INDEX IF NOT EXISTS idx_messages_content_gin ON messages USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_contacts_case_id ON contacts(case_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_case_id ON call_logs(case_id);
CREATE INDEX IF NOT EXISTS idx_entities_case_id ON entities(case_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_value ON entities(entity_value);
CREATE INDEX IF NOT EXISTS idx_entity_occurrences_entity_id ON entity_occurrences(entity_id);
CREATE INDEX IF NOT EXISTS idx_search_queries_case_id ON search_queries(case_id);

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_cases_updated_at BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Sample data for testing (optional)
INSERT INTO cases (case_id, investigator, description) VALUES 
('CASE-2024-001', 'Detective Smith', 'Mobile device analysis for fraud investigation')
ON CONFLICT (case_id) DO NOTHING;