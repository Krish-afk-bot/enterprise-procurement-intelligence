# MCP verification

Tools advertised: 9 (get_contract_amendments, get_document, get_entity_neighbours, get_evaluation_metrics, get_ingestion_status, get_supplier_profile, search_contracts, search_documents, search_graph)

Tool calls succeeded: 9/9

| Tool | Result |
| --- | --- |
| search_documents | ok |
| get_document | ok |
| search_contracts | ok |
| get_supplier_profile | ok |
| get_contract_amendments | ok |
| get_ingestion_status | ok |
| get_evaluation_metrics | ok |
| search_graph | ok |
| get_entity_neighbours | ok |

## Negative cases

| Case | Rejected |
| --- | --- |
| delete_everything {} | True |
| get_document {"document_id": "doc_does_not_exist"} | True |
| search_graph {"label": "SecretTable", "query": "", "limit": 5} | True |
| search_documents {"query": "tender", "limit": "not-a-number"} | True |

Audit rows written for `mcp_tool`: 22.

## Not tested

- tenant mismatch (only one tenant exists and creating one would modify source data)
- rate-limit exhaustion (would require >60 calls in a minute against a read-only dev database)
- timeout (no deterministic slow tool in this environment)

## Agent-over-MCP arm

Not run. The only installed model (`qwen2.5-coder:7b`) was not validated for MCP tool calling,
and `get_supplier_profile`/`search_*` cover titles and structured fields rather than chunk text,
so a content-question agent arm would mostly measure the tool gap rather than the agent. The tool
layer itself is verified above. Recommended future tool: `search_chunks(query, document_id, page)`.
