"""Check current state."""
import sqlite3

conn = sqlite3.connect('./var/epi.db')
cursor = conn.cursor()

# Check migration version
result = cursor.execute("SELECT version_num FROM alembic_version").fetchone()
print(f"Migration version: {result[0] if result else 'NONE'}")

# Check schema has new fields
result = cursor.execute("""
    SELECT name FROM pragma_table_info('documents')
    WHERE name IN ('active_indexing_version', 'candidate_indexing_version')
""").fetchall()
print(f"Documents version fields: {[r[0] for r in result]}")

result = cursor.execute("""
    SELECT name FROM pragma_table_info('chunks')  
    WHERE name IN ('indexing_version', 'is_active')
""").fetchall()
print(f"Chunks version fields: {[r[0] for r in result]}")

result = cursor.execute("""
    SELECT name FROM pragma_table_info('ingestion_jobs')
    WHERE name IN ('indexing_version', 'checkpoint', 'checkpoint_metadata')
""").fetchall()
print(f"Ingestion_jobs fields: {[r[0] for r in result]}")

conn.close()
