"""Read-only Holus lineage export and diagnostics endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from holus.lineage.store import LineageStore

router = APIRouter(prefix="/lineage", tags=["lineage"])
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
LINEAGE_DIR = REPO_ROOT / "data" / "lineage"


@router.get("/manifest")
async def lineage_manifest(
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=1000),
) -> dict[str, Any]:
    """Return the versioned, privacy-safe manifest only when its ledger validates."""
    store = LineageStore(LINEAGE_DIR)
    if not store.validate().valid:
        raise HTTPException(status_code=409, detail="LINEAGE_INVALID")
    return store.manifest(cursor=cursor, limit=limit)


@router.get("/export")
async def export_lineage(
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=1000, ge=1, le=1000),
) -> dict[str, Any]:
    """Return only a validated, sequence-cursored committed ledger snapshot."""
    try:
        return LineageStore(LINEAGE_DIR).export(after_seq=after_seq, limit=limit)
    except ValueError as exc:
        if str(exc) == "LINEAGE_INVALID":
            raise HTTPException(status_code=409, detail="LINEAGE_INVALID") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/validate")
async def validate_lineage() -> dict[str, Any]:
    """Return completeness diagnostics; a partial graph is explicitly not complete."""
    return LineageStore(LINEAGE_DIR).validate().to_dict()


@router.get("/nodes/{node_id}")
async def get_lineage_node(node_id: str) -> dict[str, Any]:
    """Return one node and its adjacent edges from the same read-only owner."""
    manifest = LineageStore(LINEAGE_DIR).manifest(limit=100_000)
    nodes = [node for node in manifest["nodes"] if node["node_id"] == node_id]
    if not nodes:
        raise HTTPException(status_code=404, detail=f"Lineage node {node_id!r} not found")
    return {
        "schema_version": manifest["schema_version"],
        "node": nodes[0],
        "edges": [
            edge
            for edge in manifest["edges"]
            if edge["from_node_id"] == node_id or edge["to_node_id"] == node_id
        ],
    }
