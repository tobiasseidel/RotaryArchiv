"""MCP Tool: Search operations."""

from src.rotary_archiv.core.database import SessionLocal
from src.rotary_archiv.mcp.tool_registry import ToolDefinition, registry
from src.rotary_archiv.services import search_service


def search_documents(
    query: str,
    person_slug: str | None = None,
    year: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> dict:
    """Search documents with full-text search and filters."""
    db = SessionLocal()
    try:
        result = search_service.search(
            db,
            query=query,
            person_slug=person_slug,
            year=year,
            category=category,
            limit=limit,
        )
        return result
    finally:
        db.close()


def list_persons(limit: int = 50, offset: int = 0) -> dict:
    """List all persons in the archive."""
    db = SessionLocal()
    try:
        result = search_service.list_persons(db, limit=limit, offset=offset)
        return result
    finally:
        db.close()


def get_person_detail(slug: str) -> dict:
    """Get detailed information about a person."""
    db = SessionLocal()
    try:
        result = search_service.get_person(db, slug)
        return result
    finally:
        db.close()


# Register tools
registry.register(
    ToolDefinition(
        name="search_documents",
        description="Full-text search in documents with optional filters (person, year, category)",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "person_slug": {
                    "type": "string",
                    "description": "Filter by person slug",
                },
                "year": {
                    "type": "string",
                    "description": "Filter by year (e.g. '1930')",
                },
                "category": {"type": "string", "description": "Filter by category"},
                "limit": {"type": "integer", "description": "Max results (default 20)"},
            },
            "required": ["query"],
        },
    ),
    search_documents,
)

registry.register(
    ToolDefinition(
        name="list_persons",
        description="List all persons in the archive with their roles",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results (default 50)"},
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset (default 0)",
                },
            },
        },
    ),
    list_persons,
)

registry.register(
    ToolDefinition(
        name="get_person_detail",
        description="Get detailed information about a person by slug",
        input_schema={
            "type": "object",
            "properties": {
                "slug": {
                    "type": "string",
                    "description": "Person slug (e.g. 'max-mustermann')",
                }
            },
            "required": ["slug"],
        },
    ),
    get_person_detail,
)
