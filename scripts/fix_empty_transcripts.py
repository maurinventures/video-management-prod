#!/usr/bin/env python3
"""Set word_count to 0 for transcripts with no segments."""

import sys
from sqlalchemy import text
from db import DatabaseSession

def fix_empty_transcripts():
    """Set word_count to 0 for transcripts that have no segments."""

    update_query = """
    UPDATE transcripts
    SET word_count = 0
    WHERE word_count IS NULL
    AND status = 'completed'
    AND id NOT IN (
        SELECT DISTINCT transcript_id
        FROM transcript_segments
        WHERE transcript_id IS NOT NULL
    )
    """

    with DatabaseSession() as session:
        # Execute the update
        result = session.execute(text(update_query))
        rows_updated = result.rowcount

        print(f"✅ Set word_count to 0 for {rows_updated} empty transcripts")

        # Verify no NULL word counts remain
        check_query = "SELECT COUNT(*) FROM transcripts WHERE word_count IS NULL AND status = 'completed'"
        result = session.execute(text(check_query))
        remaining_null = result.scalar()

        print(f"📊 Remaining transcripts with NULL word_count: {remaining_null}")

        # Get final statistics
        stats_query = """
        SELECT
            COUNT(*) as total_completed,
            SUM(CASE WHEN word_count > 0 THEN 1 ELSE 0 END) as with_content,
            SUM(CASE WHEN word_count = 0 THEN 1 ELSE 0 END) as empty,
            MAX(word_count) as max_words
        FROM transcripts
        WHERE status = 'completed'
        """
        result = session.execute(text(stats_query))
        row = result.fetchone()

        print(f"\n📈 Final Statistics:")
        print(f"Total completed transcripts: {row[0]}")
        print(f"With content (word_count > 0): {row[1]}")
        print(f"Empty (word_count = 0): {row[2]}")
        print(f"Largest transcript: {row[3]:,} words")

if __name__ == "__main__":
    try:
        fix_empty_transcripts()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)