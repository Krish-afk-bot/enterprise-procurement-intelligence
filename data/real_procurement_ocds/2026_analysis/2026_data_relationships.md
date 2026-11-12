# 2026 UK FTS Dataset: Data Relationships

## File Hierarchy

Based on file naming patterns, the CSV files represent normalized OCDS entities:

### awards.csv

- **Rows:** 84,491
- **Columns:** `id`, `status`, `relatedLots`, `main_ocid`, `main_id`, `title`, `statusDetails`, `hasSubcontracting`, `subcontracting_description`, `subcontracting_value_amount` ... (31 total)

**Child tables:**

- `awards_amendments.csv` (11,492 rows)
- `awards_documents.csv` (26,116 rows)
- `awards_items.csv` (50,776 rows)
- `awards_items_additionalClassifications.csv` (81,537 rows)
- `awards_items_deliveryAddresses.csv` (87,097 rows)
- `awards_milestones.csv` (21,603 rows)
- `awards_standstillPeriod.csv` (4 rows)
- `awards_subcontracting_subcontracts.csv` (689 rows)
- `awards_subcontracting_subcontracts_mainContractors.csv` (690 rows)
- `awards_suppliers.csv` (153,817 rows)

### bids.csv

**Child tables:**

- `bids_details.csv` (23,188 rows)
- `bids_details_tenderers.csv` (24,284 rows)
- `bids_statistics.csv` (117,709 rows)

### contracts.csv

- **Rows:** 70,470
- **Columns:** `id`, `dateSigned`, `status`, `awardID`, `value_amount`, `value_currency`, `main_ocid`, `main_id`, `title`, `period_endDate` ... (29 total)

**Child tables:**

- `contracts_agreedMetrics.csv` (11,063 rows)
- `contracts_agreedMetrics_observations.csv` (7,121 rows)
- `contracts_amendments.csv` (1,997 rows)
- `contracts_amendments_rationaleClassifications.csv` (185 rows)
- `contracts_amendments_suppliersRemoved.csv` (20 rows)
- `contracts_documents.csv` (44,264 rows)
- `contracts_implementation_metrics.csv` (142 rows)
- `contracts_implementation_metrics_observations.csv` (161 rows)
- `contracts_implementation_performanceFailures.csv` (7 rows)
- `contracts_implementation_performanceFailures_suppliers.csv` (7 rows)
- `contracts_items.csv` (1,328 rows)
- `contracts_items_additionalClassifications.csv` (628 rows)
- `contracts_items_deliveryAddresses.csv` (1,558 rows)
- `contracts_proposedAmendments.csv` (198 rows)
- `contracts_proposedAmendments_rationaleClassifications.csv` (169 rows)
- `contracts_proposedAmendments_suppliersAdded.csv` (15 rows)
- `contracts_proposedAmendments_suppliersRemoved.csv` (19 rows)
- `contracts_terminationRationaleClassifications.csv` (526 rows)

### links.csv

- **Rows:** 3,666
- **Columns:** `rel`, `href`, `main_ocid`, `main_id`

### main.csv

- **Rows:** 68,473
- **Columns:** `id`, `tag`, `language`, `date`, `ocid`, `description`, `initiationType`, `buyer_id`, `buyer_name`, `tender_id` ... (134 total)

### parties.csv

- **Rows:** 198,747
- **Columns:** `id`, `name`, `roles`, `address_region`, `address_locality`, `address_postalCode`, `address_countryName`, `address_streetAddress`, `details_url`, `details_buyerProfile` ... (30 total)

**Child tables:**

- `parties_additionalContactPoints.csv` (295 rows)
- `parties_additionalIdentifiers.csv` (40,586 rows)
- `parties_details_classifications.csv` (90,600 rows)

### planning.csv

**Child tables:**

- `planning_budget_finance.csv` (43 rows)
- `planning_documents.csv` (18,478 rows)
- `planning_milestones.csv` (8,725 rows)

### relatedProcesses.csv

- **Rows:** 2,018
- **Columns:** `id`, `uri`, `title`, `scheme`, `identifier`, `relationship`, `main_ocid`, `main_id`, `relatedLots`

### tender.csv

**Child tables:**

- `tender_additionalClassifications.csv` (244 rows)
- `tender_amendments.csv` (9,193 rows)
- `tender_amendments_unstructuredChanges.csv` (2,623 rows)
- `tender_amendments_unstructuredChanges_newValue_classifications.csv` (283 rows)
- `tender_amendments_unstructuredChanges_oldValue_classifications.csv` (117 rows)
- `tender_awardCriteria_criteria.csv` (91 rows)
- `tender_awardCriteria_criteria_numbers.csv` (74 rows)
- `tender_designContest_juryMembers.csv` (14 rows)
- `tender_documents.csv` (57,145 rows)
- `tender_items.csv` (56,732 rows)
- `tender_items_additionalClassifications.csv` (154,040 rows)
- `tender_items_deliveryAddresses.csv` (139,525 rows)
- `tender_legislativeReferences.csv` (1 rows)
- `tender_lots.csv` (87,303 rows)
- `tender_lots_awardCriteria_criteria.csv` (103,540 rows)
- `tender_lots_awardCriteria_criteria_numbers.csv` (56,585 rows)
- `tender_lots_identifiers.csv` (193 rows)
- `tender_lots_selectionCriteria_criteria.csv` (17,121 rows)
- `tender_milestones.csv` (3 rows)
- `tender_participationFees.csv` (1,067 rows)
- `tender_procurementMethodRationaleClassifications.csv` (11,478 rows)
- `tender_recurrence_dates.csv` (2,601 rows)
- `tender_selectionCriteria_criteria.csv` (2,903 rows)
- `tender_techniques_frameworkAgreement_buyerClassificationRestrictions.csv` (23 rows)
- `tender_techniques_frameworkAgreement_buyerLocationRestrictions.csv` (1,135 rows)

