import sqlite3

con = sqlite3.connect('backend/var/epi.db')
docs = con.execute("SELECT id, filename, title FROM documents").fetchall()
print(f"Total documents: {len(docs)}")

for doc_id, filename, title in docs:
    chunks = con.execute(
        "SELECT page_number, content FROM chunks WHERE document_id = ? LIMIT 2", (doc_id,)
    ).fetchall()
    print(f"\nDoc {filename} ({title}):")
    for page_num, content in chunks:
        preview = content[:150].replace('\n', ' ')
        print(f"  [p.{page_num}] {preview}...")

suppliers = con.execute("SELECT id, name, legal_name, country FROM suppliers").fetchall()
print(f"\nSuppliers ({len(suppliers)}):")
for s in suppliers:
    print(" ", s)

contracts = con.execute("SELECT contract_number, title, value, currency, supplier_id FROM contracts").fetchall()
print(f"\nContracts ({len(contracts)}):")
for c in contracts:
    print(" ", c)

prices = con.execute("SELECT product_name, unit_price, currency, supplier_name FROM prices").fetchall()
print(f"\nPrices ({len(prices)}):")
for p in prices[:6]:
    print(" ", p)
