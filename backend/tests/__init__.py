# backend/tests
# Test suite for the Enterprise Procurement Intelligence backend.
#
# Structure:
#   unit/         — pure unit tests, no I/O, no DB
#   integration/  — FastAPI TestClient tests against SQLite in-memory DB
#   retrieval/    — retrieval pipeline regression tests
#   ingestion/    — ingestion pipeline tests
#   security/     — auth, RBAC, injection guard tests
#
# Run: pytest tests/ -q
# See COMMITS.md for the implementation roadmap (TEST-1 through TEST-5).
