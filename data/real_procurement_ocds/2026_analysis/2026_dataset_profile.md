# 2026 UK FTS Dataset: Complete Profile

**Profile Date:** 2026-11-05  
**Dataset:** UK Find a Tender Service (FTS) 2026 OCDS Data  
**Publisher:** Cabinet Office (UK Government)  
**License:** Open Government Licence v3.0  
**Data Standard:** OCDS 1.1 (compiled releases)

---

## Executive Summary

- **Total Procurement Releases:** 68,473
- **Unique Contracting Processes (OCIDs):** 68,473 (1:1 release-to-OCID ratio)
- **Date Coverage:** January 2, 2026 - October 29, 2026 (10 months)
- **Unique Buyers:** 5,437
- **Unique Parties (all roles):** 79,949
- **Document References:** 112,653 unique URLs
- **Total Dataset Size:** 871.6 MB (434 MB JSONL + 397 MB CSV)

---

## Data Format and Structure

### Primary Data File

**File:** `2026.jsonl` (434.11 MB)

- **Format:** JSONL (newline-delimited JSON)
- **Records:** 68,473 lines (one OCDS compiled release per line)
- **Structure:** Each line is a complete OCDS release (NOT a release package)
- **Encoding:** UTF-8

**OCDS Structure:**
```json
{
  "id": "ocds-h6vhtk-{tender-id}-{timestamp}",
  "tag": ["compiled"],
  "date": "2026-01-29T14:53:39Z",
  "ocid": "ocds-h6vhtk-{tender-id}",
  "buyer": {...},
  "tender": {...},
  "awards": [{...}],
  "contracts": [{...}],
  "planning": {...},
  "parties": [{...}]
}
```

### Supplementary Data Files

**Directory:** `2026/` (68 CSV files, 397.15 MB total)

These files represent **normalized/flattened OCDS entities** for tabular analysis. They are NOT independent datasets but rather alternative representations of the JSONL data.

**Relationship:** CSV files are **derived exports** of the JSONL, containing the same data in denormalized table format.

---

## Entity Counts

### Procurement Stages

| Stage | Releases | Coverage |
|-------|----------|----------|
| Tender | 68,473 | 100.0% (all releases) |
| Awards | 51,985 | 75.9% |
| Contracts | 43,873 | 64.1% |
| Planning | 13,862 | 20.2% |

### Procurement Methods

| Method | Count | Percentage |
|--------|-------|------------|
| Open | 19,822 | 29.0% |
| Direct | 17,416 | 25.4% |
| Limited | 14,901 | 21.8% |
| Selective | 5,108 | 7.5% |
| Other | 11,226 | 16.3% |

### Tender Status Distribution

*To be calculated from tender.status field*

### Award Status Distribution

*To be calculated from awards[].status field*

### Contract Status Distribution

*To be calculated from contracts[].status field*

---

## Parties and Organizations

| Party Type | Unique Count |
|------------|--------------|
| All Parties | 79,949 |
| Buyers | 5,437 |
| Suppliers (from awards_suppliers.csv) | 153,817 relationships |

**Note:** The parties table (198,747 rows) contains all organizations across all roles. A single organization may appear multiple times with different roles.

---

## Items and Classifications

| Entity | Count |
|--------|-------|
| Tender Items | 56,732 |
| Tender Item Classifications | 154,040 |
| Award Items | 50,776 |
| Award Item Classifications | 81,537 |
| Contract Items | 1,328 |
| Lots | 87,303 |

---

## Documents and Attachments

| Source | Document Count |
|--------|----------------|
| JSONL document URLs | 112,653 unique URLs |
| tender_documents.csv | 57,145 references |
| awards_documents.csv | 26,116 references |
| contracts_documents.csv | 44,264 references |
| planning_documents.csv | 18,478 references |

**Total Document References:** 146,003 (CSV) vs 112,653 (JSONL unique URLs)

**Discrepancy Explanation:** CSV files may contain:
- Multiple references to the same URL
- Documents without URLs
- Metadata-only entries

---

## Amendments and Changes

| Amendment Type | Count |
|----------------|-------|
| Tender Amendments | 9,193 |
| Tender Unstructured Changes | 2,623 |
| Award Amendments | 11,492 |
| Contract Amendments | 1,997 |
| Proposed Contract Amendments | 198 |

---

## Value and Financial Data

### Currency Distribution

All contracts use **GBP** (British Pound Sterling) as primary currency.

### Value Fields

- `tender.value.amount` - Estimated tender value
- `tender.lots[].value.amount` - Lot-specific values
- Contract values extracted from contracts section

**Statistical Analysis:** *To be calculated from tender.value and contract.value fields*

---

## Data Quality Indicators

### Completeness

| Field | Populated | Missing | Coverage |
|-------|-----------|---------|----------|
| OCID | 68,473 | 0 | 100% |
| Date | 68,473 | 0 | 100% |
| Buyer | 68,473 | 0 | 100% |
| Tender | 68,473 | 0 | 100% |
| Awards | 51,985 | 16,488 | 75.9% |
| Contracts | 43,873 | 24,600 | 64.1% |
| Planning | 13,862 | 54,611 | 20.2% |

### Identifiers

- **OCID Format:** `ocds-h6vhtk-{tender-id}`
- **Buyer ID Format:** `GB-FTS-{number}`
- **Supplier ID Format:** `GB-FTS-{number}`
- **Release ID Format:** `ocds-h6vhtk-{tender-id}-{ISO8601-timestamp}`

### Duplicate Keys

**OCID Uniqueness:** ✓ VERIFIED - All 68,473 OCIDs are unique (1:1 with releases)

**main.csv OCID Match:** ✓ VERIFIED - All 68,473 OCIDs in main.csv match JSONL OCIDs (100% coverage)

---

## CSV File Hierarchy

The CSV files follow a hierarchical naming convention representing OCDS nested structures:

### Main Tables

1. **main.csv** (68,473 rows, 134 columns)
   - One row per release
   - Contains: release metadata, buyer, top-level tender fields
   - **Key column:** `ocid`

2. **parties.csv** (198,747 rows, 30 columns)
   - All organizations (buyers, suppliers, tenderers)
   - Multiple rows per OCID (one per party per release)
   - Child tables: `parties_additionalIdentifiers`, `parties_additionalContactPoints`, `parties_details_classifications`

3. **awards.csv** (84,491 rows, 31 columns)
   - Award decisions
   - Multiple awards possible per OCID
   - Child tables: `awards_suppliers`, `awards_items`, `awards_documents`, `awards_amendments`, `awards_milestones`, `awards_subcontracting_*`

4. **contracts.csv** (70,470 rows, 29 columns)
   - Contract details following awards
   - Child tables: `contracts_items`, `contracts_documents`, `contracts_amendments`, `contracts_implementation_*`, `contracts_agreedMetrics_*`, `contracts_proposedAmendments_*`

5. **tender_lots.csv** (87,303 rows, 27 columns)
   - Individual lots within tenders
   - Child tables: `tender_lots_awardCriteria_*`, `tender_lots_selectionCriteria_*`, `tender_lots_identifiers`

### Document Tables

- `tender_documents.csv` - 57,145 rows
- `awards_documents.csv` - 26,116 rows
- `contracts_documents.csv` - 44,264 rows
- `planning_documents.csv` - 18,478 rows

### Classification and Item Tables

Contain CPV codes, delivery addresses, and detailed specifications:
- `tender_items_additionalClassifications.csv` - 154,040 rows
- `awards_items_additionalClassifications.csv` - 81,537 rows
- `tender_items_deliveryAddresses.csv` - 139,525 rows

### Bid Statistics

- `bids_statistics.csv` - 117,709 rows (bid counts and statistics per lot)
- `bids_details.csv` - 23,188 rows
- `bids_details_tenderers.csv` - 24,284 rows

---

## Key Findings

### 1. JSONL as Authoritative Source

The **2026.jsonl file is the authoritative source**. CSV files are flattened exports for analysis convenience.

**Evidence:**
- main.csv contains exactly 68,473 rows with 100% OCID match to JSONL
- Only main.csv has `ocid` column; other CSVs use join keys
- CSV structure mirrors OCDS nested hierarchy

**Ingestion Strategy:** Use JSONL as primary source to preserve OCDS structure and relationships.

### 2. No Duplicate Data Between Files

JSONL and CSV files contain **the same procurement data in different formats**, not independent datasets.

**Verification:**
- Same OCID count: 68,473
- Same date range: Jan 2 - Oct 29, 2026
- main.csv columns are flattened OCDS release fields

### 3. Compiled Releases Only

All 68,473 releases have tag `"compiled"`, meaning they represent the **current state** of each contracting process, not individual release events.

**Implication:** No need to handle release versioning or compilation logic during ingestion.

### 4. High Document URL Coverage

112,653 unique document URLs across 68,473 releases = **1.65 documents per release average**.

Document types include:
- Tender notices and specifications
- Award notices
- Contract documents
- Planning documents

### 5. Incomplete Contract Coverage

Only 64.1% of tenders have associated contracts, suggesting:
- Many tenders still in progress (2026 data)
- Cancelled tenders
- Awards without formal contracts recorded

---

## Schema Compatibility Assessment

See separate document: `2026_schema_gap_analysis.md`

---

## Data Quality Issues

### Missing Values

- **Planning data:** Present in only 20.2% of releases
- **Contract data:** Present in only 64.1% of releases
- **Supplier identifiers:** Some awards have suppliers without IDs (name-only references)

### Orphaned Relationships

*To be verified:* Check if all award.relatedLots reference existing lot IDs

### Date Format Consistency

All dates use ISO 8601 format with timezone (UTC): `2026-01-29T14:53:39Z`

---

## Recommended Ingestion Approach

1. **Use JSONL as primary source** (preserve OCDS structure)
2. **Use main.csv for validation** (cross-check OCID counts)
3. **Extract entities in order:**
   - Parties (buyers and suppliers)
   - Tenders
   - Awards
   - Contracts
   - Documents (metadata only, URLs for future download)
4. **Preserve original identifiers** (OCID, party IDs, award IDs, contract IDs)
5. **Store raw OCDS in `raw` field** for audit trail

---

## Next Steps

1. ✓ Complete directory discovery
2. ✓ Understand file relationships
3. ✓ Dataset profiling
4. → Schema mapping to EPI models
5. → Design ingestion pipeline
6. → Validation testing (50 + 500 records)
7. → Full ingestion (approval required)

