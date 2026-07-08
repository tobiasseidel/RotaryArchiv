"""MCP Tool: Document operations."""

from src.rotary_archiv.core.database import SessionLocal
from src.rotary_archiv.mcp.tool_registry import ToolDefinition, registry
from src.rotary_archiv.services import document_service


def get_document_detail(document_id: int) -> dict:
    """Get detailed information about a document."""
    db = SessionLocal()
    try:
        doc = document_service.get_document(db, document_id)
        return {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "title": doc.title,
            "description": doc.description,
            "created_at": str(doc.created_at),
            "updated_at": str(doc.updated_at),
        }
    finally:
        db.close()


def list_documents_summary(limit: int = 20, offset: int = 0) -> dict:
    """List documents with summary information."""
    db = SessionLocal()
    try:
        docs = document_service.list_documents_summary(db, limit=limit, offset=offset)
        return {
            "total": len(docs),
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "status": doc.status,
                }
                for doc in docs
            ],
        }
    finally:
        db.close()


def get_document_units(document_id: int) -> dict:
    """Get all units (chapters/sections) for a document."""
    db = SessionLocal()
    try:
        units = document_service.get_document_units(db, document_id)
        return {
            "units": [
                {
                    "id": unit.id,
                    "title": unit.title,
                    "content": unit.content if hasattr(unit, "content") else None,
                }
                for unit in units
            ],
        }
    finally:
        db.close()


def delete_document(document_id: int) -> dict:
    """Delete a document."""
    db = SessionLocal()
    try:
        document_service.delete_document(db, document_id)
        return {"success": True, "message": f"Document {document_id} deleted"}
    finally:
        db.close()


# Register tools
registry.register(
    ToolDefinition(
        name="get_document_detail",
        description="Get detailed information about a document by ID",
        input_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "integer", "description": "The document ID"}
            },
            "required": ["document_id"],
        },
    ),
    get_document_detail,
)

registry.register(
    ToolDefinition(
        name="list_documents",
        description="List all documents with summary information",
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
    list_documents_summary,
)

registry.register(
    ToolDefinition(
        name="get_document_units",
        description="Get all units/chapters for a document",
        input_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "integer", "description": "The document ID"}
            },
            "required": ["document_id"],
        },
    ),
    get_document_units,
)

registry.register(
    ToolDefinition(
        name="delete_document",
        description="Delete a document by ID (use with caution)",
        input_schema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "integer",
                    "description": "The document ID to delete",
                }
            },
            "required": ["document_id"],
        },
    ),
    delete_document,
)
