import sqlite3

conn = sqlite3.connect('var/eval-v2/eval.db')
cur = conn.cursor()

print('Total chunks:', cur.execute('SELECT COUNT(*) FROM chunks').fetchone()[0])
print('\nSample chunks:')
rows = cur.execute('SELECT id, document_id, page_number, content_type FROM chunks LIMIT 10').fetchall()
for row in rows:
    print(f"  {row[0][:20]}... doc={row[1][:20]}... page={row[2]} type={row[3]}")

print('\nContent types:')
types = cur.execute('SELECT content_type, COUNT(*) FROM chunks GROUP BY content_type').fetchall()
for t in types:
    print(f"  {t[0]}: {t[1]}")

conn.close()
