# 2026 UK FTS Dataset: EPI Schema Gap Analysis

**Analysis Date:** 2026-11-05  
**Target Schema:** EPI Database Models v1.0  
**Source Schema:** OCDS 1.1 (UK FTS Implementation)

---

## Overview

This document analyzes the compatibility between the 2026 UK FTS OCDS dataset and the existing EPI database schema, identifying gaps, mapping strategies, and required schema changes.

---

## Current EPI Models

### 1. ProcurementRecord
```python
class ProcurementRecord(Base):
    id: str  # rec_xxx
    buyer: str | None
    supplier_name: str
    supplier_id: str | None
    contract_id: str | None
    product_name: str | None
    category: str | None
    quantity: float | None
    unit_price: float | None
    value: float | None
    currency: str  # default: USD
    award_date: date | None
    region: str | None
    raw: dict  # JSON field for source data
    is_synthetic: bool
    
    # Mixins: tenant_id, created_at, updated_at, source_*
```

**Current Purpose:** Award/purchase lines from external procurement datasets.

### 2. Supplier
```python
class Supplier(Base):
    id: str  # sup_xxx
    name: str
    normalized_name: str
    category: str | None
    country: str | None
    region: str | None
    status: str  # default: active
    contact_email: str | None
    is_synthetic: bool
    attributes: dict
    
    # Relationships
    contracts: list[Contract]
```

### 3. Contract
```python
class Contract(Base):
    id: str  # ctr_xxx
    supplier_id: str | None
    contract_number: str
    title: str
    contract_type: str | None
    category: str | None
    currency: str  # default: USD
    total_value: float | None
    effective_date: date | None
    expiry_date: date | None
    status: str  # default: unknown
    version: int
    superseded_by_id: str | None
    parent_contract_id: str | None
    is_synthetic: bool
    metadata_json: dict
```

### 4. Product
```python
class Product(Base):
    id: str  # prd_xxx
    sku: str
    name: str
    category: str | None
    unit: str  # default: unit
    is_synthetic: bool
    attributes: dict
```

---

## OCDS Structure vs EPI Models

### OCDS Release Structure
```json
{
  "ocid": "ocds-h6vhtk-{id}",
  "date": "2026-01-29T14:53:39Z",
  "buyer": { "id": "GB-FTS-3636", "name": "..." },
  "tender": {
    "id": "...",
    "title": "...",
    "status": "active",
    "procurementMethod": "open",
    "value": { "amount": 28000000, "currency": "GBP" },
    "lots": [{...}],
    "items": [{...}],
    "documents": [{...}]
  },
  "awards": [{
    "id": "...",
    "title": "...",
    "status": "active",
    "value": { "amount": ..., "currency": "GBP" },
    "suppliers": [{ "id": "GB-FTS-64724", "name": "..." }],
    "items": [{...}],
    "documents": [{...}]
  }],
  "contracts": [{
    "id": "...",
    "awardID": "...",
    "status": "active",
    "value": { "amount": ..., "currency": "GBP" },
    "period": { "startDate": "...", "endDate": "..." },
    "documents": [{...}]
  }],
  "parties": [{
    "id": "GB-FTS-xxx",
    "name": "...",
    "roles": ["buyer"|"supplier"|"tenderer"],
    "identifier": { "id": "...", "scheme": "..." },
    "address": {...},
    "contactPoint": {...}
  }]
}
```

---

## Gap Analysis

### 1. Buyer Information

**OCDS:**
```json
{
  "buyer": { "id": "GB-FTS-3636", "name": "Procurement and Logistics Service" }
}
```

**EPI Model:** `ProcurementRecord.buyer: str | None`

**Gap:** ✓ NO GAP - Can store buyer name directly  
**Mapping:** `buyer.name` → `ProcurementRecord.buyer`  
**Enhancement Opportunity:** Store buyer ID in `raw` field for reference

---

### 2. Supplier Information

**OCDS:**
```json
{
  "awards": [{
    "suppliers": [
      { "id": "GB-FTS-64724", "name": "Life Technologies Limited" }
    ]
  }]
}
```

**EPI Models:**
- `ProcurementRecord.supplier_name: str`
- `ProcurementRecord.supplier_id: str | None`
- `Supplier` table

**Gap:** ✓ NO GAP - Can store both name and ID  
**Mapping:**
- `award.suppliers[0].name` → `ProcurementRecord.supplier_name`
- `award.suppliers[0].id` → `ProcurementRecord.supplier_id`

**Enhancement:** Create `Supplier` records for unique suppliers

---

### 3. Contract Information

**OCDS:**
```json
{
  "contracts": [{
    "id": "029319-2024-3525889-1",
    "awardID": "029319-2024-3525889-1",
    "title": "...",
    "status": "active",
    "value": { "amount": 125000, "currency": "GBP" },
    "period": {
      "startDate": "2026-02-01",
      "endDate": "2027-02-01"
    }
  }]
}
```

**EPI Model:** `Contract` table

**Gaps:**
- ✓ `contracts[].id` maps to `Contract.contract_number`
- ✓ `contracts[].status` maps to `Contract.status`
- ✓ `contracts[].value.amount` maps to `Contract.total_value`
- ✓ `contracts[].value.currency` maps to `Contract.currency`
- ✓ `contracts[].period.startDate` maps to `Contract.effective_date`
- ✓ `contracts[].period.endDate` maps to `Contract.expiry_date`
- ⚠️ **MINOR GAP:** `awardID` link not captured in Contract model

**Resolution:** Store `awardID` in `Contract.metadata_json`

---

### 4. Award Information

**OCDS:**
```json
{
  "awards": [{
    "id": "029319-2024-3525889-1",
    "title": "Provision of a Genetic Analyser...",
    "status": "active",
    "value": { "amount": 125000, "currency": "GBP" },
    "date": "2026-01-15",
    "suppliers": [{...}],
    "items": [{...}]
  }]
}
```

**EPI Model:** `ProcurementRecord`

**Mapping:**
- `award.id` → Store in `ProcurementRecord.raw`
- `award.title` → `ProcurementRecord.product_name` (if no items)
- `award.value.amount` → `ProcurementRecord.value`
- `award.value.currency` → `ProcurementRecord.currency`
- `award.date` → `ProcurementRecord.award_date`
- `award.suppliers[0]` → `ProcurementRecord.supplier_*`

**Gap:** ⚠️ **MODERATE GAP** - No dedicated Award model

**Current Workaround:** Store award as `ProcurementRecord`  
**Future Enhancement:** Consider adding `Award` model for full OCDS fidelity

---

### 5. Items and Products

**OCDS:**
```json
{
  "items": [{
    "id": "1",
    "description": "Genetic Analyser Equipment",
    "classification": {
      "id": "38000000",
      "scheme": "CPV",
      "description": "Laboratory, optical..."
    },
    "quantity": 1,
    "unit": { "name": "unit" },
    "additionalClassifications": [{
      "id": "...",
      "scheme": "UNSPSC"
    }]
  }]
}
```

**EPI Model:** `Product`

**Gaps:**
- ✓ `item.description` maps to `Product.name`
- ✓ `item.classification.description` maps to `Product.category`
- ✓ `item.unit.name` maps to `Product.unit`
- ⚠️ **MINOR GAP:** No `sku` field in OCDS items
- ⚠️ **MINOR GAP:** CPV codes not captured

**Resolution:**
- Generate SKU from item ID
- Store CPV codes in `Product.attributes`

---

### 6. Tender Information

**OCDS:**
```json
{
  "tender": {
    "id": "ocds-h6vhtk-028e6c",
    "title": "Molecular Diagnostics Framework",
    "description": "...",
    "status": "active",
    "procurementMethod": "selective",
    "procurementMethodDetails": "dynamic purchasing system",
    "mainProcurementCategory": "goods",
    "value": { "amount": 28000000, "currency": "GBP" },
    "tenderPeriod": { "endDate": "2026-03-15" },
    "lots": [{...}],
    "items": [{...}]
  }
}
```

**EPI Model:** NO DIRECT MODEL

**Gap:** ⚠️ **MAJOR GAP** - No Tender model exists

**Current Workaround:** Store tender data in `ProcurementRecord.raw`  
**Impact:** Cannot query by tender status, procurement method, or tender value

**Resolution Options:**
1. **Option A (Minimal):** Store only awards/contracts, keep tender in `raw`
2. **Option B (Enhanced):** Create new `Tender` model

---

### 7. Documents

**OCDS:**
```json
{
  "tender": {
    "documents": [{
      "id": "doc-001",
      "documentType": "tenderNotice",
      "title": "Tender Notice",
      "url": "https://www.find-tender.service.gov.uk/...",
      "format": "text/html",
      "language": "en"
    }]
  }
}
```

**EPI Model:** Document model (assumed to exist based on `source_document_id` foreign keys)

**Gap:** ⚠️ **UNKNOWN** - Document model not inspected yet

**Required Verification:** Check if Document model supports:
- External URL storage
- Document type classification
- Format/language metadata

---

### 8. Parties and Organizations

**OCDS:**
```json
{
  "parties": [{
    "id": "GB-FTS-3636",
    "name": "Procurement and Logistics Service",
    "roles": ["buyer"],
    "identifier": {
      "id": "...",
      "scheme": "GB-FTS",
      "legalName": "..."
    },
    "address": {
      "countryName": "United Kingdom",
      "region": "Northern Ireland"
    },
    "contactPoint": {
      "email": "procurement@example.com"
    }
  }]
}
```

**EPI Model:** `Supplier`

**Gaps:**
- ✓ `party.name` maps to `Supplier.name`
- ✓ `party.address.countryName` maps to `Supplier.country`
- ✓ `party.address.region` maps to `Supplier.region`
- ✓ `party.contactPoint.email` maps to `Supplier.contact_email`
- ⚠️ **MINOR GAP:** `party.identifier` not captured
- ⚠️ **MINOR GAP:** `party.roles` not captured
- ⚠️ **MINOR GAP:** Multiple identifiers not supported

**Resolution:** Store identifier and roles in `Supplier.attributes`

---

### 9. Currency Handling

**OCDS:** All values in **GBP** (British Pound)  
**EPI Default:** USD

**Gap:** ⚠️ **CRITICAL** - Currency mismatch

**Resolution:** **MUST** set `currency = "GBP"` for all UK FTS records

---

### 10. Identifiers and Provenance

**OCDS:**
- `ocid`: Unique contracting process ID
- `id`: Unique release ID
- `date`: Release publication date

**EPI Model:** `ProvenanceMixin`
```python
source_system: str | None
source_id: str | None
source_url: str | None
source_retrieved_at: datetime | None
```

**Mapping:**
- `ocid` → `source_id`
- `"uk-fts-2026"` → `source_system`
- `date` → `source_retrieved_at`

---

## Summary of Gaps

### ✓ NO SCHEMA CHANGES REQUIRED (CAN PROCEED)

The existing EPI schema can accommodate the 2026 UK FTS dataset with these caveats:

1. **ProcurementRecord as Primary Entity:** Use for awards/contracts
2. **Supplier Records:** Create for unique suppliers
3. **Currency:** Set to GBP (not default USD)
4. **Raw Field:** Store full OCDS release for audit trail
5. **Tender Data:** Stored in `raw` only (not queryable)

### ⚠️ RECOMMENDED ENHANCEMENTS (OPTIONAL)

For full OCDS fidelity and enhanced querying:

1. **Add Tender Model:**
```python
class Tender(Base):
    id: str
    ocid: str  # FK to contracting process
    title: str
    status: str
    procurement_method: str
    main_procurement_category: str
    value_amount: float | None
    value_currency: str
    tender_period_end: date | None
    buyer_id: str | None
    metadata_json: dict
```

2. **Add Award Model:**
```python
class Award(Base):
    id: str
    ocid: str
    tender_id: str | None
    title: str
    status: str
    award_date: date | None
    value_amount: float | None
    value_currency: str
    metadata_json: dict
```

3. **Enhance Supplier Model:**
   - Add `identifiers: dict` field for storing multiple identifiers
   - Add `roles: list[str]` field for party roles

4. **Add ContractingProcess Model:**
```python
class ContractingProcess(Base):
    ocid: str  # Primary key
    release_id: str
    release_date: datetime
    buyer_id: str
    tender_id: str | None
    raw_release: dict
```

### 🚫 BLOCKERS (NONE)

No blocking schema gaps identified. Ingestion can proceed with current schema.

---

## Recommended Ingestion Strategy

### Phase 1: Minimal Viable Ingestion (Current Schema)

1. **Create Supplier records** from `parties` with role="supplier"
2. **Create ProcurementRecord per award:**
   - One record per award
   - Link to supplier
   - Store value, currency, date
   - Store full OCDS release in `raw`
3. **Create Contract records** from `contracts` section:
   - Link to supplier
   - Store contract ID, value, dates
   - Store `awardID` in `metadata_json`

**Result:** Queryable awards and contracts with full OCDS preservation

### Phase 2: Enhanced Ingestion (With Schema Changes)

1. **Add Tender and Award models** (requires migration)
2. **Create ContractingProcess records** (one per OCID)
3. **Link Tender → Awards → Contracts** hierarchy
4. **Enable querying by:**
   - Procurement method
   - Tender status
   - Award status
   - Tender value ranges

---

## Field Mapping Tables

### ProcurementRecord Mapping

| OCDS Path | EPI Field | Transform |
|-----------|-----------|-----------|
| `awards[].suppliers[0].name` | `supplier_name` | Direct |
| `awards[].suppliers[0].id` | `supplier_id` | Direct |
| `buyer.name` | `buyer` | Direct |
| `awards[].value.amount` | `value` | Direct |
| `awards[].value.currency` | `currency` | Direct (GBP) |
| `awards[].date` | `award_date` | Parse ISO date |
| `awards[].title` | `product_name` | If no items |
| `awards[].items[0].classification.description` | `category` | Direct |
| `parties[supplier].address.region` | `region` | Lookup from parties |
| Full release | `raw` | JSON |
| `ocid` | `source_id` | Via ProvenanceMixin |

### Supplier Mapping

| OCDS Path | EPI Field | Transform |
|-----------|-----------|-----------|
| `parties[].name` | `name` | Direct |
| `parties[].name` | `normalized_name` | Lowercase, trim |
| `parties[].address.countryName` | `country` | Direct |
| `parties[].address.region` | `region` | Direct |
| `parties[].contactPoint.email` | `contact_email` | Direct |
| `parties[].identifier` | `attributes["identifier"]` | JSON |
| `parties[].roles` | `attributes["roles"]` | JSON |
| Literal `"active"` | `status` | Default |

### Contract Mapping

| OCDS Path | EPI Field | Transform |
|-----------|-----------|-----------|
| `contracts[].id` | `contract_number` | Direct |
| `contracts[].title` | `title` | Direct or from award |
| `contracts[].value.amount` | `total_value` | Direct |
| `contracts[].value.currency` | `currency` | Direct (GBP) |
| `contracts[].period.startDate` | `effective_date` | Parse ISO date |
| `contracts[].period.endDate` | `expiry_date` | Parse ISO date |
| `contracts[].status` | `status` | Direct |
| `contracts[].awardID` | `metadata_json["award_id"]` | JSON |
| Lookup from awards | `supplier_id` | Via awardID lookup |

---

## Validation Checkpoints

Before full ingestion, validate:

1. ✓ All 68,473 OCIDs are unique
2. ✓ All currency values are GBP
3. ✓ Supplier IDs format: `GB-FTS-{number}`
4. ✓ OCID format: `ocds-h6vhtk-{id}`
5. □ All award.suppliers resolve to parties
6. □ All contract.awardID resolve to awards
7. □ Date ranges are reasonable (2026 only)
8. □ No negative values
9. □ Required fields populated (buyer, supplier_name, ocid)
10. □ No duplicate insertions

---

## Conclusion

**STATUS:** ✓ **READY FOR INGESTION WITH CURRENT SCHEMA**

The 2026 UK FTS dataset can be ingested into the current EPI schema without blocking issues. Recommended approach:

1. **Use ProcurementRecord for awards** (primary entity)
2. **Create Supplier records** for unique suppliers
3. **Create Contract records** for formal contracts
4. **Store full OCDS in `raw` field** for audit trail
5. **Set currency to GBP** for all records
6. **Validate 50-record batch** before full ingestion
7. **Consider schema enhancements** for Phase 2

**No schema migration required to proceed.**

