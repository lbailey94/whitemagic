
with open("scripts/execute_v19_c1_dedup.py") as f:
    content = f.read()

content = content.replace(
    """    for dup in exact_duplicates:
        ids = dup['ids'].split(',')
        if len(ids) < 2: continue

        # Keep the one with highest importance/access count
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f\"\"\"
            SELECT id FROM memories
            WHERE id IN ({placeholders})
            ORDER BY importance DESC, access_count DESC, created_at DESC
        \"\"\", ids)

        sorted_ids = [row['id'] for row in cursor.fetchall()]
        keeper = sorted_ids[0]
        to_archive = sorted_ids[1:]

        for arch_id in to_archive:
            cursor.execute(\"\"\"
                UPDATE memories
                SET memory_type = 'quarantined',
                    title = '[DEDUP] ' || title
                WHERE id = ?
            \"\"\", (arch_id,))
            archived += 1

        resolved += 1""",
    """    # Process both exact and near duplicates
    all_duplicate_groups = [dup['ids'].split(',') for dup in exact_duplicates] + [dup['ids'].split(',') for dup in near_duplicates]

    for ids in all_duplicate_groups:
        if len(ids) < 2: continue

        # Keep the one with highest importance/access count
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f\"\"\"
            SELECT id FROM memories
            WHERE id IN ({placeholders})
            ORDER BY importance DESC, access_count DESC, created_at DESC
        \"\"\", ids)

        sorted_ids = [row['id'] for row in cursor.fetchall()]
        if not sorted_ids: continue

        keeper = sorted_ids[0]
        to_archive = sorted_ids[1:]

        for arch_id in to_archive:
            cursor.execute(\"\"\"
                UPDATE memories
                SET memory_type = 'quarantined',
                    title = '[DEDUP] ' || title
                WHERE id = ?
            \"\"\", (arch_id,))
            archived += 1

        resolved += 1"""
)

with open("scripts/execute_v19_c1_dedup.py", "w") as f:
    f.write(content)
