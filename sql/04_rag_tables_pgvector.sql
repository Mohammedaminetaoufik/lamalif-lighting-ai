-- ============================================================
-- RAG Tables — Extension pgvector (optionnel)
-- À exécuter APRÈS 04_rag_tables.sql si pgvector est installé
-- Nécessite : postgresql-pgvector ou pgvector compilé
-- ============================================================

-- Activer l'extension pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Ajouter la colonne vector(384) si pgvector est disponible
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        -- Ajouter la colonne embedding uniquement si elle n'existe pas
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'rag_chunks' AND column_name = 'embedding'
        ) THEN
            ALTER TABLE rag_chunks ADD COLUMN embedding vector(384);
            RAISE NOTICE 'Colonne embedding vector(384) ajoutée à rag_chunks.';
        ELSE
            RAISE NOTICE 'Colonne embedding déjà présente.';
        END IF;

        -- Créer l'index ivfflat cosine (nécessite au moins quelques lignes dans la table)
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding_cosine
                 ON rag_chunks USING ivfflat (embedding vector_cosine_ops)
                 WITH (lists = 50)';
        RAISE NOTICE 'Index ivfflat cosine créé.';
        RAISE NOTICE 'pgvector activé — changer RAG_BACKEND=pgvector dans .env';
    ELSE
        RAISE WARNING 'pgvector non disponible. Restez en RAG_BACKEND=jsonb.';
    END IF;
END $$;
