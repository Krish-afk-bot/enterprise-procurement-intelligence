# 2026 UK FTS Dataset: Ingestion Design

**Design Date:** 2026-11-05  
**Target Database:** EPI PostgreSQL  
**Source Files:** `2026.jsonl` (primary), `2026/*.csv` (validation only)  
**Expected Records:** 68,473 OCDS releases → ~150,000+ database records

---

## Ingestion Goals

1. **Import all 68,473 procurement releases** from UK FTS 2026 dataset
2. **Preserve complete OCDS structure** in `raw` fields for audit trail
3. **Create queryable entities:** Suppliers, Awards (as ProcurementRecords), Contracts
4. **Maintain data provenance:** Track source, OCID, retrieval date
5. **Avoid data loss:** No information discarded during transformation
6. **Enable validation:** Cross-check counts against CSV files
7. **Support rollback:** Tag records for bulk removal if needed

---

## Data Flow

```
2026.jsonl (68,473 releases)
    ↓
[Parse JSONL] → OCDS Release Objects
    ↓
[Extract Parties] → Create/Update Suppliers
    ↓
[Extract Awards] → Create ProcurementRecords
    ↓
[Extract Contracts] → Create Contracts (linked to Suppliers)
    ↓
[Extract Documents] → Store metadata (URLs only, no downloads)
    ↓
[Validation] → Cross-check counts vs CSV files
    ↓
EPI Database (suppliers, procurement_records, contracts)
```

---

## Entity Extraction Strategy

### 1. Suppliers (from `parties`)

**Source:** `release.parties[]` where `roles` includes `"supplier"` or `"tenderer"`

**Logic:**
```python
for release in jsonl_releases:
    for party in release.get('parties', []):
        if 'supplier' in party.get('roles', []):
            supplier = create_or_update_supplier(party)
```

**Deduplication:** By `party.id` (GB-FTS identifier)

**Mapping:**
```python
{
    'id': generate_id('sup'),
    'name': party['name'],
    'normalized_name': normalize(party['name']),
    'country': party.get('address', {}).get('countryName'),
    'region': party.get('address', {}).get('region'),
    'contact_email': party.get('contactPoint', {}).get('email'),
    'status': 'active',
    'is_synthetic': False,
    'attributes': {
        'gb_fts_id': party['id'],
        'identifier': party.get('identifier'),
        'roles': party.get('roles'),
        'address': party.get('address')
    },
    'source_system': 'uk-fts-2026',
    'source_id': party['id']
}
```

**Expected Count:** ~79,949 unique parties, ~15,000-20,000 suppliers

---

### 2. Procurement Records (from `awards`)

**Source:** `release.awards[]`

**Logic:**
```python
for release in jsonl_releases:
    buyer = release.get('buyer', {})
    
    for award in release.get('awards', []):
        # One ProcurementRecord per award
        record = create_procurement_record(release, award, buyer)
```

**One record per award** (not per award item)

**Mapping:**
```python
{
    'id': generate_id('rec'),
    'buyer': buyer.get('name'),
    'supplier_name': award['suppliers'][0]['name'] if award.get('suppliers') else None,
    'supplier_id': lookup_supplier_by_gb_fts_id(award['suppliers'][0]['id']),
    'contract_id': None,  # Populated later when linking contracts
    'product_name': award.get('title') or extract_first_item_description(award),
    'category': extract_classification(award),
    'quantity': extract_quantity(award),
    'unit_price': calculate_unit_price(award),
    'value': award.get('value', {}).get('amount'),
    'currency': award.get('value', {}).get('currency', 'GBP'),
    'award_date': parse_date(award.get('date')),
    'region': extract_region_from_parties(release, award),
    'raw': award,  # Full award object
    'is_synthetic': False,
    'source_system': 'uk-fts-2026',
    'source_id': release['ocid'],
    'source_url': f"https://www.find-tender.service.gov.uk/Notice/{release['ocid']}"
}
```

**Expected Count:** ~84,491 (from awards.csv row count)

---

### 3. Contracts (from `contracts`)

**Source:** `release.contracts[]`

**Logic:**
```python
for release in jsonl_releases:
    for contract in release.get('contracts', []):
        # Lookup related award to find supplier
        award = find_award_by_id(release, contract.get('awardID'))
        supplier_id = lookup_supplier_from_award(award)
        
        record = create_contract(release, contract, supplier_id)
```

**Mapping:**
```python
{
    'id': generate_id('ctr'),
    'supplier_id': supplier_id,  # From award lookup
    'contract_number': contract['id'],
    'title': contract.get('title') or award.get('title'),
    'contract_type': None,  # Not in OCDS
    'category': extract_classification(contract or award),
    'currency': contract.get('value', {}).get('currency', 'GBP'),
    'total_value': contract.get('value', {}).get('amount'),
    'effective_date': parse_date(contract.get('period', {}).get('startDate')),
    'expiry_date': parse_date(contract.get('period', {}).get('endDate')),
    'status': contract.get('status', 'unknown'),
    'version': 1,
    'is_synthetic': False,
    'metadata_json': {
        'ocid': release['ocid'],
        'award_id': contract.get('awardID'),
        'description': contract.get('description'),
        'period': contract.get('period')
    },
    'source_system': 'uk-fts-2026',
    'source_id': f"{release['ocid']}-{contract['id']}"
}
```

**Expected Count:** ~70,470 (from contracts.csv row count)

---

## Field Extraction Helpers

### Classification Extraction
```python
def extract_classification(award_or_contract):
    """Extract CPV or other classification as category"""
    items = award_or_contract.get('items', [])
    if items and items[0].get('classification'):
        return items[0]['classification'].get('description')
    return None
```

### Region Extraction
```python
def extract_region_from_parties(release, award):
    """Get supplier region from parties list"""
    if not award.get('suppliers'):
        return None
    
    supplier_id = award['suppliers'][0]['id']
    
    for party in release.get('parties', []):
        if party.get('id') == supplier_id:
            return party.get('address', {}).get('region')
    
    return None
```

### Quantity Extraction
```python
def extract_quantity(award):
    """Sum quantities from award items"""
    total_qty = 0
    for item in award.get('items', []):
        qty = item.get('quantity', 0)
        if qty:
            total_qty += qty
    return total_qty if total_qty > 0 else None
```

### Unit Price Calculation
```python
def calculate_unit_price(award):
    """Calculate unit price if value and quantity available"""
    value = award.get('value', {}).get('amount')
    quantity = extract_quantity(award)
    
    if value and quantity and quantity > 0:
        return value / quantity
    
    return None
```

---

## Deduplication Strategy

### Supplier Deduplication

**Key:** `party.id` (GB-FTS identifier like `"GB-FTS-64724"`)

**Logic:**
```python
supplier_cache = {}  # gb_fts_id -> epi_supplier_id

def get_or_create_supplier(party):
    gb_fts_id = party['id']
    
    if gb_fts_id in supplier_cache:
        return supplier_cache[gb_fts_id]
    
    # Check database
    existing = db.query(Supplier).filter(
        Supplier.attributes['gb_fts_id'].astext == gb_fts_id
    ).first()
    
    if existing:
        supplier_cache[gb_fts_id] = existing.id
        return existing.id
    
    # Create new
    new_supplier = create_supplier(party)
    supplier_cache[gb_fts_id] = new_supplier.id
    return new_supplier.id
```

### Award Deduplication

**Key:** `ocid + award.id`

**Logic:** Awards should be unique per release. No deduplication needed if processing each release once.

### Contract Deduplication

**Key:** `ocid + contract.id`

**Logic:** Contracts should be unique per release. No deduplication needed.

---

## Database Transaction Strategy

### Batch Size: 1000 releases per transaction

**Rationale:**
- Large enough for efficiency
- Small enough to allow rollback on error
- Enables progress checkpointing

### Commit Strategy

```python
def ingest_batch(releases, start_idx):
    with db.session.begin():
        for idx, release in enumerate(releases):
            try:
                # Extract and insert entities
                process_release(release)
                
                if (idx + 1) % 100 == 0:
                    logger.info(f"Processed {start_idx + idx + 1} releases...")
            
            except Exception as e:
                logger.error(f"Failed on release {release['ocid']}: {e}")
                # Store failed OCID
                failed_ocids.append(release['ocid'])
                continue
        
        # Commit batch
        db.session.flush()
        logger.info(f"Committed batch {start_idx} - {start_idx + len(releases)}")
```

### Checkpoint Files

Save progress after each batch:
```json
{
  "last_completed_line": 1000,
  "last_ocid": "ocds-h6vhtk-028e6c",
  "records_created": {
    "suppliers": 245,
    "procurement_records": 780,
    "contracts": 650
  },
  "failed_ocids": ["ocds-h6vhtk-abc123"]
}
```

**Enables:** Resume from checkpoint on failure

---

## Error Handling

### Record-Level Errors

**Strategy:** Log and skip, don't fail batch

**Errors to catch:**
- Missing required fields (buyer, supplier)
- Invalid date formats
- Negative values
- Invalid OCID format
- Supplier lookup failures

**Logging:**
```python
{
  "ocid": "ocds-h6vhtk-028e6c",
  "error_type": "missing_supplier",
  "error_message": "Award has no suppliers array",
  "award_id": "029319-2024-3525889-1"
}
```

### Batch-Level Errors

**Strategy:** Rollback transaction, log failure, continue with next batch

### Fatal Errors

**Strategy:** Stop ingestion, preserve checkpoint, report to user

**Fatal conditions:**
- Database connection lost
- Disk space exhausted
- Invalid JSONL format (corrupted file)

---

## Validation Strategy

### Pre-Ingestion Validation

1. **File integrity:** Verify JSONL parses completely
2. **Count check:** Verify 68,473 lines
3. **OCID uniqueness:** Verify no duplicate OCIDs
4. **Schema validation:** Verify all releases have required fields

### During Ingestion Validation

1. **Supplier resolution:** Track failed supplier lookups
2. **Award-contract links:** Track orphaned contracts
3. **Value ranges:** Flag suspiciously high/low values
4. **Date ranges:** Flag dates outside 2026

### Post-Ingestion Validation

Compare database counts against CSV files:

| Entity | JSONL Source | CSV Validation | Database Count | Match? |
|--------|--------------|----------------|----------------|--------|
| Releases | 68,473 | main.csv: 68,473 | - | ✓ |
| Suppliers | ~79,949 parties | parties.csv: 198,747 rows | ? | ? |
| Awards | 51,985 releases | awards.csv: 84,491 | ? | ? |
| Contracts | 43,873 releases | contracts.csv: 70,470 | ? | ? |

**Validation queries:**
```sql
-- Count procurement records by source
SELECT COUNT(*) FROM procurement_records 
WHERE source_system = 'uk-fts-2026';

-- Count suppliers by source
SELECT COUNT(*) FROM suppliers 
WHERE source_system = 'uk-fts-2026';

-- Count contracts by source
SELECT COUNT(*) FROM contracts 
WHERE source_system = 'uk-fts-2026';

-- Verify currency
SELECT currency, COUNT(*) FROM procurement_records 
WHERE source_system = 'uk-fts-2026' 
GROUP BY currency;

-- Verify date range
SELECT MIN(award_date), MAX(award_date) 
FROM procurement_records 
WHERE source_system = 'uk-fts-2026';
```

---

## Progress Monitoring

### Console Output
```
[2026-11-05 10:15:32] Starting UK FTS 2026 ingestion...
[2026-11-05 10:15:33] Loaded 68,473 releases from 2026.jsonl
[2026-11-05 10:15:45] Batch 1/69: Processed 1,000 releases
  → Created 245 suppliers, 780 awards, 650 contracts
[2026-11-05 10:16:12] Batch 2/69: Processed 2,000 releases
  → Created 198 suppliers, 795 awards, 672 contracts
...
[2026-11-05 11:42:15] Ingestion complete!
  → Total suppliers: 18,432
  → Total awards: 84,491
  → Total contracts: 70,470
  → Failed releases: 23
```

### Progress File
`data/real_procurement_ocds/2026_analysis/ingestion_progress.json`

---

## Rollback Strategy

### Tag-Based Removal

All records tagged with `source_system = 'uk-fts-2026'`

**Rollback queries:**
```sql
-- Count records to be removed
SELECT 
  'procurement_records' as table_name, COUNT(*) as count
FROM procurement_records WHERE source_system = 'uk-fts-2026'
UNION ALL
SELECT 'contracts', COUNT(*) 
FROM contracts WHERE source_system = 'uk-fts-2026'
UNION ALL
SELECT 'suppliers', COUNT(*) 
FROM suppliers WHERE source_system = 'uk-fts-2026';

-- Delete in correct order (respect foreign keys)
DELETE FROM procurement_records WHERE source_system = 'uk-fts-2026';
DELETE FROM contracts WHERE source_system = 'uk-fts-2026';
DELETE FROM suppliers WHERE source_system = 'uk-fts-2026' AND is_synthetic = FALSE;
```

---

## Performance Optimization

### Bulk Insert

Use SQLAlchemy `bulk_insert_mappings` for large batches:
```python
db.session.bulk_insert_mappings(ProcurementRecord, records_batch)
```

### Index Management

**Before ingestion:** Drop non-essential indexes
**After ingestion:** Rebuild all indexes

```sql
-- Disable indexes temporarily
DROP INDEX IF EXISTS idx_procurement_records_award_date;
DROP INDEX IF EXISTS idx_procurement_records_region;

-- ... run ingestion ...

-- Rebuild indexes
CREATE INDEX idx_procurement_records_award_date 
ON procurement_records(award_date) 
WHERE source_system = 'uk-fts-2026';
```

### Database Vacuum

Run `VACUUM ANALYZE` after ingestion to update statistics

---

## Testing Plan

### Phase 1: 50-Record Sample (5 minutes)

**Goal:** Validate entity extraction logic

1. Extract first 50 releases from JSONL
2. Process through ingestion pipeline
3. Verify:
   - All 50 releases processed
   - Suppliers created correctly
   - Awards mapped to ProcurementRecords
   - Contracts linked to suppliers
   - `raw` fields contain full OCDS data
   - All currencies are GBP
   - Dates parse correctly

**Success Criteria:**
- 0 fatal errors
- All 50 releases ingested
- Manual inspection of 5 random records shows correct mapping

### Phase 2: 500-Record Validation (15 minutes)

**Goal:** Validate deduplication and performance

1. Extract first 500 releases
2. Process through ingestion pipeline
3. Verify:
   - Supplier deduplication working (no duplicate GB-FTS IDs)
   - Award counts match expectations
   - Contract-award links correct
   - Performance acceptable (~30-50 releases/second)

**Success Criteria:**
- Processing speed: >20 releases/second
- No duplicate suppliers
- Relationships intact

### Phase 3: Full Ingestion (2-3 hours)

**Goal:** Complete dataset import

1. Process all 68,473 releases
2. Monitor progress with checkpoints
3. Validate final counts against CSV files

**Success Criteria:**
- All 68,473 releases processed
- Count validation passes (±5% tolerance)
- <1% failed records
- Database queries return correct results

---

## Output Deliverables

1. **Ingestion Script:** `scripts/ingest_2026_dataset.py`
2. **Validation Report:** `data/real_procurement_ocds/2026_analysis/2026_ingestion_validation_report.md`
3. **Failed Records Log:** `data/real_procurement_ocds/2026_analysis/ingestion_failures.jsonl`
4. **Statistics JSON:** `data/real_procurement_ocds/2026_analysis/ingestion_stats.json`

---

## Approval Gates

### Gate 1: After 50-Record Test
**Decision:** Proceed to 500-record test OR fix issues

### Gate 2: After 500-Record Test
**Decision:** Proceed to full ingestion OR reassess design

### Gate 3: After Full Ingestion
**Decision:** Keep data OR rollback

---

## Timeline Estimate

| Phase | Duration | Notes |
|-------|----------|-------|
| Script development | 2 hours | Extraction logic, error handling |
| 50-record test | 15 minutes | Including manual verification |
| 500-record test | 30 minutes | Including count checks |
| Full ingestion | 2-3 hours | 68,473 releases |
| Post-validation | 30 minutes | Query testing, count verification |
| **Total** | **6-7 hours** | Single developer, no blockers |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Supplier lookup failures | Medium | Medium | Store GB-FTS ID for manual resolution |
| Award-contract link breaks | Low | Medium | Log orphaned contracts, manual linking |
| Performance degradation | Low | Low | Batch commits, index management |
| Disk space exhaustion | Low | High | Monitor space, estimate 2GB requirement |
| Data corruption | Very Low | High | Transaction rollback, checkpoint recovery |

---

## Next Steps

1. ✓ Design complete
2. → Implement ingestion script
3. → Run 50-record validation test
4. → **AWAIT APPROVAL** for 500-record test
5. → Run 500-record validation test
6. → **AWAIT APPROVAL** for full ingestion
7. → Execute full ingestion
8. → Generate validation report
9. → **AWAIT FINAL APPROVAL** to keep or rollback

