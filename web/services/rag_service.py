"""
RAG Service for Retrieval-Augmented Generation

Provides semantic search functionality using the RAG knowledge hierarchy.
Bridges the EmbeddingService and RAG database for cost-effective AI queries.
"""

import sys
import os
import time
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass

# Add paths for imports
sys.path.append('/Users/josephs./internal-platform/scripts')
sys.path.append('/Users/josephs./internal-platform/web')

try:
    from scripts.embedding_service import EmbeddingService, EmbeddingResult
    from scripts.db import DatabaseSession
    from sqlalchemy import text
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Import error in RAGService: {e}")
    # Fallback imports
    from embedding_service import EmbeddingService, EmbeddingResult
    from db import DatabaseSession
    from sqlalchemy import text

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class RAGChunkResult:
    """Result from RAG chunk search."""
    chunk_id: str
    content_text: str
    similarity_score: float
    text_rank: float
    combined_score: float

    # Enhanced metadata for context assembly
    document_title: Optional[str] = None
    section_title: Optional[str] = None
    speaker: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    content_date: Optional[str] = None
    source_type: Optional[str] = None
    video_id: Optional[str] = None


@dataclass
class RAGSearchResult:
    """Complete result from RAG search with metadata."""
    chunks: List[RAGChunkResult]
    search_method: str  # 'rag', 'keyword', 'hybrid'
    query_embedding_time_ms: float
    search_time_ms: float
    total_time_ms: float
    chunks_found: int
    similarity_threshold: float
    embedding_cost: float


class RAGService:
    """Service for RAG-based semantic search and context assembly."""

    def __init__(self, embedding_service: EmbeddingService = None):
        """Initialize RAG service with embedding service."""
        self.embedding_service = embedding_service or EmbeddingService()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def search_with_rag(self,
                       query: str,
                       limit: int = 20,
                       similarity_threshold: float = 0.7) -> RAGSearchResult:
        """
        Perform semantic search using RAG chunks.

        Args:
            query: User's search query
            limit: Maximum number of chunks to return
            similarity_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            RAGSearchResult with chunks and metadata
        """
        start_time = time.time()

        try:
            # Step 1: Embed the query
            embed_start = time.time()
            embedding_result = self.embedding_service.embed_text(
                query,
                metadata={'request_type': 'rag_query_embedding'}
            )
            embed_time = (time.time() - embed_start) * 1000

            if not embedding_result.success:
                raise Exception(f"Failed to embed query: {embedding_result.error}")

            # Step 2: Search using hybrid_search function
            search_start = time.time()
            chunks = self._search_chunks_with_metadata(
                query,
                embedding_result.embedding,
                similarity_threshold,
                limit
            )
            search_time = (time.time() - search_start) * 1000

            total_time = (time.time() - start_time) * 1000

            self.logger.info(
                f"RAG search completed: {len(chunks)} chunks found in {total_time:.2f}ms "
                f"(embed: {embed_time:.2f}ms, search: {search_time:.2f}ms)"
            )

            return RAGSearchResult(
                chunks=chunks,
                search_method='rag',
                query_embedding_time_ms=embed_time,
                search_time_ms=search_time,
                total_time_ms=total_time,
                chunks_found=len(chunks),
                similarity_threshold=similarity_threshold,
                embedding_cost=embedding_result.cost
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "hybrid_search" in error_msg and "does not exist" in error_msg:
                self.logger.info(f"RAG search unavailable: hybrid_search function not installed. Using keyword fallback.")
                search_method = 'rag_unavailable'
            else:
                self.logger.error(f"RAG search failed: {e}")
                search_method = 'rag_failed'

            total_time = (time.time() - start_time) * 1000

            return RAGSearchResult(
                chunks=[],
                search_method=search_method,
                query_embedding_time_ms=0,
                search_time_ms=0,
                total_time_ms=total_time,
                chunks_found=0,
                similarity_threshold=similarity_threshold,
                embedding_cost=0.0
            )

    def _search_chunks_with_metadata(self,
                                   query_text: str,
                                   query_embedding: List[float],
                                   similarity_threshold: float,
                                   limit: int) -> List[RAGChunkResult]:
        """
        Use PostgreSQL hybrid_search function and enrich with metadata.
        """
        with DatabaseSession() as session:
            # Convert embedding to pgvector format
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

            # Call hybrid_search function
            result = session.execute(
                text("""
                    SELECT
                        h.chunk_id,
                        h.content_text,
                        h.similarity_score,
                        h.text_rank,
                        h.combined_score,
                        -- Additional metadata from joins
                        d.title as document_title,
                        d.content_date,
                        d.source_type,
                        d.source_id as video_id,
                        s.title as section_title,
                        s.speaker,
                        s.start_time,
                        s.end_time
                    FROM hybrid_search(:query_text, (:query_embedding)::vector, :similarity_threshold, :limit) h
                    LEFT JOIN rag_chunks c ON c.id = h.chunk_id
                    LEFT JOIN rag_sections s ON s.id = c.section_id
                    LEFT JOIN rag_documents d ON d.id = c.document_id
                    ORDER BY h.combined_score DESC
                """),
                {
                    'query_text': query_text,
                    'query_embedding': embedding_str,
                    'similarity_threshold': similarity_threshold,
                    'limit': limit
                }
            ).fetchall()

            # Convert to RAGChunkResult objects
            chunks = []
            for row in result:
                chunk = RAGChunkResult(
                    chunk_id=str(row.chunk_id),
                    content_text=row.content_text,
                    similarity_score=float(row.similarity_score),
                    text_rank=float(row.text_rank),
                    combined_score=float(row.combined_score),
                    document_title=row.document_title,
                    section_title=row.section_title,
                    speaker=row.speaker,
                    start_time=float(row.start_time) if row.start_time else None,
                    end_time=float(row.end_time) if row.end_time else None,
                    content_date=row.content_date.isoformat() if row.content_date else None,
                    source_type=row.source_type,
                    video_id=str(row.video_id) if row.video_id else None
                )
                chunks.append(chunk)

            return chunks

    def assemble_context_from_chunks(self,
                                   chunks: List[RAGChunkResult],
                                   max_tokens: int = 5000) -> str:
        """
        Build AI context from RAG chunks with citations.

        Args:
            chunks: List of RAG chunks to include
            max_tokens: Maximum tokens in assembled context

        Returns:
            Formatted context string with citations
        """
        if not chunks:
            return ""

        context_parts = ["TRANSCRIPT DATA FROM RAG SEARCH:\n"]
        total_chars = len(context_parts[0])
        chunks_used = 0
        videos_referenced = set()

        # Rough conversion: ~4 characters per token
        max_chars = max_tokens * 4

        for chunk in chunks:
            # Format citation header
            date_str = chunk.content_date[:10] if chunk.content_date else "Unknown Date"
            speaker_str = chunk.speaker or "Unknown Speaker"
            title_str = chunk.document_title or "Unknown Source"

            citation_header = f"\n[{date_str} | {speaker_str} | {title_str}]"

            # Add timing/position info if available
            if chunk.start_time and chunk.end_time:
                video_info = f'\nVideo: "{title_str}" | {chunk.start_time:.1f}s-{chunk.end_time:.1f}s'
                if chunk.video_id:
                    video_info += f" | ID:{chunk.video_id}"
            else:
                video_info = f'\nContent: "{title_str}"'

            # Format content with quotes
            content_text = f'\n"{chunk.content_text}"\n'

            # Calculate total size
            entry_size = len(citation_header) + len(video_info) + len(content_text)

            # Check if we exceed token limit
            if total_chars + entry_size > max_chars and chunks_used > 0:
                break

            # Add to context
            context_parts.append(citation_header)
            context_parts.append(video_info)
            context_parts.append(content_text)

            total_chars += entry_size
            chunks_used += 1

            if chunk.video_id:
                videos_referenced.add(chunk.video_id)

        # Add summary footer
        similarity_avg = sum(c.combined_score for c in chunks[:chunks_used]) / chunks_used if chunks_used > 0 else 0
        summary_footer = f"\n[Citations: {len(videos_referenced)} videos, {chunks_used} chunks, {similarity_avg:.1%} relevance match]"

        context_parts.append(summary_footer)

        final_context = "".join(context_parts)

        self.logger.info(
            f"Context assembled: {chunks_used} chunks, {total_chars} chars, "
            f"{len(videos_referenced)} videos, {similarity_avg:.1%} avg relevance"
        )

        return final_context

    def search_with_fallback(self,
                           query: str,
                           limit: int = 20,
                           similarity_threshold: float = 0.7,
                           min_quality_chunks: int = 3) -> Tuple[RAGSearchResult, str]:
        """
        RAG search with automatic fallback to keyword search if needed.

        Returns:
            Tuple of (search_result, search_method_used)
        """
        try:
            # Try RAG search first
            rag_result = self.search_with_rag(query, limit, similarity_threshold)

            # Check if RAG search was successful and has quality results
            if (rag_result.search_method == 'rag' and
                len(rag_result.chunks) >= min_quality_chunks):
                return rag_result, 'rag'

            self.logger.warning(
                f"RAG search yielded {len(rag_result.chunks)} chunks "
                f"(below threshold of {min_quality_chunks}), considering fallback"
            )

            # If RAG didn't yield enough results, we'll mark it as needing fallback
            # The actual keyword search fallback would be handled by the calling service
            return rag_result, 'rag_insufficient'

        except Exception as e:
            self.logger.error(f"RAG search with fallback failed: {e}")

            # Return empty result for error case
            empty_result = RAGSearchResult(
                chunks=[],
                search_method='rag_error',
                query_embedding_time_ms=0,
                search_time_ms=0,
                total_time_ms=0,
                chunks_found=0,
                similarity_threshold=similarity_threshold,
                embedding_cost=0.0
            )

            return empty_result, 'error'


# Convenience functions
def search_rag_chunks(query: str, **kwargs) -> RAGSearchResult:
    """Quick RAG search function."""
    service = RAGService()
    return service.search_with_rag(query, **kwargs)


def assemble_rag_context(chunks: List[RAGChunkResult], **kwargs) -> str:
    """Quick context assembly function."""
    service = RAGService()
    return service.assemble_context_from_chunks(chunks, **kwargs)