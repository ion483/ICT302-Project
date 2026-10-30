
from typing import Any


def create_parsed_document(
    document_id: str,
    paragraphs: list[dict],
    metadata: dict,
    rsid_root: str | None = None,
    rsid_table: list[str] | None = None,
) -> dict[str, Any]:
    """Create a shared document structure for the analysis modules."""

    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("document_id must be a non-empty string")

    if not isinstance(paragraphs, list):
        raise ValueError("paragraphs must be a list")

    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a dictionary")

    return {
        "document_id": document_id,
        "paragraphs": paragraphs,
        "metadata": metadata,
        "rsid_root": rsid_root,
        "rsid_table": rsid_table if rsid_table is not None else [],
        "extraction_complete": False,
        "extraction_notes": [
            "Full OOXML extraction coverage has not been verified."
        ],
    }


def validate_parsed_document(document: dict) -> bool:
    """Check that the main document fields have the expected types."""

    if not isinstance(document, dict):
        return False

    required_fields = {
        "document_id": str,
        "paragraphs": list,
        "metadata": dict,
        "rsid_table": list,
        "extraction_complete": bool,
        "extraction_notes": list,
    }

    for field, expected_type in required_fields.items():
        if field not in document:
            return False

        if not isinstance(document[field], expected_type):
            return False

    if not document["document_id"].strip():
        return False

    if document.get("rsid_root") is not None:
        if not isinstance(document["rsid_root"], str):
            return False

    return True
