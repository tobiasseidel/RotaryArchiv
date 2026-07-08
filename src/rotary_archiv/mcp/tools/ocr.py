"""MCP Tool: OCR operations."""

from src.rotary_archiv.core.database import SessionLocal
from src.rotary_archiv.mcp.tool_registry import ToolDefinition, registry
from src.rotary_archiv.services import ocr_service


def get_ocr_results(document_id: int) -> dict:
    """Get all OCR results for a document."""
    db = SessionLocal()
    try:
        results = ocr_service.get_ocr_results(db, document_id)
        return {
            "results": [
                {
                    "id": r.id,
                    "engine": r.engine,
                    "confidence": r.confidence,
                    "created_at": str(r.created_at)
                    if hasattr(r, "created_at")
                    else None,
                }
                for r in results
            ],
        }
    finally:
        db.close()


def get_ocr_result_detail(document_id: int, result_id: int) -> dict:
    """Get detailed OCR result with text content."""
    db = SessionLocal()
    try:
        result = ocr_service.get_ocr_result(db, document_id, result_id)
        return {
            "id": result.id,
            "document_id": result.document_id,
            "engine": result.engine,
            "confidence": result.confidence,
            "text_content": result.text_content,
            "created_at": str(result.created_at)
            if hasattr(result, "created_at")
            else None,
        }
    finally:
        db.close()


def get_queue_status(job_type: str = "all") -> dict:
    """Get OCR queue status."""
    db = SessionLocal()
    try:
        result = ocr_service.get_queue_status(db, job_type)
        return result
    finally:
        db.close()


def list_ocr_jobs(limit: int = 20, offset: int = 0) -> dict:
    """List OCR jobs with status."""
    db = SessionLocal()
    try:
        jobs = ocr_service.list_ocr_jobs(db, limit=limit, offset=offset)
        return {
            "jobs": [
                {
                    "id": job.id,
                    "status": job.status,
                    "priority": job.priority,
                    "created_at": str(job.created_at)
                    if hasattr(job, "created_at")
                    else None,
                }
                for job in jobs
            ],
        }
    finally:
        db.close()


# Register tools
registry.register(
    ToolDefinition(
        name="get_ocr_results",
        description="Get all OCR results for a document",
        input_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "integer", "description": "The document ID"}
            },
            "required": ["document_id"],
        },
    ),
    get_ocr_results,
)

registry.register(
    ToolDefinition(
        name="get_ocr_result_detail",
        description="Get detailed OCR result with full text content",
        input_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "integer", "description": "The document ID"},
                "result_id": {"type": "integer", "description": "The OCR result ID"},
            },
            "required": ["document_id", "result_id"],
        },
    ),
    get_ocr_result_detail,
)

registry.register(
    ToolDefinition(
        name="get_queue_status",
        description="Get OCR processing queue status",
        input_schema={
            "type": "object",
            "properties": {
                "job_type": {
                    "type": "string",
                    "description": "Filter by job type (default: 'all')",
                    "enum": ["all", "ocr", "processing"],
                },
            },
        },
    ),
    get_queue_status,
)

registry.register(
    ToolDefinition(
        name="list_ocr_jobs",
        description="List OCR jobs with their status",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results (default 20)"},
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset (default 0)",
                },
            },
        },
    ),
    list_ocr_jobs,
)
