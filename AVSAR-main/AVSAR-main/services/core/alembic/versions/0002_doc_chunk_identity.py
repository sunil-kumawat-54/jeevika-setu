"""doc_chunks: make the identity key NULL-safe and size-safe

Two defects in the original UNIQUE (source, page, section, chunk):

1. ``section`` is nullable, and Postgres treats NULLs as distinct in a unique
   constraint — so every re-run of ``make seed`` re-inserted each NULL-section
   chunk. Observed: a 244-row corpus grew to 251 on the second load.
2. ``chunk`` holds ~2 000 characters. A btree index entry is capped near 2 704
   bytes, so a multibyte (Devanagari/Telugu) chunk could overflow the index and
   fail the insert outright.

Both are fixed with stored generated columns: ``section_key`` collapses NULL to
'' and ``chunk_sha`` reduces the body to a fixed-width digest.

Revision ID: 0002_doc_chunk_identity
Revises: 689e6d7eb5f5
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_doc_chunk_identity"
down_revision: str | None = "689e6d7eb5f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Remove rows the broken constraint already let through, keeping the lowest id.
    op.execute(
        """
        DELETE FROM doc_chunks a
        USING doc_chunks b
        WHERE a.id > b.id
          AND a.source = b.source
          AND a.page IS NOT DISTINCT FROM b.page
          AND a.section IS NOT DISTINCT FROM b.section
          AND a.chunk = b.chunk
        """
    )

    op.execute("ALTER TABLE doc_chunks DROP CONSTRAINT IF EXISTS uq_doc_chunks_identity")

    op.execute(
        "ALTER TABLE doc_chunks ADD COLUMN section_key TEXT "
        "GENERATED ALWAYS AS (COALESCE(section, '')) STORED"
    )
    op.execute(
        "ALTER TABLE doc_chunks ADD COLUMN chunk_sha TEXT "
        "GENERATED ALWAYS AS (md5(chunk)) STORED"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_doc_chunks_identity "
        "ON doc_chunks (source, page, section_key, chunk_sha)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_doc_chunks_identity")
    op.execute("ALTER TABLE doc_chunks DROP COLUMN IF EXISTS chunk_sha")
    op.execute("ALTER TABLE doc_chunks DROP COLUMN IF EXISTS section_key")
    op.execute(
        "ALTER TABLE doc_chunks ADD CONSTRAINT uq_doc_chunks_identity "
        "UNIQUE (source, page, section, chunk)"
    )
