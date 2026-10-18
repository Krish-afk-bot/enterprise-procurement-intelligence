# Security Operations Guide

## Authorization Audit Logging

### Overview
All authorization failures (403 Forbidden responses) are automatically logged to the `audit_logs` table for compliance review. This implements GAP-1 from the Phase 7.2 security audit.

### What is Logged
- **Action**: `security.access_denied`
- **Tenant ID**: The tenant of the user who was denied access
- **User ID**: The user who was denied access
- **Resource Type**: The type of resource accessed (if available in error details)
- **Resource ID**: The specific resource ID (if available in error details)
- **Outcome**: `denied`
- **IP Address**: The client IP address (respects X-Forwarded-For)
- **Detail**: Contains the error code and reason message
- **Request ID**: Correlates with application logs

### Implementation
Authorization audit logging is implemented in `app/api/errors.py` in the `AppError` exception handler. When an `AuthorizationError` (or subclass like `TenantIsolationError`) is raised:

1. The error handler extracts the Principal from the JWT token
2. Creates an audit log entry with action `ACTION_ACCESS_DENIED`
3. Commits the audit entry in a separate session scope
4. Returns the error response to the client

If audit logging fails, the failure is logged to application logs but does not affect the error response.

### Querying Audit Logs
```python
from app.security.audit import recent_audit_entries, ACTION_ACCESS_DENIED

# Get recent access denials for a tenant
async with session_scope() as session:
    denials = await recent_audit_entries(
        session,
        tenant_id="tenant-123",
        action=ACTION_ACCESS_DENIED,
        limit=100
    )
    for entry in denials:
        print(f"{entry.created_at}: {entry.user_id} denied {entry.resource_type}/{entry.resource_id}")
```

### SQL Query Example
```sql
SELECT 
    created_at,
    user_id,
    resource_type,
    resource_id,
    detail,
    ip_address,
    request_id
FROM audit_logs
WHERE tenant_id = 'tenant-123'
  AND action = 'security.access_denied'
  AND outcome = 'denied'
ORDER BY created_at DESC
LIMIT 100;
```

## Answer Caching Status

### Current Implementation
As of Phase 7.2B, **answer caching is not implemented**. The cache provider (`app/providers/cache.py`) exists and is connected to the container, but the answer pipeline does not cache query results.

### Why GAP-2 is Not Applicable
The Phase 7.2 audit identified GAP-2 as "document deletion doesn't invalidate cached answers." However, since answers are never cached, there is nothing to invalidate. Each query:
1. Retrieves documents from Qdrant vector store
2. Runs the agent pipeline
3. Generates a new answer
4. Persists to `query_records` and `answer_records` tables

### Future Implementation Considerations
When answer caching is implemented:
- Cache keys MUST be scoped to `tenant_id:user_id` to prevent cross-tenant leakage (see `scoped_key()` in `cache.py`)
- Document deletion MUST call `cache.clear_prefix(f"{tenant_id}:")` to invalidate all cached answers for that tenant
- Alternative: Track document IDs in cache keys (e.g., `tenant:user:query_hash:doc_ids`) for fine-grained invalidation

## Vector Store Consistency (GAP-3)

### Known Limitation
Document re-indexing may leave orphaned vectors in Qdrant if the indexing process fails partway through.

### Failure Scenarios
1. **Partial chunk deletion**: Old chunks deleted, new chunks fail to upload
2. **Network interruption**: Connection lost mid-upload
3. **Qdrant service failure**: Service unavailable during delete or upsert

### Current Behavior
The ingestion pipeline (`app/ingestion/pipeline.py`):
- Deletes old vectors using `delete_document_chunks(document_id)`
- Uploads new chunks using `upsert_chunks()`
- Logs errors but does not rollback vector operations (no transactional guarantee)

### Mitigation Strategies
1. **Manual cleanup**: Use Qdrant API to list all points and compare with PostgreSQL document IDs
2. **Periodic reconciliation**: Schedule a job to find orphaned vectors and delete them
3. **Soft delete**: Keep old vectors with a `deleted_at` metadata field, clean up later

### Reconciliation Script Example
```python
async def reconcile_vectors(tenant_id: str):
    """Find and delete orphaned vectors for a tenant."""
    from app.db.session import session_scope
    from app.db.models import DocumentChunk
    from app.providers.vector.qdrant import get_qdrant_client
    
    async with session_scope() as session:
        # Get all chunk IDs from PostgreSQL
        result = await session.execute(
            select(DocumentChunk.id).where(DocumentChunk.tenant_id == tenant_id)
        )
        db_chunk_ids = {row[0] for row in result}
        
        # Get all point IDs from Qdrant
        qdrant = get_qdrant_client()
        collection = f"tenant_{tenant_id}_chunks"
        scroll_result = qdrant.scroll(collection, limit=10000)
        qdrant_ids = {point.id for point in scroll_result[0]}
        
        # Find orphans
        orphans = qdrant_ids - db_chunk_ids
        
        if orphans:
            print(f"Found {len(orphans)} orphaned vectors, deleting...")
            qdrant.delete(collection, points_selector=list(orphans))
```

## Tenant Quotas (GAP-4)

### Architectural Limitation
Per-tenant upload quotas and document count limits are **not enforced** at the application layer. This is an architectural decision with the following tradeoffs:

### Why Not Implemented
1. **Storage is cheap**: MinIO and PostgreSQL storage costs are low relative to compute
2. **Trust model**: Enterprise customers are trusted to self-govern usage
3. **Operational complexity**: Quota enforcement requires background jobs, soft/hard limits, grace periods
4. **Scalability**: Checking quotas on every upload adds latency and complexity

### Risks
- **Storage exhaustion**: A single tenant could fill disk space
- **Cost overruns**: Vector embeddings and LLM API costs scale with document count
- **Performance degradation**: Large document counts may slow retrieval

### Recommended Controls
1. **Infrastructure-level limits**: Use MinIO bucket quotas or filesystem quotas
2. **Monitoring**: Alert on tenant storage growth rates
3. **Billing integration**: Charge per-document or per-GB to create economic incentives
4. **Manual intervention**: Disable ingestion for abusive tenants

### Configuration (if implemented)
Add to `app/config/settings.py`:
```python
max_documents_per_tenant: int = 10000
max_storage_mb_per_tenant: int = 50000  # 50 GB
```

## Ingestion Concurrency (GAP-5)

### Current Architecture
The ingestion system uses a **single background worker** processing jobs from a Redis queue (`/app/workers/ingestion_worker.py`). This design:
- Processes one document at a time per worker instance
- Prevents resource contention on embedding generation and vector upload
- Simplifies error handling and retry logic

### Why Single Worker is Acceptable
1. **Controlled load**: Prevents overwhelming LLM embedding APIs
2. **Cost predictability**: Embedding API costs are linear with time
3. **Database safety**: No concurrent writes to the same document
4. **Horizontal scaling**: Deploy multiple worker containers if needed

### Horizontal Scaling
To increase throughput:
```bash
# Deploy multiple worker containers
docker-compose up --scale ingestion-worker=3
```

Each worker:
- Polls the Redis queue independently
- Processes different documents in parallel
- No shared state or coordination needed

### Risks of Unbounded Parallelism
- **Embedding API rate limits**: OpenAI/Cohere have rate limits per account
- **Database connection exhaustion**: Each worker needs a DB connection pool
- **Memory pressure**: Large PDFs can consume 500MB+ during processing

### Monitoring
Track these metrics to decide if more workers are needed:
- `ingestion_queue_depth`: Number of pending jobs
- `ingestion_latency_p95`: 95th percentile processing time
- `ingestion_error_rate`: Failure rate per document

## Backup and Restore Procedures

### PostgreSQL Database

#### Backup
```bash
# Full database backup
pg_dump -h localhost -U epi_user -d epi_db -F c -b -v -f epi_backup_$(date +%Y%m%d_%H%M%S).dump

# Tenant-specific backup (using tenant_id filter)
pg_dump -h localhost -U epi_user -d epi_db -F c -b -v \
  -t documents -t document_chunks -t prices -t suppliers -t products -t contracts \
  --where="tenant_id='tenant-123'" \
  -f tenant_123_backup_$(date +%Y%m%d).dump
```

#### Restore
```bash
# Full restore (drop existing database first)
dropdb -h localhost -U epi_user epi_db
createdb -h localhost -U epi_user epi_db
pg_restore -h localhost -U epi_user -d epi_db -v epi_backup_20241019_120000.dump

# Partial restore (merge into existing database)
pg_restore -h localhost -U epi_user -d epi_db -v --data-only --disable-triggers tenant_123_backup_20241019.dump
```

### Qdrant Vector Store

#### Backup
```bash
# Qdrant provides snapshot API
curl -X POST "http://localhost:6333/collections/{collection_name}/snapshots"

# Download snapshot
curl -X GET "http://localhost:6333/collections/{collection_name}/snapshots/{snapshot_name}" \
  -o qdrant_snapshot_$(date +%Y%m%d).tar.gz
```

#### Restore
```bash
# Upload snapshot to Qdrant
curl -X PUT "http://localhost:6333/collections/{collection_name}/snapshots/upload" \
  -F "snapshot=@qdrant_snapshot_20241019.tar.gz"

# Recover collection from snapshot
curl -X PUT "http://localhost:6333/collections/{collection_name}/snapshots/{snapshot_name}/recover"
```

### Neo4j Graph Database

#### Backup
```bash
# Stop Neo4j first
docker-compose stop neo4j

# Copy data directory
tar -czf neo4j_backup_$(date +%Y%m%d).tar.gz /var/lib/neo4j/data

# Or use neo4j-admin dump (requires Neo4j Enterprise)
neo4j-admin database dump neo4j --to=/backups/neo4j_$(date +%Y%m%d).dump
```

#### Restore
```bash
# Stop Neo4j
docker-compose stop neo4j

# Extract backup
tar -xzf neo4j_backup_20241019.tar.gz -C /var/lib/neo4j/data

# Or use neo4j-admin load
neo4j-admin database load neo4j --from=/backups/neo4j_20241019.dump --overwrite-destination=true

# Start Neo4j
docker-compose start neo4j
```

### MinIO Object Storage

#### Backup
```bash
# Use MinIO client (mc)
mc mirror minio/epi-documents /backups/minio_$(date +%Y%m%d)

# Or use rclone
rclone sync minio:epi-documents /backups/minio_$(date +%Y%m%d) -v
```

#### Restore
```bash
# Restore all documents
mc mirror /backups/minio_20241019 minio/epi-documents

# Tenant-specific restore (documents are prefixed with tenant_id/)
mc mirror /backups/minio_20241019/tenant-123 minio/epi-documents/tenant-123
```

### Redis Cache (Optional)

Redis cache is ephemeral and does not require backup. On restore:
1. Cache will be empty
2. First queries will be slower (cache miss)
3. Cache will warm up naturally with use

If you need to backup Redis:
```bash
# Redis automatically saves to dump.rdb
cp /var/lib/redis/dump.rdb /backups/redis_$(date +%Y%m%d).rdb

# Restore
docker-compose stop redis
cp /backups/redis_20241019.rdb /var/lib/redis/dump.rdb
docker-compose start redis
```

### Full System Backup Script

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups/epi_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Backing up PostgreSQL..."
pg_dump -h localhost -U epi_user -d epi_db -F c -b -v -f "$BACKUP_DIR/postgres.dump"

echo "Backing up Qdrant..."
# Snapshot each tenant collection
for collection in $(curl -s http://localhost:6333/collections | jq -r '.result.collections[].name'); do
  snapshot=$(curl -sX POST "http://localhost:6333/collections/$collection/snapshots" | jq -r '.result.name')
  curl -X GET "http://localhost:6333/collections/$collection/snapshots/$snapshot" \
    -o "$BACKUP_DIR/qdrant_${collection}.tar.gz"
done

echo "Backing up Neo4j..."
docker-compose exec -T neo4j neo4j-admin database dump neo4j --to=/tmp/neo4j.dump
docker cp epi_neo4j_1:/tmp/neo4j.dump "$BACKUP_DIR/neo4j.dump"

echo "Backing up MinIO..."
mc mirror minio/epi-documents "$BACKUP_DIR/minio"

echo "Backup complete: $BACKUP_DIR"
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
echo "Compressed backup: $BACKUP_DIR.tar.gz"
```

### Disaster Recovery Procedure

1. **Deploy fresh infrastructure**
   ```bash
   docker-compose up -d
   ```

2. **Restore PostgreSQL** (restores users, documents, embeddings metadata)
   ```bash
   pg_restore -h localhost -U epi_user -d epi_db -v postgres.dump
   ```

3. **Restore Qdrant** (restores vector embeddings)
   ```bash
   for snapshot in qdrant_*.tar.gz; do
     collection=$(basename $snapshot .tar.gz | sed 's/qdrant_//')
     curl -X PUT "http://localhost:6333/collections/$collection/snapshots/upload" -F "snapshot=@$snapshot"
     # Wait for upload to complete, then recover
     snapshot_name=$(basename $snapshot .tar.gz)
     curl -X PUT "http://localhost:6333/collections/$collection/snapshots/$snapshot_name/recover"
   done
   ```

4. **Restore Neo4j** (restores knowledge graph)
   ```bash
   docker-compose stop neo4j
   docker cp neo4j.dump epi_neo4j_1:/tmp/neo4j.dump
   docker-compose start neo4j
   docker-compose exec neo4j neo4j-admin database load neo4j --from=/tmp/neo4j.dump --overwrite-destination=true
   docker-compose restart neo4j
   ```

5. **Restore MinIO** (restores original documents)
   ```bash
   mc mirror minio_backup/ minio/epi-documents
   ```

6. **Verify integrity**
   ```bash
   # Check document count
   psql -h localhost -U epi_user -d epi_db -c "SELECT tenant_id, COUNT(*) FROM documents GROUP BY tenant_id;"
   
   # Check vector store
   curl -s http://localhost:6333/collections | jq '.result.collections[] | {name, vectors_count}'
   
   # Check MinIO
   mc du minio/epi-documents
   
   # Check Neo4j
   docker-compose exec neo4j cypher-shell "MATCH (n) RETURN count(n);"
   ```

### Backup Retention Policy (Recommended)

- **Daily backups**: Retain for 7 days
- **Weekly backups**: Retain for 4 weeks
- **Monthly backups**: Retain for 12 months
- **Yearly backups**: Retain indefinitely

### Backup Testing

Test backups quarterly:
1. Restore to a staging environment
2. Run smoke tests (login, query, upload)
3. Verify data integrity (document count, sample queries)
4. Document any issues or gaps

## Security Monitoring

### Key Metrics to Monitor

1. **Authorization failures** (audit_logs WHERE outcome='denied')
2. **Failed login attempts** (audit_logs WHERE action='auth.login_failed')
3. **Tenant isolation violations** (audit_logs WHERE action='security.scope_violation')
4. **Unusual query patterns** (high volume from single user)
5. **Document access patterns** (audit_logs WHERE action='document.read')

### Alerting Rules

Set up alerts for:
- More than 10 authorization failures per user per hour
- More than 5 failed logins per account per minute (potential brute force)
- Any `security.scope_violation` events (critical: tenant isolation breach)
- Document deletion by non-admin roles
- Query rate exceeding 100/min per user (potential abuse)

### Log Retention

- **Application logs**: 30 days
- **Audit logs** (database): 7 years (compliance requirement)
- **Access logs**: 90 days

## Incident Response

### Suspected Tenant Isolation Breach

1. **Immediate**: Disable affected user accounts
   ```sql
   UPDATE users SET is_active = false WHERE id = 'user-123';
   ```

2. **Investigate**: Query audit logs
   ```sql
   SELECT * FROM audit_logs 
   WHERE user_id = 'user-123' 
   AND created_at > NOW() - INTERVAL '24 hours'
   ORDER BY created_at DESC;
   ```

3. **Notify**: Alert tenant administrators and security team

4. **Remediate**: Patch vulnerability, rotate tokens, re-test isolation

### Unusual Query Volume

1. **Check rate limiter**: Verify limits are enforced
2. **Review queries**: Check for automated scraping or data exfiltration
3. **Temporary ban**: Increase rate limit throttling for affected user
4. **Investigate intent**: Contact user to understand use case

### Document Deletion (Accidental or Malicious)

1. **Check audit logs**: Identify who deleted what
   ```sql
   SELECT * FROM audit_logs 
   WHERE action = 'document.delete' 
   AND created_at > NOW() - INTERVAL '7 days';
   ```

2. **Restore from backup**: Use tenant-specific backup if available

3. **Review permissions**: Ensure only admins can delete documents

4. **Enable soft delete**: Modify `delete_document()` to mark deleted instead of purging

## Conclusion

This document covers security operations for the Enterprise Procurement Intelligence platform, including:
- Authorization audit logging (GAP-1 remediation)
- Answer caching status (GAP-2 N/A)
- Vector consistency limitations (GAP-3 documented)
- Tenant quotas architectural decision (GAP-4 documented)
- Ingestion concurrency design (GAP-5 documented)
- Comprehensive backup/restore procedures
- Security monitoring and incident response

For questions or updates, see `backend/docs/audit_reports/` for phase-specific security audits.
