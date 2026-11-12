# 2026 UK FTS Dataset: Integration Report

**Report Date:** 2026-11-05  
**Dataset:** UK Find a Tender Service 2026 OCDS Data  
**Status:** ✓ **READY FOR CONTROLLED INGESTION**

---

## Executive Summary

Complete discovery and integration analysis of the 2026 UK Find a Tender Service dataset has been completed. The dataset contains **68,473 procurement releases** from UK government buyers, covering January-October 2026. All files have been inventoried, relationships mapped, schema compatibility verified, and ingestion pipeline designed.

**Key Finding:** The dataset can be ingested into the existing EPI schema without modifications. No blocking schema gaps identified.

---

## Dataset Overview

### Files Discovered

| File | Format | Size | Records | Purpose |
|------|--------|------|---------|---------|
| `2026.jsonl` | JSONL | 434.11 MB | 68,473 | **Primary source** - OCDS compiled releases |
| `2026/*.csv` | CSV (68 files) | 397.15 MB | 1,959,036 rows | **Validation source** - Flattened OCDS tables |
| **Total** | - | **871.6 MB** | - | Complete 2026 UK FTS dataset |

### Directory Structure

```
Sprint 2/
├── 2026.jsonl                    ← PRIMARY AUTHORITATIVE SOURCE
└── 2026/                         ← CSV exports for validation
    ├── main.csv                  ← One row per release (68,473)
    ├── parties.csv               ← All organizations (198,747)
    ├── awards.csv                ← Award decisions (84,491)
    ├── awards_suppliers.csv      ← Supplier relationships (153,817)
    ├── contracts.csv             ← Contracts (70,470)
    ├── tender_lots.csv           ← Tender lots (87,303)
    ├── tender_documents.csv      ← Document metadata (57,145)
    ├── awards_documents.csv      ← Award documents (26,116)
    ├── contracts_documents.csv   ← Contract documents (44,264)
    └── ... (59 more CSV files)
```

---

## Data Profile

### Procurement Coverage

- **Total Releases:** 68,473 (one per OCID)
- **Unique Contracting Processes:** 68,473 OCIDs
- **Date Range:** January 2, 2026 – October 29, 2026 (10 months)
- **Unique Buyers:** 5,437 UK public sector organizations
- **Unique Parties (all roles):** 79,949 organizations
- **Document References:** 112,653 unique URLs

### Procurement Stages

| Stage | Releases with Stage | Coverage |
|-------|---------------------|----------|
| Tender | 68,473 | 100.0% |
| Awards | 51,985 | 75.9% |
| Contracts | 43,873 | 64.1% |
| Planning | 13,862 | 20.2% |

### Procurement Methods

| Method | Count | % of Total |
|--------|-------|------------|
| Open | 19,822 | 29.0% |
| Direct | 17,416 | 25.4% |
| Limited | 14,901 | 21.8% |
| Selective | 5,108 | 7.5% |
| Other | 11,226 | 16.3% |

### Entity Counts (Extracted from CSV)

| Entity Type | Count | Source CSV |
|-------------|-------|------------|
| Awards | 84,491 | awards.csv |
| Award-Supplier Relationships | 153,817 | awards_suppliers.csv |
| Contracts | 70,470 | contracts.csv |
| Tender Lots | 87,303 | tender_lots.csv |
| Tender Items | 56,732 | tender_items.csv |
| Award Items | 50,776 | awards_items.csv |
| Parties (all roles) | 198,747 | parties.csv |
| Tender Documents | 57,145 | tender_documents.csv |
| Award Documents | 26,116 | awards_documents.csv |
| Contract Documents | 44,264 | contracts_documents.csv |

---

## File Relationships

### JSONL vs CSV Relationship

**Finding:** CSV files are **derived exports** of the JSONL file, not independent datasets.

**Evidence:**
1. ✓ OCID counts match exactly: 68,473 in both JSONL and main.csv
2. ✓ Only main.csv contains `ocid` column (primary key)
3. ✓ CSV file structure mirrors OCDS JSON nested hierarchy
4. ✓ Same date range: Jan 2 - Oct 29, 2026 in both formats

**Conclusion:** Use JSONL as primary source, CSV for validation only.

### CSV Hierarchy

CSV files follow OCDS nested structure with `{parent}_{child}.csv` naming:

```
main.csv (68,473 releases)
├── parties.csv (198,747 organizations)
│   ├── parties_additionalIdentifiers.csv
│   ├── parties_additionalContactPoints.csv
│   └── parties_details_classifications.csv
│
├── awards.csv (84,491 awards)
│   ├── awards_suppliers.csv (153,817)
│   ├── awards_items.csv (50,776)
│   ├── awards_documents.csv (26,116)
│   ├── awards_amendments.csv (11,492)
│   └── ... (6 more child tables)
│
├── contracts.csv (70,470 contracts)
│   ├── contracts_documents.csv (44,264)
│   ├── contracts_items.csv (1,328)
│   ├── contracts_amendments.csv (1,997)
│   └── ... (15 more child tables)
│
└── tender_lots.csv (87,303 lots)
    ├── tender_documents.csv (57,145)
    ├── tender_items.csv (56,732)
    ├── tender_lots_awardCriteria_criteria.csv (103,540)
    └── ... (24 more child tables)
```

---

## Schema Compatibility

### EPI Database Models

Four primary models will be used:

1. **ProcurementRecord** - For awards (main entity)
2. **Supplier** - For organizations with supplier role
3. **Contract** - For formal contracts
4. **Product** - For items/specifications (optional)

### Compatibility Assessment

**✓ NO BLOCKING SCHEMA GAPS**

The 2026 dataset can be fully ingested without schema modifications:

| OCDS Entity | EPI Model | Compatibility | Notes |
|-------------|-----------|---------------|-------|
| `awards[]` | ProcurementRecord | ✓ Compatible | One record per award |
| `parties[]` (suppliers) | Supplier | ✓ Compatible | Deduplicate by GB-FTS ID |
| `contracts[]` | Contract | ✓ Compatible | Link to supplier via award |
| `buyer` | ProcurementRecord.buyer | ✓ Compatible | Store name directly |
| `items[]` | Product | ⚠️ Optional | Can extract if needed |
| `tender` | - | ⚠️ No model | Store in `raw` field only |

### Critical Requirement

**Currency:** All UK FTS records use **GBP** (British Pound), not USD default.  
**Action Required:** Set `currency = "GBP"` for all imported records.

---

## Schema Mapping

### ProcurementRecord Mapping

| OCDS Field | EPI Field | Transform |
|------------|-----------|-----------|
| `awards[].suppliers[0].name` | `supplier_name` | Direct |
| `awards[].suppliers[0].id` | `supplier_id` | Lookup EPI ID by GB-FTS ID |
| `buyer.name` | `buyer` | Direct |
| `awards[].value.amount` | `value` | Direct (float) |
| `awards[].value.currency` | `currency` | Set to "GBP" |
| `awards[].date` | `award_date` | Parse ISO 8601 date |
| `awards[].title` | `product_name` | Direct |
| `awards[].items[0].classification.description` | `category` | Extract from items |
| `parties[supplier].address.region` | `region` | Lookup from parties |
| Full OCDS release | `raw` | JSON (preserve everything) |
| `ocid` | `source_id` | Via ProvenanceMixin |
| `"uk-fts-2026"` | `source_system` | Literal value |

### Supplier Mapping

| OCDS Field | EPI Field | Transform |
|------------|-----------|-----------|
| `parties[].name` | `name` | Direct |
| `parties[].name` | `normalized_name` | Lowercase + trim |
| `parties[].address.countryName` | `country` | Direct |
| `parties[].address.region` | `region` | Direct |
| `parties[].contactPoint.email` | `contact_email` | Direct |
| `parties[].id` | `attributes["gb_fts_id"]` | Store for deduplication |
| `parties[].identifier` | `attributes["identifier"]` | JSON |
| `parties[].roles` | `attributes["roles"]` | JSON array |
| `"active"` | `status` | Default |

### Contract Mapping

| OCDS Field | EPI Field | Transform |
|------------|-----------|-----------|
| `contracts[].id` | `contract_number` | Direct |
| `contracts[].title` | `title` | Direct or from award |
| `contracts[].value.amount` | `total_value` | Direct |
| `contracts[].value.currency` | `currency` | Set to "GBP" |
| `contracts[].period.startDate` | `effective_date` | Parse ISO date |
| `contracts[].period.endDate` | `expiry_date` | Parse ISO date |
| `contracts[].status` | `status` | Direct |
| `contracts[].awardID` | `metadata_json["award_id"]` | JSON |
| Lookup from `awards[]` | `supplier_id` | Via awardID |

---

## Data Quality Verification

### Verified ✓

1. ✓ **OCID Uniqueness:** All 68,473 OCIDs are unique (no duplicates)
2. ✓ **JSONL-CSV Match:** main.csv OCIDs match JSONL 100% (68,473 = 68,473)
3. ✓ **Date Range:** All dates within 2026 (Jan 2 - Oct 29)
4. ✓ **Currency Consistency:** All values in GBP
5. ✓ **OCID Format:** Consistent `ocds-h6vhtk-{id}` pattern
6. ✓ **Party ID Format:** Consistent `GB-FTS-{number}` pattern
7. ✓ **File Integrity:** JSONL parses completely, all 68,473 lines valid JSON

### Requires Validation During Ingestion

- □ All award.suppliers resolve to valid parties
- □ All contract.awardID resolve to existing awards
- □ No negative values in amounts
- □ Required fields populated (buyer, supplier_name)
- □ Date parsing successful for all date fields
- □ Supplier deduplication working correctly

---

## Ingestion Design

### Data Flow

```
2026.jsonl (68,473 releases)
    ↓
Parse JSONL → OCDS Release Objects
    ↓
Extract Parties → Create Suppliers (deduplicated by GB-FTS ID)
    ↓
Extract Awards → Create ProcurementRecords (one per award)
    ↓
Extract Contracts → Create Contracts (linked to suppliers)
    ↓
Validation → Cross-check counts vs CSV files
    ↓
EPI Database
```

### Entity Creation Strategy

1. **Suppliers First**
   - Extract all parties with role="supplier"
   - Deduplicate by `party.id` (GB-FTS identifier)
   - Create/update Supplier records
   - Cache GB-FTS ID → EPI supplier_id mapping

2. **Awards as ProcurementRecords**
   - One ProcurementRecord per award
   - Lookup supplier by GB-FTS ID from cache
   - Store full award object in `raw` field
   - Expected: ~84,491 records

3. **Contracts**
   - Extract from contracts[] section
   - Link to supplier via awardID → award → supplier lookup
   - Store contract metadata
   - Expected: ~70,470 records

### Batch Processing

- **Batch Size:** 1,000 releases per transaction
- **Checkpointing:** Save progress after each batch
- **Error Handling:** Log and skip failed records, don't fail batch
- **Estimated Time:** 2-3 hours for full dataset

### Expected Database Counts

| Entity | Estimated Count | Source |
|--------|-----------------|--------|
| Suppliers | 15,000 - 20,000 | Unique suppliers from 79,949 parties |
| ProcurementRecords | 84,491 | One per award |
| Contracts | 70,470 | One per contract |

---

## Validation Strategy

### Phase 1: 50-Record Test

**Goal:** Validate extraction logic

- Extract first 50 releases
- Process through pipeline
- Manual inspection of results
- **Duration:** 15 minutes

**Success Criteria:**
- All 50 releases processed
- Suppliers created correctly
- Awards mapped to ProcurementRecords
- Contracts linked properly
- Currency is GBP
- Dates parse correctly

### Phase 2: 500-Record Test

**Goal:** Validate deduplication and performance

- Extract first 500 releases
- Process through pipeline
- Check supplier deduplication
- **Duration:** 30 minutes

**Success Criteria:**
- Processing speed: >20 releases/second
- No duplicate suppliers (by GB-FTS ID)
- Relationships intact

### Phase 3: Full Ingestion

**Goal:** Complete dataset import

- Process all 68,473 releases
- Monitor with checkpoints
- Validate final counts
- **Duration:** 2-3 hours

**Success Criteria:**
- All 68,473 releases processed
- Count validation passes (±5% tolerance)
- <1% failed records
- Database queries return correct results

### Post-Ingestion Validation Queries

```sql
-- Verify record counts
SELECT source_system, COUNT(*) 
FROM procurement_records 
WHERE source_system = 'uk-fts-2026';
-- Expected: ~84,491

SELECT source_system, COUNT(*) 
FROM suppliers 
WHERE source_system = 'uk-fts-2026';
-- Expected: ~15,000-20,000

SELECT source_system, COUNT(*) 
FROM contracts 
WHERE source_system = 'uk-fts-2026';
-- Expected: ~70,470

-- Verify currency
SELECT currency, COUNT(*) 
FROM procurement_records 
WHERE source_system = 'uk-fts-2026' 
GROUP BY currency;
-- Expected: GBP only

-- Verify date range
SELECT MIN(award_date), MAX(award_date) 
FROM procurement_records 
WHERE source_system = 'uk-fts-2026';
-- Expected: 2026-01-02 to 2026-10-29
```

---

## Rollback Plan

All records tagged with `source_system = 'uk-fts-2026'` for easy rollback:

```sql
-- Remove all 2026 UK FTS data
DELETE FROM procurement_records WHERE source_system = 'uk-fts-2026';
DELETE FROM contracts WHERE source_system = 'uk-fts-2026';
DELETE FROM suppliers WHERE source_system = 'uk-fts-2026' AND is_synthetic = FALSE;
```

**Note:** Original 9 synthetic documents remain untouched (`is_synthetic = TRUE`).

---

## Deliverables

All analysis documents completed:

1. ✓ `2026_directory_inventory.md` - Complete file listing with sizes and counts
2. ✓ `2026_directory_inventory.json` - Machine-readable inventory
3. ✓ `2026_data_relationships.md` - CSV file hierarchy and relationships
4. ✓ `2026_dataset_profile.md` - Statistical profile and data quality analysis
5. ✓ `2026_schema_gap_analysis.md` - EPI schema compatibility assessment
6. ✓ `2026_ingestion_design.md` - Complete ingestion pipeline design
7. ✓ `INTEGRATION_REPORT.md` - This summary document
8. → `2026_ingestion_validation_report.md` - To be created after testing

---

## Restrictions Compliance

### ✓ Verified

- ✓ Only 2026 dataset used (not all-time dataset)
- ✓ Original 9 synthetic documents untouched
- ✓ No database modifications made
- ✓ No source files overwritten
- ✓ No destructive migrations run
- ✓ JSONL and CSV relationship established (CSV = derived export)
- ✓ All counts verified, not estimated
- ✓ No ingestion started (awaiting approval)

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Supplier lookup failures | Medium | Medium | Store GB-FTS ID for manual resolution |
| Award-contract link breaks | Low | Medium | Log orphaned contracts for investigation |
| Performance degradation | Low | Low | Batch commits, index management |
| Disk space exhaustion | Very Low | High | Estimate: 2GB required, verify available |
| Currency conversion errors | Very Low | High | Hard-code GBP, no conversion logic |

---

## Final Status

### ✓ **READY FOR CONTROLLED INGESTION**

All prerequisites completed:

- ✓ Complete directory discovery
- ✓ File relationships understood
- ✓ Dataset profiled (68,473 releases verified)
- ✓ Schema compatibility confirmed (no blocking gaps)
- ✓ Ingestion pipeline designed
- ✓ Validation strategy defined
- ✓ Rollback plan documented

### Next Actions

1. **DECISION REQUIRED:** Approve 50-record validation test
2. Run 50-record test (15 minutes)
3. **DECISION REQUIRED:** Approve 500-record validation test
4. Run 500-record test (30 minutes)
5. **DECISION REQUIRED:** Approve full ingestion
6. Execute full ingestion (2-3 hours)
7. Generate validation report
8. **FINAL DECISION:** Keep data or rollback

---

## Contact for Approval

All phases require explicit user approval before proceeding. No ingestion will be performed without confirmation.

**Current Status:** Awaiting approval for Phase 1 (50-record test)

---

**Report End**  
**Generated:** 2026-11-05  
**Analysis Complete:** ✓  
**Ready for Testing:** ✓  
**Awaiting Approval:** ✓

