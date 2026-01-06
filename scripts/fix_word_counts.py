#!/usr/bin/env python3
"""Fix word counts for all transcripts that are missing them."""

import sys
from sqlalchemy import text
from db import DatabaseSession

def fix_word_counts():
    """Calculate and update word counts for transcripts with NULL values."""

    update_query = """
    UPDATE transcripts
    SET word_count = (
        SELECT SUM(array_length(string_to_array(TRIM(text), ' '), 1))
        FROM transcript_segments
        WHERE transcript_id = transcripts.id
    )
    WHERE word_count IS NULL AND status = 'completed'
    """

    with DatabaseSession() as session:
        # Execute the update
        result = session.execute(text(update_query))
        rows_updated = result.rowcount

        print(f"✅ Updated word counts for {rows_updated} transcripts")

        # Verify the fix worked
        check_query = "SELECT COUNT(*) FROM transcripts WHERE word_count IS NULL AND status = 'completed'"
        result = session.execute(text(check_query))
        remaining_null = result.scalar()

        print(f"📊 Remaining transcripts with NULL word_count: {remaining_null}")

        # Get sample of updated word counts
        sample_query = """
        SELECT v.filename, t.word_count, t.provider
        FROM transcripts t
        JOIN videos v ON t.video_id = v.id
        WHERE t.word_count IS NOT NULL
        ORDER BY t.word_count DESC
        LIMIT 10
        """
        result = session.execute(text(sample_query))
        rows = result.fetchall()

        print("\n📋 Sample of transcripts with word counts:")
        print("Filename | Word Count | Provider")
        print("-" * 60)
        for row in rows:
            filename = row[0][:40] + "..." if len(row[0]) > 40 else row[0]
            print(f"{filename:<43} | {row[1]:>6} | {row[2]}")

if __name__ == "__main__":
    try:
        fix_word_counts()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)