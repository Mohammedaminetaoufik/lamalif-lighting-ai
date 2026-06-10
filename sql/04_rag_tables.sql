-- ============================================================
-- RAG Tables — Smart Lighting AI Service
-- Version JSONB stable (sans pgvector)
-- Compatible PostgreSQL 14+ sans extension
-- ============================================================

-- ── Documents sources RAG ────────────────────────────────────
CREATE TABLE IF NOT EXISTS rag_documents (
    id           SERIAL PRIMARY KEY,
    title        TEXT    NOT NULL,
    source_type  TEXT    NOT NULL,
    source_path  TEXT,
    content      TEXT    NOT NULL,
    content_hash TEXT    NOT NULL,
    metadata     JSONB   DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(title, source_type)
);

-- ── Chunks avec embeddings JSONB ─────────────────────────────
-- La colonne embedding_json stocke le vecteur sous forme de tableau JSON
-- La similarité cosine est calculée côté Python (numpy)
CREATE TABLE IF NOT EXISTS rag_chunks (
    id             SERIAL  PRIMARY KEY,
    document_id    INT     REFERENCES rag_documents(id) ON DELETE CASCADE,
    chunk_index    INT     NOT NULL,
    content        TEXT    NOT NULL,
    content_hash   TEXT    NOT NULL,
    embedding_json JSONB,
    metadata       JSONB   DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);

-- ── Index standard ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_rag_documents_source_type
    ON rag_documents(source_type);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_document_id
    ON rag_chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_metadata
    ON rag_chunks USING GIN(metadata);

-- ── Droits ai_readonly (lecture) ─────────────────────────────
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_readonly') THEN
        EXECUTE 'GRANT SELECT ON rag_documents TO ai_readonly';
        EXECUTE 'GRANT SELECT ON rag_chunks TO ai_readonly';
        RAISE NOTICE 'Droits SELECT accordés à ai_readonly.';
    ELSE
        RAISE NOTICE 'ATTENTION : rôle ai_readonly inexistant — droits non accordés.';
    END IF;
END $$;

-- ── Droits ai_logger (écriture) ──────────────────────────────
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_logger') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON rag_documents TO ai_logger';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON rag_chunks TO ai_logger';
        EXECUTE 'GRANT USAGE, SELECT ON SEQUENCE rag_documents_id_seq TO ai_logger';
        EXECUTE 'GRANT USAGE, SELECT ON SEQUENCE rag_chunks_id_seq TO ai_logger';
        RAISE NOTICE 'Droits CRUD accordés à ai_logger.';
    ELSE
        RAISE NOTICE 'ATTENTION : rôle ai_logger inexistant — droits non accordés.';
    END IF;
END $$;

-- ── Colonnes observabilité dans ai_query_logs (optionnel) ─────
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_query_logs') THEN
        -- Ajouter les colonnes RAG seulement si ai_query_logs existe
        BEGIN
            ALTER TABLE ai_query_logs ADD COLUMN IF NOT EXISTS rag_used         BOOLEAN DEFAULT false;
            ALTER TABLE ai_query_logs ADD COLUMN IF NOT EXISTS rag_chunks_count INT     DEFAULT 0;
            ALTER TABLE ai_query_logs ADD COLUMN IF NOT EXISTS rag_sources      JSONB   DEFAULT '[]'::jsonb;
            RAISE NOTICE 'Colonnes RAG ajoutées à ai_query_logs.';
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Impossible d''ajouter les colonnes RAG à ai_query_logs : %', SQLERRM;
        END;
    ELSE
        RAISE NOTICE 'Table ai_query_logs non trouvée — colonnes RAG non ajoutées.';
    END IF;
END $$;

-- ============================================================
-- Vérification finale
-- ============================================================
DO $$
DECLARE
    doc_exists   BOOLEAN;
    chunk_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'rag_documents'
    ) INTO doc_exists;

    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'rag_chunks'
    ) INTO chunk_exists;

    IF doc_exists THEN
        RAISE NOTICE 'OK : rag_documents existe.';
    ELSE
        RAISE WARNING 'ERREUR : rag_documents manquante !';
    END IF;

    IF chunk_exists THEN
        RAISE NOTICE 'OK : rag_chunks existe.';
    ELSE
        RAISE WARNING 'ERREUR : rag_chunks manquante !';
    END IF;

    RAISE NOTICE 'Mode : JSONB (pas de pgvector requis).';
    RAISE NOTICE 'Pour activer pgvector, exécuter : sql/04_rag_tables_pgvector.sql';
END $$;
