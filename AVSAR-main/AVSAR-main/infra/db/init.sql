-- Enable pgvector + trigram on first boot of the Postgres 16 data volume.
-- ARCHITECTURE.md §4: HNSW indexes on both vector columns.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS postgis;
