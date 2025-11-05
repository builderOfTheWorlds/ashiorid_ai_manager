"""
API routes for Lore RAG Service.
"""

import time
from typing import List

from fastapi import APIRouter, HTTPException, Request, Depends, File, UploadFile

import sys
sys.path.append('../..')
from shared.common_types import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    DocumentChunk,
)
from shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_search_service(request: Request):
    """Dependency to get search service from app state."""
    return request.app.state.app_state.search_service


def get_ingestion_service(request: Request):
    """Dependency to get ingestion service from app state."""
    return request.app.state.app_state.ingestion_service


def get_qdrant_service(request: Request):
    """Dependency to get Qdrant service from app state."""
    return request.app.state.app_state.qdrant_service


def get_metrics(request: Request):
    """Dependency to get metrics from app state."""
    return request.app.state.metrics


@router.post("/search", response_model=SemanticSearchResponse)
async def semantic_search(
    search_request: SemanticSearchRequest,
    request: Request,
    search_service=Depends(get_search_service),
    metrics=Depends(get_metrics),
):
    """
    Perform semantic search over lore collections.

    Args:
        search_request: Search query with filters

    Returns:
        Semantic search results with scores
    """
    start_time = time.time()

    try:
        logger.info(
            f"Search request: query='{search_request.query}', "
            f"collection={search_request.collection}, limit={search_request.limit}"
        )

        # Perform search
        response = await search_service.search(search_request)

        # Update metrics
        latency = time.time() - start_time
        response.latency_ms = latency * 1000

        metrics["search_count"].labels(
            collection=search_request.collection,
            status="success",
        ).inc()

        metrics["search_latency"].labels(
            collection=search_request.collection,
        ).observe(latency)

        logger.info(
            f"Search completed: results={len(response.results)}, "
            f"latency_ms={response.latency_ms:.2f}"
        )

        return response

    except Exception as e:
        metrics["search_count"].labels(
            collection=search_request.collection,
            status="error",
        ).inc()

        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest_documents(
    documents: List[DocumentChunk],
    collection: str = "lore",
    ingestion_service=Depends(get_ingestion_service),
    metrics=Depends(get_metrics),
):
    """
    Ingest documents into a collection.

    Args:
        documents: List of document chunks to ingest
        collection: Target collection name

    Returns:
        Ingestion status
    """
    try:
        logger.info(
            f"Ingestion request: {len(documents)} documents to collection '{collection}'"
        )

        # Ingest documents
        result = await ingestion_service.ingest(documents, collection)

        # Update metrics
        metrics["ingestion_count"].labels(
            collection=collection,
            status="success",
        ).inc()

        metrics["embedding_count"].inc(len(documents))

        logger.info(f"Ingestion completed: {result}")

        return {
            "status": "success",
            "collection": collection,
            "documents_ingested": len(documents),
            "details": result,
        }

    except Exception as e:
        metrics["ingestion_count"].labels(
            collection=collection,
            status="error",
        ).inc()

        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    collection: str = "lore",
    source: str = None,
    ingestion_service=Depends(get_ingestion_service),
):
    """
    Ingest a text file into a collection.

    Args:
        file: Uploaded file
        collection: Target collection name
        source: Source identifier for the document

    Returns:
        Ingestion status
    """
    try:
        # Read file content
        content = await file.read()
        text = content.decode('utf-8')

        source_name = source or file.filename

        logger.info(
            f"File ingestion request: file='{file.filename}', "
            f"size={len(text)} bytes, collection='{collection}'"
        )

        # Ingest file
        result = await ingestion_service.ingest_text(
            text=text,
            source=source_name,
            collection=collection,
        )

        logger.info(f"File ingestion completed: {result}")

        return {
            "status": "success",
            "filename": file.filename,
            "collection": collection,
            "chunks_created": result.get("chunks_created", 0),
        }

    except Exception as e:
        logger.error(f"File ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections")
async def list_collections(
    qdrant_service=Depends(get_qdrant_service),
):
    """
    List all available collections.

    Returns:
        List of collection names and their info
    """
    try:
        collections = await qdrant_service.list_collections()

        return {
            "collections": collections,
            "total": len(collections),
        }

    except Exception as e:
        logger.error(f"Failed to list collections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/{collection_name}")
async def get_collection_info(
    collection_name: str,
    qdrant_service=Depends(get_qdrant_service),
):
    """
    Get information about a specific collection.

    Args:
        collection_name: Name of the collection

    Returns:
        Collection information
    """
    try:
        info = await qdrant_service.get_collection_info(collection_name)

        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{collection_name}' not found"
            )

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collection info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collections/{collection_name}")
async def create_collection(
    collection_name: str,
    vector_size: int = 768,
    qdrant_service=Depends(get_qdrant_service),
):
    """
    Create a new collection.

    Args:
        collection_name: Name for the new collection
        vector_size: Dimension of vectors (default: 768 for nomic-embed-text)

    Returns:
        Creation status
    """
    try:
        await qdrant_service.create_collection(collection_name, vector_size)

        logger.info(f"Collection '{collection_name}' created")

        return {
            "status": "success",
            "collection": collection_name,
            "vector_size": vector_size,
        }

    except Exception as e:
        logger.error(f"Failed to create collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collections/{collection_name}")
async def delete_collection(
    collection_name: str,
    qdrant_service=Depends(get_qdrant_service),
):
    """
    Delete a collection.

    Args:
        collection_name: Name of the collection to delete

    Returns:
        Deletion status
    """
    try:
        await qdrant_service.delete_collection(collection_name)

        logger.info(f"Collection '{collection_name}' deleted")

        return {
            "status": "success",
            "collection": collection_name,
            "message": "Collection deleted",
        }

    except Exception as e:
        logger.error(f"Failed to delete collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats(
    qdrant_service=Depends(get_qdrant_service),
):
    """
    Get service statistics.

    Returns:
        Service statistics including collection counts
    """
    try:
        collections = await qdrant_service.list_collections()

        stats = {
            "total_collections": len(collections),
            "collections": {},
        }

        # Get stats for each collection
        for collection in collections:
            info = await qdrant_service.get_collection_info(collection["name"])
            if info:
                stats["collections"][collection["name"]] = {
                    "points_count": info.get("points_count", 0),
                    "vectors_count": info.get("vectors_count", 0),
                }

        return stats

    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
