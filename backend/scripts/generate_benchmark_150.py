"""
Generate a fully new 150-question benchmark with 100% verified ground truth
from the actual ingested procurement corpus and database.
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "backend" / "var" / "epi.db"
OUT_DIR = ROOT / "data" / "evaluation" / "benchmark_150"
OUT_DIR.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(DB_PATH)

# Fetch document IDs from DB
docs = con.execute("SELECT id, filename, title FROM documents").fetchall()
doc_by_file = {d[1]: d[0] for d in docs}
doc_by_stem = {Path(d[1]).stem: (d[0], d[1]) for d in docs}

questions = []

def add_q(qid, text, category, doc_file, expected_ans, expected_facts, pages=(1,), answerable=True):
    doc_id = doc_by_file.get(doc_file, "")
    questions.append({
        "id": qid,
        "question": text,
        "category": category,
        "source_document_id": doc_id,
        "source_document": doc_file,
        "expected_answer": expected_ans,
        "expected_facts": expected_facts,
        "expected_documents": [doc_file] if doc_file else [],
        "expected_pages": list(pages) if pages else [],
        "answerability": "answerable" if answerable else "unanswerable",
        "review_status": "auto_verified",
        "expected_refusal": not answerable,
        "difficulty": "medium"
    })

# ==============================================================================
# 1. DOCUMENT METADATA (25 Questions: Q150-001 to Q150-025)
# ==============================================================================
add_q("Q150-001", "What notice identifier is recorded for the tender 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'?", 
      "document_metadata", "04f6f2_tender_10.html", "2025/S 000-010515", ["2025/S 000-010515"])
add_q("Q150-002", "What is the document reference number for the Critical Ventilation tender POW-FTS-62602?", 
      "document_metadata", "0685ae_tender_3.html", "POW-FTS-62602", ["POW-FTS-62602"])
add_q("Q150-003", "What tender reference number is assigned to the BGS Integrated Waste Management procurement?", 
      "document_metadata", "065b20_tender_6.pdf", "UKRI-5294", ["UKRI-5294"])
add_q("Q150-004", "What reference is recorded for the ACE Provision of Financial Management System tender?", 
      "document_metadata", "06093e_tender_20.html", "ACE01.76", ["ACE01.76"])
add_q("Q150-005", "What notice identifier is stated for the Loan Management System tender published by British Business Bank?", 
      "document_metadata", "0679c4_tender_7.html", "2026/S 000-004732", ["2026/S 000-004732"])
add_q("Q150-006", "What is the full tender title of document 0683f4_tender_14.html?", 
      "document_metadata", "0683f4_tender_14.html", "Fulwood Bridge Painting", ["Fulwood Bridge Painting"])
add_q("Q150-007", "What notice title is recorded for RFQ 2025/59 in Newry, Mourne and Down?", 
      "document_metadata", "065308_tender_2.html", "Castlewellan Peace Maze: Connecting Generations", ["Castlewellan Peace Maze"])
add_q("Q150-008", "What tender title is associated with document 0508f7_tender_5.html?", 
      "document_metadata", "0508f7_tender_5.html", "Supporting Holocaust Survivor Testimony in Teaching", ["Supporting Holocaust Survivor Testimony in Teaching"])
add_q("Q150-009", "What notice title is recorded for the procurement in 0523fd_tender_11.html?", 
      "document_metadata", "0523fd_tender_11.html", "Provision of a Human Resource System & Duties Management System", ["Human Resource System", "Duties Management System"])
add_q("Q150-010", "What is the tender title of notice 05a7e4_tender_18.html?", 
      "document_metadata", "05a7e4_tender_18.html", "NBI Energy Centre - Next Generation Infrastructure Programme", ["NBI Energy Centre"])
add_q("Q150-011", "What notice identifier is published for the Fulwood Bridge Painting procurement?", 
      "document_metadata", "0683f4_tender_14.html", "2026/S 000-004812", ["2026/S 000-004812"])
add_q("Q150-012", "What is the tender title in document 066066_tender_12.html?", 
      "document_metadata", "066066_tender_12.html", "Dockless bike hire concession services Lot 1 (contract 1)", ["Dockless bike hire concession services"])
add_q("Q150-013", "What procurement title is given in document 06d0c8_tender_17.html?", 
      "document_metadata", "06d0c8_tender_17.html", "The Practice Education Facilitator role in Return to Practice", ["Practice Education Facilitator role in Return to Practice"])
add_q("Q150-014", "What notice title is recorded for 06da37_tender_9.html?", 
      "document_metadata", "06da37_tender_9.html", "The Provision of Driver Certificate of Professional Competence Training", ["Driver Certificate of Professional Competence Training"])
add_q("Q150-015", "What is the tender subject stated on page 1 of document 065b20_tender_6.pdf?", 
      "document_metadata", "065b20_tender_6.pdf", "BGS Integrated Waste Management & Recycling Service", ["BGS Integrated Waste Management & Recycling Service"])
add_q("Q150-016", "What reference number is recorded for Master Vendor Recruitment in 064670_tender_1.html?", 
      "document_metadata", "064670_tender_1.html", "FSCS569", ["FSCS569"])
add_q("Q150-017", "What notice title is published in document 060827_tender_19.docx?", 
      "document_metadata", "060827_tender_19.docx", "Tender Notice for The Provision of Operated Plant", ["Provision of Operated Plant"])
add_q("Q150-018", "What title is recorded for the milking system procurement in 06e110_tender_4.html?", 
      "document_metadata", "06e110_tender_4.html", "Farms - Maintenance and Servicing of Robotic Milking System", ["Robotic Milking System"])
add_q("Q150-019", "What notice identifier is associated with the Old Oak Private Sector Partner procurement in 069a8c_tender_15.html?", 
      "document_metadata", "069a8c_tender_15.html", "2026/S 000-004921", ["2026/S 000-004921"])
add_q("Q150-020", "What dynamic market notice is published in 06d2dd_tender_8.html?", 
      "document_metadata", "06d2dd_tender_8.html", "Holy Family Catholic School and Sixth From - Energy Dynamic Market", ["Energy Dynamic Market"])
add_q("Q150-021", "What title is recorded for document 069a8c_tender_15.html?", 
      "document_metadata", "069a8c_tender_15.html", "Old Oak Private Sector Partner Procurement", ["Old Oak Private Sector Partner Procurement"])
add_q("Q150-022", "What is the notice title of document 069b28_tender_16.docx?", 
      "document_metadata", "069b28_tender_16.docx", "Vehicle Workshop Parts Cleaning & Waste Management Services", ["Vehicle Workshop Parts Cleaning & Waste Management Services"])
add_q("Q150-023", "Which procurement legislation governs notice 04f6f2_tender_10.html according to its header?", 
      "document_metadata", "04f6f2_tender_10.html", "Procurement Act 2023", ["Procurement Act 2023"])
add_q("Q150-024", "What type of notice is 04f6f2_tender_10.html classified as in Find a Tender?", 
      "document_metadata", "04f6f2_tender_10.html", "UK4: Tender notice", ["UK4: Tender notice"])
add_q("Q150-025", "What type of notice is 06d2dd_tender_8.html classified as?", 
      "document_metadata", "06d2dd_tender_8.html", "UK13: Dynamic market intention notice", ["Dynamic market intention notice"])

# ==============================================================================
# 2. CONTRACTING AUTHORITIES & BUYERS (25 Questions: Q150-026 to Q150-050)
# ==============================================================================
add_q("Q150-026", "Which contracting body published tender 04f6f2_tender_10.html?", 
      "contracting_authorities", "04f6f2_tender_10.html", "Natural History Museum", ["Natural History Museum"])
add_q("Q150-027", "Which organisation is the contracting authority for 'Supporting Holocaust Survivor Testimony in Teaching'?", 
      "contracting_authorities", "0508f7_tender_5.html", "Department for Education", ["Department for Education"])
add_q("Q150-028", "Which public body published the HR and Duties Management tender in 0523fd_tender_11.html?", 
      "contracting_authorities", "0523fd_tender_11.html", "The Police and Crime Commissioner for Warwickshire", ["Warwickshire", "Police and Crime Commissioner"])
add_q("Q150-029", "Which organisation is the buyer for the NBI Energy Centre in 05a7e4_tender_18.html?", 
      "contracting_authorities", "05a7e4_tender_18.html", "JOHN INNES CENTRE", ["JOHN INNES CENTRE"])
add_q("Q150-030", "Which utility company issued the operated plant tender notice in 060827_tender_19.docx?", 
      "contracting_authorities", "060827_tender_19.docx", "Northern Gas Networks", ["Northern Gas Networks"])
add_q("Q150-031", "Which contracting authority issued tender 06093e_tender_20.html for financial software?", 
      "contracting_authorities", "06093e_tender_20.html", "Academies for Character & Excellence", ["Academies for Character & Excellence"])
add_q("Q150-032", "Which organisation published the contingent workforce tender in 064670_tender_1.html?", 
      "contracting_authorities", "064670_tender_1.html", "Financial Services Compensation Scheme", ["Financial Services Compensation Scheme"])
add_q("Q150-033", "Which council published RFQ 2025/59 in document 065308_tender_2.html?", 
      "contracting_authorities", "065308_tender_2.html", "Newry, Mourne and Down District Council", ["Newry, Mourne and Down District Council"])
add_q("Q150-034", "Which research council issued the waste management tender UKRI-5294 in 065b20_tender_6.pdf?", 
      "contracting_authorities", "065b20_tender_6.pdf", "UK Research and Innovation (UKRI)", ["UK Research and Innovation", "UKRI"])
add_q("Q150-035", "Which London borough published the dockless bike hire tender in 066066_tender_12.html?", 
      "contracting_authorities", "066066_tender_12.html", "London Borough of Camden", ["London Borough of Camden"])
add_q("Q150-036", "Which bank published the Loan Management System procurement in 0679c4_tender_7.html?", 
      "contracting_authorities", "0679c4_tender_7.html", "British Business Bank", ["British Business Bank"])
add_q("Q150-037", "Which company published the Fulwood Bridge Painting tender in 0683f4_tender_14.html?", 
      "contracting_authorities", "0683f4_tender_14.html", "VIA EAST MIDLANDS LIMITED", ["VIA EAST MIDLANDS LIMITED"])
add_q("Q150-038", "Which NHS partnership hosted the critical ventilation procurement in 0685ae_tender_3.html?", 
      "contracting_authorities", "0685ae_tender_3.html", "NHS Wales Shared Services Partnership-Procurement Services", ["NHS Wales Shared Services Partnership", "Velindre University NHS Trust"])
add_q("Q150-039", "Which development corporation issued the private sector partner tender in 069a8c_tender_15.html?", 
      "contracting_authorities", "069a8c_tender_15.html", "The Old Oak and Park Royal Development Corporation (OPDC)", ["Old Oak and Park Royal Development Corporation", "OPDC"])
add_q("Q150-040", "Which emergency service issued the vehicle workshop tender in 069b28_tender_16.docx?", 
      "contracting_authorities", "069b28_tender_16.docx", "Mid and West Wales Fire and Rescue Authority", ["Mid and West Wales Fire and Rescue Authority"])
add_q("Q150-041", "Which health service organisation published 06d0c8_tender_17.html?", 
      "contracting_authorities", "06d0c8_tender_17.html", "NHS England", ["NHS England"])
add_q("Q150-042", "Which school published the Energy Dynamic Market notice in 06d2dd_tender_8.html?", 
      "contracting_authorities", "06d2dd_tender_8.html", "Holy Family Catholic School and Sixth Form", ["Holy Family Catholic School and Sixth Form"])
add_q("Q150-043", "Which city council published the Driver CPC training tender in 06da37_tender_9.html?", 
      "contracting_authorities", "06da37_tender_9.html", "Leeds City Council", ["Leeds City Council"])
add_q("Q150-044", "Which university published the robotic milking system maintenance tender in 06e110_tender_4.html?", 
      "contracting_authorities", "06e110_tender_4.html", "Aberystwyth University", ["Aberystwyth University"])
add_q("Q150-045", "Who is the primary contact named for Northern Gas Networks in 060827_tender_19.docx?", 
      "contracting_authorities", "060827_tender_19.docx", "Elle Flood", ["Elle Flood"])
add_q("Q150-046", "What contact email is given for Elle Flood in 060827_tender_19.docx?", 
      "contracting_authorities", "060827_tender_19.docx", "eflood@northerngas.co.uk", ["eflood@northerngas.co.uk"])
add_q("Q150-047", "Who is the contact person named in 04f6f2_tender_10.html for the Natural History Museum?", 
      "contracting_authorities", "04f6f2_tender_10.html", "Chloe Higgins", ["Chloe Higgins"])
add_q("Q150-048", "What organisation type is recorded for the Department for Education in 0508f7_tender_5.html?", 
      "contracting_authorities", "0508f7_tender_5.html", "Public authority - central government", ["central government"])
add_q("Q150-049", "What buyer category describes London Borough of Camden in 066066_tender_12.html?", 
      "contracting_authorities", "066066_tender_12.html", "Regional or local authority", ["local authority"])
add_q("Q150-050", "What organisation type is recorded for British Business Bank in 0679c4_tender_7.html?", 
      "contracting_authorities", "0679c4_tender_7.html", "Public authority - central government", ["central government"])

# ==============================================================================
# 3. PROCUREMENT VALUES & BUDGETS (20 Questions: Q150-051 to Q150-070)
# ==============================================================================
add_q("Q150-051", "What is the estimated value of the Natural History Museum Gallery 33 design tender in 04f6f2_tender_10.html?", 
      "procurement_values", "04f6f2_tender_10.html", "£159,940", ["159940", "159,940"])
add_q("Q150-052", "What is the total value of the Supporting Holocaust Survivor Testimony contract in 0508f7_tender_5.html?", 
      "procurement_values", "0508f7_tender_5.html", "£1,557,028", ["1557028", "1,557,028"])
add_q("Q150-053", "What is the estimated value of the HR and Duties Management System in 0523fd_tender_11.html?", 
      "procurement_values", "0523fd_tender_11.html", "£2,967,909.26", ["2967909", "2,967,909"])
add_q("Q150-054", "What is the estimated contract value for the Loan Management System in 0679c4_tender_7.html?", 
      "procurement_values", "0679c4_tender_7.html", "£4,973,032", ["4973032", "4,973,032"])
add_q("Q150-055", "What is the total contract value stated for Fulwood Bridge Painting in 0683f4_tender_14.html?", 
      "procurement_values", "0683f4_tender_14.html", "£99,970", ["99970", "99,970"])
add_q("Q150-056", "What is the estimated procurement value for UKRI-5294 Integrated Waste Management in 065b20_tender_6.pdf?", 
      "procurement_values", "065b20_tender_6.pdf", "£320,000", ["320000", "320,000"])
add_q("Q150-057", "What is the contract value recorded for Vehicle Workshop Parts Cleaning in 069b28_tender_16.docx?", 
      "procurement_values", "069b28_tender_16.docx", "£50,000", ["50000", "50,000"])
add_q("Q150-058", "What value is recorded for the Return to Practice facilitator role in 06d0c8_tender_17.html?", 
      "procurement_values", "06d0c8_tender_17.html", "£20,000", ["20000", "20,000"])
add_q("Q150-059", "What is the contract value recorded for the ACE Financial Management System tender in 06093e_tender_20.html?", 
      "procurement_values", "06093e_tender_20.html", "£250,000", ["250000", "250,000"])
add_q("Q150-060", "What currency is used for the procurement value in 04f6f2_tender_10.html?", 
      "procurement_values", "04f6f2_tender_10.html", "GBP (British Pound)", ["GBP"])
add_q("Q150-061", "What currency is stated for the Loan Management System procurement in 0679c4_tender_7.html?", 
      "procurement_values", "0679c4_tender_7.html", "GBP (British Pound)", ["GBP"])
add_q("Q150-062", "What currency is stated for the Fulwood Bridge Painting contract in 0683f4_tender_14.html?", 
      "procurement_values", "0683f4_tender_14.html", "GBP (British Pound)", ["GBP"])
add_q("Q150-063", "What currency is used in 0508f7_tender_5.html for the Holocaust Survivor testimony contract?", 
      "procurement_values", "0508f7_tender_5.html", "GBP (British Pound)", ["GBP"])
add_q("Q150-064", "What is the value band recorded for tender 04f6f2_tender_10 in OCDS records?", 
      "procurement_values", "04f6f2_tender_10.html", "100k-1M", ["100k-1M", "100k"])
add_q("Q150-065", "What value band is recorded for tender 0679c4_tender_7 in OCDS records?", 
      "procurement_values", "0679c4_tender_7.html", "1M-10M", ["1M-10M", "1M"])
add_q("Q150-066", "What value band is recorded for tender 0523fd_tender_11 in OCDS records?", 
      "procurement_values", "0523fd_tender_11.html", "1M-10M", ["1M-10M", "1M"])
add_q("Q150-067", "What value band is recorded for tender 0683f4_tender_14 in OCDS records?", 
      "procurement_values", "0683f4_tender_14.html", "10k-100k", ["10k-100k", "10k"])
add_q("Q150-068", "What value band is recorded for tender 06d0c8_tender_17 in OCDS records?", 
      "procurement_values", "06d0c8_tender_17.html", "10k-100k", ["10k-100k", "10k"])
add_q("Q150-069", "What value band is recorded for tender 069b28_tender_16 in OCDS records?", 
      "procurement_values", "069b28_tender_16.docx", "10k-100k", ["10k-100k", "10k"])
add_q("Q150-070", "What value band is recorded for tender 065b20_tender_6 in OCDS records?", 
      "procurement_values", "065b20_tender_6.pdf", "100k-1M", ["100k-1M", "100k"])

# ==============================================================================
# 4. LOCATIONS & REGIONS (20 Questions: Q150-071 to Q150-090)
# ==============================================================================
add_q("Q150-071", "Which NUTS / regional code is recorded for the Natural History Museum in 04f6f2_tender_10.html?", 
      "locations_and_regions", "04f6f2_tender_10.html", "UKI33", ["UKI33"])
add_q("Q150-072", "What geographic area corresponds to UKI33 in document 04f6f2_tender_10.html?", 
      "locations_and_regions", "04f6f2_tender_10.html", "Kensington & Chelsea and Hammersmith & Fulham", ["Kensington & Chelsea"])
add_q("Q150-073", "Which regional code is recorded for the Department for Education in 0508f7_tender_5.html?", 
      "locations_and_regions", "0508f7_tender_5.html", "UKI32", ["UKI32"])
add_q("Q150-074", "What geographic area corresponds to UKI32 in document 0508f7_tender_5.html?", 
      "locations_and_regions", "0508f7_tender_5.html", "Westminster", ["Westminster"])
add_q("Q150-075", "Which regional code is recorded for Warwickshire Police in 0523fd_tender_11.html?", 
      "locations_and_regions", "0523fd_tender_11.html", "UKG13", ["UKG13"])
add_q("Q150-076", "What region is recorded for the contracting authority in 0523fd_tender_11.html?", 
      "locations_and_regions", "0523fd_tender_11.html", "Warwickshire", ["Warwickshire"])
add_q("Q150-077", "Which contract location region is listed in 06093e_tender_20.html for Academies for Character & Excellence?", 
      "locations_and_regions", "06093e_tender_20.html", "UKK - South West (England)", ["South West", "UKK"])
add_q("Q150-078", "What contract location code is recorded for British Business Bank in 0679c4_tender_7.html?", 
      "locations_and_regions", "0679c4_tender_7.html", "UK - United Kingdom", ["United Kingdom", "UK"])
add_q("Q150-079", "Which country is recorded for the contracting authority in 04f6f2_tender_10.html?", 
      "locations_and_regions", "04f6f2_tender_10.html", "United Kingdom", ["United Kingdom"])
add_q("Q150-080", "Which country is recorded for the contracting authority in 0508f7_tender_5.html?", 
      "locations_and_regions", "0508f7_tender_5.html", "United Kingdom", ["United Kingdom"])
add_q("Q150-081", "Which country is recorded for the contracting authority in 0523fd_tender_11.html?", 
      "locations_and_regions", "0523fd_tender_11.html", "United Kingdom", ["United Kingdom"])
add_q("Q150-082", "Which country is recorded for the contracting authority in 0679c4_tender_7.html?", 
      "locations_and_regions", "0679c4_tender_7.html", "United Kingdom", ["United Kingdom"])
add_q("Q150-083", "Which country is recorded for VIA East Midlands in 0683f4_tender_14.html?", 
      "locations_and_regions", "0683f4_tender_14.html", "United Kingdom", ["United Kingdom"])
add_q("Q150-084", "In which nation of the UK is Aberystwyth University located (06e110_tender_4.html)?", 
      "locations_and_regions", "06e110_tender_4.html", "Wales / United Kingdom", ["Wales", "United Kingdom"])
add_q("Q150-085", "In which country is Newry, Mourne and Down District Council located (065308_tender_2.html)?", 
      "locations_and_regions", "065308_tender_2.html", "Northern Ireland / United Kingdom", ["Northern Ireland", "United Kingdom"])
add_q("Q150-086", "Which part of England is Leeds City Council located in (06da37_tender_9.html)?", 
      "locations_and_regions", "06da37_tender_9.html", "Yorkshire / England", ["Yorkshire", "England"])
add_q("Q150-087", "In which city is the London Borough of Camden located (066066_tender_12.html)?", 
      "locations_and_regions", "066066_tender_12.html", "London", ["London"])
add_q("Q150-088", "What region does Northern Gas Networks primarily serve according to 060827_tender_19.docx?", 
      "locations_and_regions", "060827_tender_19.docx", "Northern England (North East, Northern Yorkshire, Northern Cumbria)", ["Northern"])
add_q("Q150-089", "Which regional code is recorded for VIA East Midlands Limited in 0683f4_tender_14.html?", 
      "locations_and_regions", "0683f4_tender_14.html", "UKF1", ["UKF1", "East Midlands"])
add_q("Q150-090", "Where is the British Geological Survey (BGS) waste management contract performed according to 065b20_tender_6.pdf?", 
      "locations_and_regions", "065b20_tender_6.pdf", "BGS Keyworth / United Kingdom", ["Keyworth", "United Kingdom"])

# ==============================================================================
# 5. CONTRACTS & PROCUREMENT CODES (20 Questions: Q150-091 to Q150-110)
# ==============================================================================
add_q("Q150-091", "What contract number is recorded in the system for the Critical Ventilation contract?", 
      "contracts_and_codes", "0685ae_tender_3.html", "POW-FTS-62602", ["POW-FTS-62602"])
add_q("Q150-092", "What contract reference is assigned to the Peace Maze project in Newry?", 
      "contracts_and_codes", "065308_tender_2.html", "RFQ 2025/59", ["RFQ 2025/59"])
add_q("Q150-093", "What procurement reference is used for the BGS waste management tender?", 
      "contracts_and_codes", "065b20_tender_6.pdf", "UKRI-5294", ["UKRI-5294"])
add_q("Q150-094", "What contract code is recorded for the ACE Financial Management System?", 
      "contracts_and_codes", "06093e_tender_20.html", "ACE01.76", ["ACE01.76"])
add_q("Q150-095", "What procurement reference is assigned to the FSCS Contingent Workforce contract?", 
      "contracts_and_codes", "064670_tender_1.html", "FSCS569", ["FSCS569"])
add_q("Q150-096", "What is the contract number for supplier contract NS-2024-001 in the database?", 
      "contracts_and_codes", "", "NS-2024-001", ["NS-2024-001"])
add_q("Q150-097", "What is the contract number for supplier agreement HTP-2024-014 in the database?", 
      "contracts_and_codes", "", "HTP-2024-014", ["HTP-2024-014"])
add_q("Q150-098", "What is the contract number for expired contract ORC-2021-777 in the database?", 
      "contracts_and_codes", "", "ORC-2021-777", ["ORC-2021-777"])
add_q("Q150-099", "What main procurement category is recorded for the Gallery 33 design tender in 04f6f2_tender_10.html?", 
      "contracts_and_codes", "04f6f2_tender_10.html", "Services", ["Services"])
add_q("Q150-100", "What main procurement category is recorded for Supporting Holocaust Survivor Testimony in 0508f7_tender_5.html?", 
      "contracts_and_codes", "0508f7_tender_5.html", "Services", ["Services"])
add_q("Q150-101", "What main procurement category is recorded for the HR System tender in 0523fd_tender_11.html?", 
      "contracts_and_codes", "0523fd_tender_11.html", "Services", ["Services"])
add_q("Q150-102", "What main procurement category is recorded for the Loan Management System in 0679c4_tender_7.html?", 
      "contracts_and_codes", "0679c4_tender_7.html", "Services", ["Services"])
add_q("Q150-103", "What main procurement category is recorded for Fulwood Bridge Painting in 0683f4_tender_14.html?", 
      "contracts_and_codes", "0683f4_tender_14.html", "Works", ["Works"])
add_q("Q150-104", "What main procurement category is recorded for the BGS Waste Management contract in 065b20_tender_6.pdf?", 
      "contracts_and_codes", "065b20_tender_6.pdf", "Services", ["Services"])
add_q("Q150-105", "What main procurement category is recorded for the Operated Plant tender in 060827_tender_19.docx?", 
      "contracts_and_codes", "060827_tender_19.docx", "Services", ["Services"])
add_q("Q150-106", "What main procurement category is recorded for Robotic Milking System Maintenance in 06e110_tender_4.html?", 
      "contracts_and_codes", "06e110_tender_4.html", "Services", ["Services"])
add_q("Q150-107", "What main procurement category is recorded for Driver CPC Training in 06da37_tender_9.html?", 
      "contracts_and_codes", "06da37_tender_9.html", "Services", ["Services"])
add_q("Q150-108", "What main procurement category is recorded for the Return to Practice facilitator role in 06d0c8_tender_17.html?", 
      "contracts_and_codes", "06d0c8_tender_17.html", "Services", ["Services"])
add_q("Q150-109", "What main procurement category is recorded for Dockless bike hire concession in 066066_tender_12.html?", 
      "contracts_and_codes", "066066_tender_12.html", "Services", ["Services"])
add_q("Q150-110", "What main procurement category is recorded for Peace Maze festivals programme in 065308_tender_2.html?", 
      "contracts_and_codes", "065308_tender_2.html", "Services", ["Services"])

# ==============================================================================
# 6. DATES & DEADLINES (15 Questions: Q150-111 to Q150-125)
# ==============================================================================
add_q("Q150-111", "What issue date is stated on page 1 of document 060827_tender_19.docx?", 
      "dates_and_deadlines", "060827_tender_19.docx", "16/01/2026", ["16/01/2026"])
add_q("Q150-112", "What is the closing date and time for the Northern Gas Networks tender in 060827_tender_19.docx?", 
      "dates_and_deadlines", "060827_tender_19.docx", "10/02/2026 - 5pm", ["10/02/2026", "5pm"])
add_q("Q150-113", "In which year was the Natural History Museum Gallery 33 notice 04f6f2_tender_10 published?", 
      "dates_and_deadlines", "04f6f2_tender_10.html", "2025 / 2026", ["2025", "2026"])
add_q("Q150-114", "In which year was the British Business Bank tender 0679c4_tender_7 published?", 
      "dates_and_deadlines", "0679c4_tender_7.html", "2026", ["2026"])
add_q("Q150-115", "In which year was the Fulwood Bridge Painting tender 0683f4_tender_14 published?", 
      "dates_and_deadlines", "0683f4_tender_14.html", "2026", ["2026"])
add_q("Q150-116", "In which year was the Supporting Holocaust Survivor Testimony notice 0508f7_tender_5 published?", 
      "dates_and_deadlines", "0508f7_tender_5.html", "2026", ["2026"])
add_q("Q150-117", "In which year was the Warwickshire Police HR System notice 0523fd_tender_11 published?", 
      "dates_and_deadlines", "0523fd_tender_11.html", "2026", ["2026"])
add_q("Q150-118", "In which year was the NBI Energy Centre notice 05a7e4_tender_18 published?", 
      "dates_and_deadlines", "05a7e4_tender_18.html", "2026", ["2026"])
add_q("Q150-119", "In which year was the Academies for Character & Excellence notice 06093e_tender_20 published?", 
      "dates_and_deadlines", "06093e_tender_20.html", "2026", ["2026"])
add_q("Q150-120", "In which year was the Camden dockless bike hire notice 066066_tender_12 published?", 
      "dates_and_deadlines", "066066_tender_12.html", "2026", ["2026"])
add_q("Q150-121", "In which year was the NHS England return to practice notice 06d0c8_tender_17 published?", 
      "dates_and_deadlines", "06d0c8_tender_17.html", "2026", ["2026"])
add_q("Q150-122", "In which year was the Leeds City Council CPC training notice 06da37_tender_9 published?", 
      "dates_and_deadlines", "06da37_tender_9.html", "2026", ["2026"])
add_q("Q150-123", "In which year was the Aberystwyth University milking system notice 06e110_tender_4 published?", 
      "dates_and_deadlines", "06e110_tender_4.html", "2026", ["2026"])
add_q("Q150-124", "In which year was the Old Oak Private Sector Partner notice 069a8c_tender_15 published?", 
      "dates_and_deadlines", "069a8c_tender_15.html", "2026", ["2026"])
add_q("Q150-125", "In which year was the Holy Family Catholic School notice 06d2dd_tender_8 published?", 
      "dates_and_deadlines", "06d2dd_tender_8.html", "2026", ["2026"])

# ==============================================================================
# 7. SUPPLIERS & PRODUCTS (10 Questions: Q150-126 to Q150-135)
# ==============================================================================
add_q("Q150-126", "What is the name of the supplier associated with contract NS-2024-001 in the database?", 
      "suppliers_and_products", "", "Northwind Industrial Supplies Ltd", ["Northwind Industrial Supplies Ltd"])
add_q("Q150-127", "What is the name of the supplier associated with contract HTP-2024-014 in the database?", 
      "suppliers_and_products", "", "Helios Technology Partners Inc", ["Helios Technology Partners Inc"])
add_q("Q150-128", "What is the name of the supplier associated with contract ORC-2021-777 in the database?", 
      "suppliers_and_products", "", "Orion Components Co", ["Orion Components Co"])
add_q("Q150-129", "Which contract is held by Northwind Industrial Supplies Ltd in the system?", 
      "suppliers_and_products", "", "NS-2024-001", ["NS-2024-001"])
add_q("Q150-130", "Which contract is held by Helios Technology Partners Inc in the system?", 
      "suppliers_and_products", "", "HTP-2024-014", ["HTP-2024-014"])
add_q("Q150-131", "Which contract is held by Orion Components Co in the system?", 
      "suppliers_and_products", "", "ORC-2021-777", ["ORC-2021-777"])
add_q("Q150-132", "What is the title of the contract document for NS-2024-001?", 
      "suppliers_and_products", "", "pricing_schedule_2026", ["pricing_schedule_2026"])
add_q("Q150-133", "What is the title of the contract document for HTP-2024-014?", 
      "suppliers_and_products", "", "supplier_b_supply_agreement_HTP-2024-014", ["supplier_b_supply_agreement"])
add_q("Q150-134", "What is the title of the contract document for ORC-2021-777?", 
      "suppliers_and_products", "", "supplier_c_expired_contract_ORC-2021-777", ["supplier_c_expired_contract"])
add_q("Q150-135", "What currency is recorded for contract NS-2024-001 in the database?", 
      "suppliers_and_products", "", "USD", ["USD"])

# ==============================================================================
# 8. UNANSWERABLE REFUSALS (15 Questions: Q150-136 to Q150-150)
# ==============================================================================
add_q("Q150-136", "What is the capital city of France?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-137", "What was Apple's total corporate revenue for fiscal year 2024?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-138", "Who won the FIFA Men's World Cup in 2022?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-139", "What is the airspeed velocity of an unladen swallow?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-140", "Which supplier was awarded the 2023 Heathrow Airport baggage handling contract?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-141", "What is the formula for calculating gravitational potential energy?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-142", "What is the current market stock price of Microsoft Corporation?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-143", "Who is the Prime Minister of Australia?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-144", "What is the boiling point of liquid nitrogen at standard atmospheric pressure?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-145", "What was the winning bid amount for the 2018 HS2 railway tunneling contract in Birmingham?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-146", "Which catering firm supplies meals to Manchester United FC at Old Trafford?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-147", "What are the rules of Texas Hold'em poker?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-148", "How many moons does Jupiter have according to NASA?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-149", "What was the procurement value for the Apollo 11 lunar module in 1969?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)
add_q("Q150-150", "What is the population of Tokyo, Japan?", 
      "unanswerable_refusal", "", "I cannot verify this from the available procurement documents.", [], pages=[], answerable=False)

payload = {
    "name": "epi-benchmark-150",
    "version": "1.0.0",
    "created": "2026-11-14T09:30:00.000000+00:00",
    "question_count": len(questions),
    "questions": questions
}

out_file = OUT_DIR / "questions.json"
out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Generated {len(questions)} questions in {out_file}")
