"""
Transcript Service

Handles all transcript-related operations including advanced search functionality,
transcript listing, and segment management for AI context generation.
"""

import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

# Import database models and session
try:
    from scripts.db import DatabaseSession, Video, Transcript, TranscriptSegment
except ImportError:
    from ..scripts.db import DatabaseSession, Video, Transcript, TranscriptSegment


class TranscriptService:
    """Service for managing transcript operations and advanced search functionality."""

    # Stop words for search optimization
    DEFAULT_STOP_WORDS = {
        'want', 'need', 'like', 'make', 'create', 'find', 'give', 'about', 'from',
        'with', 'that', 'this', 'have', 'will', 'would', 'could', 'should', 'video',
        'script', 'clips', 'second', 'minute', 'the', 'and', 'for', 'how', 'know',
        'talking', 'talk', 'good', 'great', 'thing', 'things', 'way', 'just',
        'really', 'very', 'also', 'can', 'get', 'got', 'say', 'said', 'think',
        'going', 'look', 'see', 'time', 'year', 'years', 'people', 'work', 'working'
    }

    @staticmethod
    def search_for_context(query: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Advanced transcript search with intelligent keyword weighting and context expansion.

        This function prioritizes rare/specific keywords over common words and provides
        expanded context by including surrounding segments for better AI generation.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of transcript segments with metadata, scored and sorted by relevance
        """
        # Extract meaningful keywords (3+ chars, excluding stop words)
        keywords = [
            w for w in re.findall(r'\b\w{3,}\b', query.lower())
            if w not in TranscriptService.DEFAULT_STOP_WORDS
        ]

        # Remove duplicates while preserving order
        keywords = list(dict.fromkeys(keywords))

        print(f"[DEBUG] Search keywords: {keywords}")

        # Extract year filters from query
        year_pattern = re.findall(r'\b(19\d{2}|20\d{2})\b', query)
        min_year = None
        if year_pattern:
            min_year = min(int(y) for y in year_pattern)

        # Check for "recent" or "latest" keywords
        if any(w in query.lower() for w in ['recent', 'latest', 'new', 'newest']):
            min_year = 2020

        results_by_id = {}  # Track by segment_id to avoid duplicates and merge scores

        with DatabaseSession() as db_session:
            # Get all videos with metadata for context
            videos = db_session.query(Video).all()
            video_map = {
                str(v.id): {
                    'filename': v.filename,
                    'speaker': v.speaker or 'Unknown',
                    'event_name': v.event_name or 'Unknown',
                    'event_date': v.event_date,
                    'year': v.event_date.year if v.event_date else None
                } for v in videos
            }

            # Filter videos by year if specified
            if min_year:
                filtered_video_ids = {
                    str(v.id) for v in videos
                    if (v.event_date and v.event_date.year >= min_year) or not v.event_date
                }
            else:
                filtered_video_ids = set(video_map.keys())

            # Calculate keyword weights based on rarity
            keyword_weights = TranscriptService._calculate_keyword_weights(
                db_session, keywords
            )
            print(f"[DEBUG] Keyword weights: {keyword_weights}")

            # Search for matching segments with scoring
            for keyword in keywords[:15]:  # Limit to top 15 keywords
                if keyword_weights.get(keyword, 0) == 0:
                    continue

                segments = db_session.query(TranscriptSegment).join(
                    Transcript, TranscriptSegment.transcript_id == Transcript.id
                ).filter(
                    TranscriptSegment.text.ilike(f'%{keyword}%'),
                    Transcript.status == 'completed'
                ).limit(100).all()

                for seg in segments:
                    transcript = db_session.query(Transcript).filter(
                        Transcript.id == seg.transcript_id
                    ).first()

                    if transcript and str(transcript.video_id) in filtered_video_ids:
                        video_info = video_map.get(str(transcript.video_id), {})
                        event_date = video_info.get('event_date')
                        date_str = event_date.strftime('%Y-%m-%d') if event_date else 'Unknown date'

                        # Get surrounding segments for context (30 seconds around match)
                        nearby_segments = db_session.query(TranscriptSegment).filter(
                            TranscriptSegment.transcript_id == seg.transcript_id,
                            TranscriptSegment.start_time >= float(seg.start_time) - 15,
                            TranscriptSegment.end_time <= float(seg.end_time) + 15
                        ).order_by(TranscriptSegment.start_time).all()

                        if nearby_segments:
                            combined_text = ' '.join(s.text for s in nearby_segments)
                            start_time = float(nearby_segments[0].start_time)
                            end_time = float(nearby_segments[-1].end_time)
                        else:
                            combined_text = seg.text
                            start_time = float(seg.start_time)
                            end_time = float(seg.end_time)

                        seg_key = str(seg.id)

                        if seg_key in results_by_id:
                            # Merge scores for duplicate segments
                            results_by_id[seg_key]['score'] += keyword_weights.get(keyword, 1)
                            results_by_id[seg_key]['matched_keywords'].add(keyword)
                        else:
                            # New segment result
                            results_by_id[seg_key] = {
                                'video_id': str(transcript.video_id),
                                'video_title': video_info.get('filename', 'Unknown'),
                                'speaker': video_info.get('speaker', 'Unknown'),
                                'event_name': video_info.get('event_name', 'Unknown'),
                                'event_date': date_str,
                                'year': video_info.get('year'),
                                'start': start_time,
                                'end': end_time,
                                'text': combined_text,
                                'segment_id': seg_key,
                                'score': keyword_weights.get(keyword, 1),
                                'matched_keywords': {keyword}
                            }

            # Sort by score (highest first) - rare keyword matches come first
            results = sorted(results_by_id.values(), key=lambda x: -x['score'])

            print(f"[DEBUG] Total unique results: {len(results)}")
            if results:
                top = results[0]
                print(f"[DEBUG] Top result (score={top['score']}, keywords={top['matched_keywords']}): {top['text'][:80]}...")

            # If no keyword matches, get sample transcripts
            if not results:
                results = TranscriptService._get_fallback_transcripts(
                    db_session, video_map, filtered_video_ids
                )

        # Deduplicate and limit results
        return TranscriptService._deduplicate_results(results, limit)

    @staticmethod
    def _calculate_keyword_weights(db_session, keywords: List[str]) -> Dict[str, int]:
        """
        Calculate weights for keywords based on rarity.
        Rare keywords get higher weights for better relevance scoring.
        """
        keyword_counts = {}
        keyword_weights = {}

        # Count matches for each keyword
        for keyword in keywords[:15]:
            count = db_session.query(TranscriptSegment).join(
                Transcript, TranscriptSegment.transcript_id == Transcript.id
            ).filter(
                TranscriptSegment.text.ilike(f'%{keyword}%'),
                Transcript.status == 'completed'
            ).count()
            keyword_counts[keyword] = count
            print(f"[DEBUG] Keyword '{keyword}' has {count} matches")

        # Assign weights based on rarity
        for kw, count in keyword_counts.items():
            if count == 0:
                keyword_weights[kw] = 0
            elif count <= 5:
                keyword_weights[kw] = 10  # Very specific - highest priority
            elif count <= 20:
                keyword_weights[kw] = 5   # Specific
            elif count <= 50:
                keyword_weights[kw] = 2   # Moderate
            else:
                keyword_weights[kw] = 1   # Common

        return keyword_weights

    @staticmethod
    def _get_fallback_transcripts(db_session, video_map: Dict, filtered_video_ids: Set[str]) -> List[Dict[str, Any]]:
        """
        Get sample transcripts when no keyword matches are found.
        """
        results = []

        transcripts = db_session.query(Transcript).filter(
            Transcript.status == 'completed'
        ).all()

        # Filter by year and limit
        transcripts = [
            t for t in transcripts
            if str(t.video_id) in filtered_video_ids
        ][:20]

        for t in transcripts:
            video_info = video_map.get(str(t.video_id), {})
            event_date = video_info.get('event_date')
            date_str = event_date.strftime('%Y-%m-%d') if event_date else 'Unknown date'

            segments = db_session.query(TranscriptSegment).filter(
                TranscriptSegment.transcript_id == t.id
            ).order_by(TranscriptSegment.start_time).limit(30).all()

            for seg in segments:
                if len(seg.text) > 40:  # Only substantial segments
                    results.append({
                        'video_id': str(t.video_id),
                        'video_title': video_info.get('filename', 'Unknown'),
                        'speaker': video_info.get('speaker', 'Unknown'),
                        'event_name': video_info.get('event_name', 'Unknown'),
                        'event_date': date_str,
                        'year': video_info.get('year'),
                        'start': float(seg.start_time),
                        'end': float(seg.end_time),
                        'text': seg.text,
                        'segment_id': str(seg.id)
                    })

        return results

    @staticmethod
    def _deduplicate_results(results: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        Remove duplicate results and apply limit.
        """
        seen = set()
        unique_results = []

        for r in results:
            key = (r['video_id'], r['start'], r['end'])
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
                if len(unique_results) >= limit:
                    break

        print(f"[DEBUG] Total unique results: {len(unique_results)}")
        if unique_results:
            print(f"[DEBUG] Sample result: {unique_results[0]['text'][:100]}...")

        return unique_results

    @staticmethod
    def simple_search(query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Simple transcript search for basic functionality.

        Args:
            query: Search term
            limit: Maximum number of results

        Returns:
            List of matching transcript segments
        """
        results = []

        if not query.strip():
            return results

        with DatabaseSession() as db_session:
            segments = db_session.query(TranscriptSegment).filter(
                TranscriptSegment.text.ilike(f'%{query}%')
            ).limit(limit).all()

            for seg in segments:
                transcript = db_session.query(Transcript).filter(
                    Transcript.id == seg.transcript_id
                ).first()

                if transcript:
                    video = db_session.query(Video).filter(
                        Video.id == transcript.video_id
                    ).first()

                    results.append({
                        'video_id': str(transcript.video_id),
                        'video_title': video.filename if video else "Unknown",
                        'transcript_id': str(transcript.id),
                        'start': float(seg.start_time),
                        'end': float(seg.end_time),
                        'text': seg.text,
                        'segment_id': str(seg.id)
                    })

        return results

    @staticmethod
    def list_transcripts(status: str = 'completed', limit: int = 100) -> List[Dict[str, Any]]:
        """
        List transcripts with metadata.

        Args:
            status: Filter by transcript status
            limit: Maximum number of results

        Returns:
            List of transcripts with metadata
        """
        transcript_list = []

        with DatabaseSession() as db_session:
            transcripts = db_session.query(Transcript).filter(
                Transcript.status == status
            ).order_by(Transcript.created_at.desc()).limit(limit).all()

            for t in transcripts:
                # Get associated video
                video = db_session.query(Video).filter(Video.id == t.video_id).first()

                # Count segments
                segment_count = db_session.query(TranscriptSegment).filter(
                    TranscriptSegment.transcript_id == t.id
                ).count()

                transcript_list.append({
                    'id': str(t.id),
                    'video_id': str(t.video_id),
                    'video_title': video.filename if video else 'Unknown',
                    'speaker': video.speaker if video else 'Unknown',
                    'event_name': video.event_name if video else 'Unknown',
                    'event_date': video.event_date.strftime('%Y-%m-%d') if video and video.event_date else 'Unknown',
                    'status': t.status,
                    'segment_count': segment_count,
                    'created_at': t.created_at.isoformat() if t.created_at else None,
                    'updated_at': t.updated_at.isoformat() if t.updated_at else None
                })

        return transcript_list

    @staticmethod
    def get_transcript_by_id(transcript_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed transcript information by ID.

        Args:
            transcript_id: Transcript UUID

        Returns:
            Transcript data with segments or None if not found
        """
        with DatabaseSession() as db_session:
            transcript = db_session.query(Transcript).filter(
                Transcript.id == transcript_id
            ).first()

            if not transcript:
                return None

            # Get associated video
            video = db_session.query(Video).filter(Video.id == transcript.video_id).first()

            # Get segments
            segments = db_session.query(TranscriptSegment).filter(
                TranscriptSegment.transcript_id == transcript.id
            ).order_by(TranscriptSegment.start_time).all()

            segment_list = []
            for seg in segments:
                segment_list.append({
                    'id': str(seg.id),
                    'start_time': float(seg.start_time),
                    'end_time': float(seg.end_time),
                    'text': seg.text,
                    'speaker': seg.speaker,
                    'confidence': float(seg.confidence) if seg.confidence else None,
                    'sequence_number': seg.sequence_number
                })

            return {
                'id': str(transcript.id),
                'video_id': str(transcript.video_id),
                'video_title': video.filename if video else 'Unknown',
                'speaker': video.speaker if video else 'Unknown',
                'event_name': video.event_name if video else 'Unknown',
                'event_date': video.event_date.strftime('%Y-%m-%d') if video and video.event_date else 'Unknown',
                'status': transcript.status,
                'language': transcript.language,
                'confidence': float(transcript.confidence) if transcript.confidence else None,
                'segments': segment_list,
                'total_duration': float(video.duration_seconds) if video and video.duration_seconds else 0,
                'created_at': transcript.created_at.isoformat() if transcript.created_at else None,
                'updated_at': transcript.updated_at.isoformat() if transcript.updated_at else None
            }

    @staticmethod
    def get_segments_by_transcript_id(transcript_id: str) -> List[Dict[str, Any]]:
        """
        Get all segments for a transcript.

        Args:
            transcript_id: Transcript UUID

        Returns:
            List of transcript segments
        """
        with DatabaseSession() as db_session:
            segments = db_session.query(TranscriptSegment).filter(
                TranscriptSegment.transcript_id == transcript_id
            ).order_by(TranscriptSegment.start_time).all()

            return [{
                'id': str(seg.id),
                'transcript_id': str(seg.transcript_id),
                'start_time': float(seg.start_time),
                'end_time': float(seg.end_time),
                'text': seg.text,
                'speaker': seg.speaker,
                'confidence': float(seg.confidence) if seg.confidence else None,
                'sequence_number': seg.sequence_number
            } for seg in segments]

    @staticmethod
    def update_segment(segment_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a transcript segment.

        Args:
            segment_id: Segment UUID
            updates: Dictionary of field updates

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            with DatabaseSession() as db_session:
                segment = db_session.query(TranscriptSegment).filter(
                    TranscriptSegment.id == segment_id
                ).first()

                if not segment:
                    return False

                # Update allowed fields
                allowed_fields = {'text', 'speaker', 'confidence'}
                for field, value in updates.items():
                    if field in allowed_fields and hasattr(segment, field):
                        setattr(segment, field, value)

                db_session.commit()
                return True

        except Exception as e:
            print(f"Error updating segment {segment_id}: {e}")
            return False