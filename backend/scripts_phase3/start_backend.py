"""Phase 4 Stage 6: Start the backend and verify live health endpoint.

Run as: python scripts_phase3/start_backend.py
Then in another terminal: python scripts_phase3/check_backend_health.py
"""

# This script just sets env vars and prints the uvicorn command.
# The server must be started manually so it can run in the background.

import os

env_vars = {
    "DATABASE_URL": "postgresql+asyncpg://epi:epi@localhost:5432/epi",
    "VECTOR_PROVIDER": "qdrant",
    "QDRANT_URL": "http://localhost:6333",
    "GRAPH_PROVIDER": "neo4j",
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USERNAME": "neo4j",
    "NEO4J_PASSWORD": "neo4jdev",
    "CACHE_PROVIDER": "redis",
    "REDIS_URL": "redis://localhost:6379/0",
    "STORAGE_PROVIDER": "s3",
    "S3_ENDPOINT": "http://localhost:9000",
    "S3_ACCESS_KEY": "minioadmin",
    "S3_SECRET_KEY": "minioadmin",
    "S3_BUCKET": "epi-documents",
    "ALLOW_PROVIDER_FALLBACK": "false",
    "AUTO_CREATE_SCHEMA": "false",
    "RERANKER_ENABLED": "true",
    "EMBEDDING_MODEL": "BAAI/bge-small-en-v1.5",
    "LLM_BASE_URL": "http://localhost:11434/v1",
    "LLM_API_KEY": "ollama",
    "LLM_MODEL": "llama3.1:8b",
}

for k, v in env_vars.items():
    os.environ[k] = v

print("Environment variables set.")
print("\nStarting uvicorn...")
import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
