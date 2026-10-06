"""SQLAlchemy models. Importing this module registers all tables on Base.metadata."""

from app.db.models.conversations import (
    ANSWER_STATUSES,
    AnswerRecord,
    Citation,
    Conversation,
    Message,
    QueryRecord,
)
from app.db.models.documents import (
    CONTENT_TYPES,
    DOCUMENT_STATUSES,
    DOCUMENT_TYPES,
    Chunk,
    Document,
    DocumentPage,
    TableRecord,
)
from app.db.models.operations import (
    JOB_STATUSES,
    AgentTrace,
    AuditLog,
    EvaluationResult,
    EvaluationRun,
    IngestionJob,
)
from app.db.models.procurement import (
    CONTRACT_STATUSES,
    ComplianceCertificate,
    Contract,
    DataSourceRecord,
    Price,
    ProcurementRecord,
    Product,
    Supplier,
)
from app.db.models.tenancy import ACCESS_LEVELS, ROLES, Tenant, User

__all__ = [
    "ACCESS_LEVELS",
    "ANSWER_STATUSES",
    "AgentTrace",
    "AnswerRecord",
    "AuditLog",
    "CONTENT_TYPES",
    "CONTRACT_STATUSES",
    "Citation",
    "Chunk",
    "ComplianceCertificate",
    "Contract",
    "Conversation",
    "DOCUMENT_STATUSES",
    "DOCUMENT_TYPES",
    "DataSourceRecord",
    "Document",
    "DocumentPage",
    "EvaluationResult",
    "EvaluationRun",
    "IngestionJob",
    "JOB_STATUSES",
    "Message",
    "Price",
    "ProcurementRecord",
    "Product",
    "QueryRecord",
    "ROLES",
    "Supplier",
    "TableRecord",
    "Tenant",
    "User",
]
