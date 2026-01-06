"""
Video Service

Handles all video-related operations including download, processing, validation,
caching, and metadata management with FFmpeg integration.
"""

import os
import re
import subprocess
import shutil
import time
import urllib.request
from pathlib import Path
from uuid import UUID
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

# Import database models and session
try:
    from scripts.db import DatabaseSession, Video, Transcript, TranscriptSegment
    from scripts.config_loader import get_config
except ImportError:
    from ..scripts.db import DatabaseSession, Video, Transcript, TranscriptSegment
    from ..scripts.config_loader import get_config

# Import boto3 for S3
try:
    import boto3
except ImportError:
    boto3 = None


def get_s3_client():
    """Get configured S3 client."""
    config = get_config()
    return boto3.client(
        's3',
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
        region_name=config.aws_region
    )


class VideoService:
    """Service for managing video operations, processing, and downloads."""

    # Cache configuration
    CACHE_BASE_PATH = Path('/home/ec2-user/video_cache')
    VIDEOS_CACHE_PATH = CACHE_BASE_PATH / 'videos'
    CLIPS_CACHE_PATH = CACHE_BASE_PATH / 'clips'
    MAX_CACHED_CLIPS = 50
    CACHE_EXPIRY_HOURS = 24

    # FFmpeg configuration
    DEFAULT_FFMPEG_SETTINGS = {
        'video_codec': 'libx264',
        'profile': 'high',
        'level': '4.0',
        'pixel_format': 'yuv420p',
        'preset': 'fast',
        'crf': '18',  # High quality
        'audio_codec': 'aac',
        'audio_bitrate': '192k',
        'audio_rate': '48000',
        'movflags': '+faststart'
    }

    @staticmethod
    def _ensure_cache_directories():
        """Ensure cache directories exist."""
        VideoService.CACHE_BASE_PATH.mkdir(exist_ok=True)
        VideoService.VIDEOS_CACHE_PATH.mkdir(exist_ok=True)
        VideoService.CLIPS_CACHE_PATH.mkdir(exist_ok=True)

    @staticmethod
    def _cleanup_old_clips():
        """Clean up old clips to save space (keep only last N clips)."""
        try:
            existing_clips = sorted(
                VideoService.CLIPS_CACHE_PATH.glob('*.mp4'),
                key=lambda x: x.stat().st_mtime
            )
            if len(existing_clips) > VideoService.MAX_CACHED_CLIPS:
                for old_clip in existing_clips[:-VideoService.MAX_CACHED_CLIPS]:
                    old_clip.unlink()
        except Exception as e:
            print(f"[WARNING] Failed to cleanup old clips: {e}")

    @staticmethod
    def get_video_by_id(video_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get video by ID with user ownership validation.

        Args:
            video_id: Video UUID
            user_id: User ID for ownership validation

        Returns:
            Video data dictionary or None if not found/unauthorized
        """
        with DatabaseSession() as db_session:
            video = db_session.query(Video).filter(
                Video.id == UUID(video_id),
                Video.uploaded_by == user_id
            ).first()

            if not video:
                return None

            return {
                'id': str(video.id),
                'filename': video.filename,
                'original_filename': video.original_filename,
                's3_key': video.s3_key,
                'duration_seconds': float(video.duration_seconds) if video.duration_seconds else 0,
                'file_size_bytes': video.file_size_bytes or 0,
                'format': video.format or 'mp4',
                'resolution': video.resolution or 'unknown',
                'speaker': video.speaker,
                'event_name': video.event_name,
                'event_date': video.event_date,
                'uploaded_by': video.uploaded_by,
                'created_at': video.created_at,
                'updated_at': video.updated_at
            }

    @staticmethod
    def get_download_options(video_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get download options and metadata for a video.

        Args:
            video_id: Video UUID
            user_id: User ID for ownership validation

        Returns:
            Download options and cache status

        Raises:
            FileNotFoundError: If video not found or unauthorized
        """
        video = VideoService.get_video_by_id(video_id, user_id)
        if not video:
            raise FileNotFoundError('Video not found or unauthorized')

        # Check if video is cached
        VideoService._ensure_cache_directories()
        cached_video = VideoService.VIDEOS_CACHE_PATH / f"{video_id}.mp4"
        video_cached = cached_video.exists() and cached_video.stat().st_size > 1000

        # Calculate cache expiry
        cache_expires_at = None
        if video_cached:
            cache_time = datetime.fromtimestamp(cached_video.stat().st_mtime)
            cache_expires_at = (cache_time + timedelta(hours=VideoService.CACHE_EXPIRY_HOURS)).isoformat()

        return {
            'video_id': video['id'],
            'title': video['filename'] or 'Unknown Video',
            'duration_seconds': video['duration_seconds'],
            'file_size_bytes': video['file_size_bytes'],
            'format': video['format'],
            'resolution': video['resolution'],
            'download_options': {
                'full_source': {
                    'endpoint': f'/api/video-download/{video_id}',
                    'file_size_bytes': video['file_size_bytes'],
                    'duration_seconds': video['duration_seconds'],
                    'format': video['format']
                },
                'trimmed_segment': {
                    'endpoint': f'/api/clip-download/{video_id}',
                    'parameters': {
                        'start': 'Start time in seconds (float)',
                        'end': 'End time in seconds (float)',
                        'metadata': 'Include metadata (boolean, default true)',
                        'timeout': 'Processing timeout in seconds (default 300, max 900)'
                    },
                    'max_duration': 600,
                    'supported_formats': ['mp4']
                }
            },
            'cache_status': {
                'video_cached': video_cached,
                'cache_expires_at': cache_expires_at
            }
        }

    @staticmethod
    def generate_download_url(video_id: str, user_id: str) -> Dict[str, Any]:
        """
        Generate download URL for full video.

        Args:
            video_id: Video UUID
            user_id: User ID for ownership validation

        Returns:
            Download URL and metadata

        Raises:
            FileNotFoundError: If video not found or unauthorized
            ValueError: If video not in S3
        """
        video = VideoService.get_video_by_id(video_id, user_id)
        if not video:
            raise FileNotFoundError('Video not found or unauthorized')

        if not video['s3_key']:
            raise ValueError('Video not in S3')

        config = get_config()
        bucket = config.s3_bucket
        s3_client = get_s3_client()

        # Generate presigned URL for direct download
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': video['s3_key'],
                'ResponseContentDisposition': f'attachment; filename="{video["filename"]}"'
            },
            ExpiresIn=3600
        )

        return {
            'download_url': download_url,
            'metadata': {
                'video_id': video['id'],
                'title': video['filename'] or 'Unknown Video',
                'duration_seconds': video['duration_seconds'],
                'file_size_bytes': video['file_size_bytes'],
                'format': video['format'],
                'resolution': video['resolution'],
                'original_filename': video['original_filename'] or video['filename']
            }
        }

    @staticmethod
    def process_clip_download(
        video_id: str,
        user_id: str,
        start_time: float,
        end_time: float,
        include_metadata: bool = True,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Process and download a video clip with FFmpeg.

        Args:
            video_id: Video UUID
            user_id: User ID for ownership validation
            start_time: Clip start time in seconds
            end_time: Clip end time in seconds
            include_metadata: Whether to include metadata in response
            timeout: Processing timeout in seconds (max 900)

        Returns:
            Download URL and metadata or file path for direct serving

        Raises:
            ValueError: If invalid parameters
            FileNotFoundError: If video not found
            subprocess.TimeoutExpired: If processing times out
        """
        # Validation
        if start_time < 0 or end_time <= start_time:
            raise ValueError('Invalid time range')

        timeout = min(timeout, 900)  # Max 15 minutes
        duration = end_time - start_time
        processing_start = time.time()

        video = VideoService.get_video_by_id(video_id, user_id)
        if not video:
            raise FileNotFoundError('Video not found or unauthorized')

        # Validate time range against video duration
        if video['duration_seconds'] and end_time > video['duration_seconds']:
            raise ValueError(f'End time ({end_time}s) exceeds video duration ({video["duration_seconds"]}s)')

        if not video['s3_key']:
            raise ValueError('Video not in S3')

        # Setup cache and download video if needed
        VideoService._ensure_cache_directories()
        cached_video = VideoService.VIDEOS_CACHE_PATH / f"{video_id}.mp4"

        if not cached_video.exists() or cached_video.stat().st_size < 1000:
            VideoService._download_video_to_cache(video, cached_video)

        # Setup output paths
        safe_name = re.sub(r'[^\w\-_ ]', '_', video['filename'] or 'clip')
        safe_name = safe_name.replace('.mp4', '')
        filename = f"{safe_name}_{start_time:.0f}s-{end_time:.0f}s.mp4"
        output_path = VideoService.CLIPS_CACHE_PATH / f"{video_id}_{start_time:.0f}_{end_time:.0f}.mp4"

        # Clean up old clips
        VideoService._cleanup_old_clips()

        # Process clip with FFmpeg
        VideoService._extract_clip_with_ffmpeg(
            cached_video, output_path, start_time, duration, timeout
        )

        # Generate results
        processing_time_ms = int((time.time() - processing_start) * 1000)
        file_size = output_path.stat().st_size
        clip_title = f"{video['filename'] or 'Video'} - {start_time:.0f}s-{end_time:.0f}s"
        if clip_title.endswith('.mp4.mp4'):
            clip_title = clip_title[:-4]

        if include_metadata:
            # Upload to S3 and return metadata
            download_url = VideoService._upload_clip_to_s3(
                output_path, video_id, start_time, end_time, filename
            )

            return {
                'download_url': download_url,
                'metadata': {
                    'source_video_id': video['id'],
                    'title': clip_title,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_seconds': duration,
                    'file_size_bytes': file_size,
                    'format': 'mp4',
                    'resolution': video['resolution'],
                    'cached': True,
                    'processing_time_ms': processing_time_ms
                }
            }
        else:
            # Return file path for direct serving
            return {
                'file_path': str(output_path),
                'filename': filename,
                'mimetype': 'video/mp4'
            }

    @staticmethod
    def _download_video_to_cache(video: Dict[str, Any], cache_path: Path):
        """Download video from S3 to local cache."""
        print(f"[DOWNLOAD] Downloading video {video['id']}...")

        config = get_config()
        bucket = config.s3_bucket
        s3_client = get_s3_client()

        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': video['s3_key']},
            ExpiresIn=3600
        )
        urllib.request.urlretrieve(presigned_url, str(cache_path))
        print(f"[DOWNLOAD] Downloaded {cache_path.stat().st_size} bytes")

    @staticmethod
    def _extract_clip_with_ffmpeg(
        input_path: Path,
        output_path: Path,
        start_time: float,
        duration: float,
        timeout: int
    ):
        """Extract video clip using FFmpeg."""
        ffmpeg_path = shutil.which('ffmpeg') or '/usr/local/bin/ffmpeg'
        settings = VideoService.DEFAULT_FFMPEG_SETTINGS

        print(f"[DOWNLOAD] Extracting clip from {start_time}s for {duration}s")

        cmd = [
            ffmpeg_path, '-y',
            '-ss', str(start_time),
            '-i', str(input_path),
            '-t', str(duration),
            '-c:v', settings['video_codec'],
            '-profile:v', settings['profile'],
            '-level', settings['level'],
            '-pix_fmt', settings['pixel_format'],
            '-preset', settings['preset'],
            '-crf', settings['crf'],
            '-c:a', settings['audio_codec'],
            '-b:a', settings['audio_bitrate'],
            '-ar', settings['audio_rate'],
            '-movflags', settings['movflags'],
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=timeout)

        if result.returncode != 0:
            error_msg = result.stderr.decode()[:500]
            print(f"[DOWNLOAD] Encoding failed: {error_msg}")
            raise RuntimeError(f'Failed to extract clip: {error_msg}')

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError('Output file is empty or missing')

        print(f"[DOWNLOAD] Success: {output_path} ({output_path.stat().st_size} bytes)")

    @staticmethod
    def _upload_clip_to_s3(
        clip_path: Path,
        video_id: str,
        start_time: float,
        end_time: float,
        filename: str
    ) -> str:
        """Upload clip to S3 and return download URL."""
        config = get_config()
        bucket = config.s3_bucket
        s3_client = get_s3_client()

        clip_s3_key = f"clips/{video_id}_{start_time:.0f}_{end_time:.0f}.mp4"

        try:
            s3_client.upload_file(str(clip_path), bucket, clip_s3_key)
            # Generate presigned URL
            download_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket,
                    'Key': clip_s3_key,
                    'ResponseContentDisposition': f'attachment; filename="{filename}"'
                },
                ExpiresIn=3600
            )
            return download_url
        except Exception as e:
            print(f"[WARNING] S3 upload failed: {e}")
            # Fallback to direct file serving endpoint
            return f"/api/clip-download/{video_id}?start={start_time}&end={end_time}&metadata=false"

    @staticmethod
    def validate_clips_against_database(clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate clips against database with fuzzy matching and transcript verification.

        Args:
            clips: List of clip dictionaries with video_id, video_title, start_time, end_time, text

        Returns:
            List of validated and corrected clips
        """
        validated = []

        with DatabaseSession() as db_session:
            # Pre-load all videos for fuzzy matching
            all_videos = db_session.query(Video).all()
            video_id_map = {str(v.id): v for v in all_videos}
            video_title_map = {v.filename.lower(): v for v in all_videos if v.filename}

            for clip in clips:
                video_id = clip.get('video_id')
                video_title = clip.get('video_title', '')
                start_time = clip.get('start_time', 0)
                end_time = clip.get('end_time', 0)
                claimed_text = clip.get('text', '')

                video = VideoService._find_video_by_fuzzy_matching(
                    db_session, video_id, video_title, video_id_map, video_title_map
                )

                if not video:
                    print(f"[VALIDATION] No video found for ID: {video_id}, title: {video_title}")
                    continue

                # Validate transcript text
                validated_clip = VideoService._validate_clip_text(
                    db_session, video, clip, start_time, end_time, claimed_text
                )

                if validated_clip:
                    validated.append(validated_clip)

        return validated

    @staticmethod
    def _find_video_by_fuzzy_matching(
        db_session,
        video_id: str,
        video_title: str,
        video_id_map: Dict[str, Any],
        video_title_map: Dict[str, Any]
    ) -> Optional[Any]:
        """Find video using fuzzy matching strategies."""
        video = None

        # 1. Try exact video ID match
        try:
            video = db_session.query(Video).filter(Video.id == UUID(video_id)).first()
        except:
            pass

        # 2. Try fuzzy ID matching (1-2 character difference)
        if not video and video_id:
            for existing_id, existing_video in video_id_map.items():
                if len(existing_id) == len(video_id):
                    diff_count = sum(1 for a, b in zip(existing_id, video_id) if a != b)
                    if diff_count <= 2:  # Allow up to 2 character differences
                        video = existing_video
                        print(f"[FUZZY MATCH] ID {video_id} -> {existing_id} (diff: {diff_count})")
                        break

        # 3. Try matching by video title
        if not video and video_title:
            title_lower = video_title.lower()
            # Exact title match
            if title_lower in video_title_map:
                video = video_title_map[title_lower]
                print(f"[TITLE MATCH] Found video by exact title: {video_title}")
            else:
                # Partial title match
                for filename, v in video_title_map.items():
                    if title_lower in filename or filename in title_lower:
                        video = v
                        print(f"[TITLE MATCH] Found video by partial title: {video_title} -> {v.filename}")
                        break

        return video

    @staticmethod
    def _validate_clip_text(
        db_session,
        video: Any,
        clip: Dict[str, Any],
        start_time: float,
        end_time: float,
        claimed_text: str
    ) -> Optional[Dict[str, Any]]:
        """Validate clip text against transcript and return corrected clip."""
        # Find matching or nearby segments
        transcript = db_session.query(Transcript).filter(
            Transcript.video_id == video.id,
            Transcript.status == 'completed'
        ).first()

        if not transcript:
            print(f"[VALIDATION] No transcript for video: {video.filename}")
            return None

        # Look for segments in the time range
        segments = db_session.query(TranscriptSegment).filter(
            TranscriptSegment.transcript_id == transcript.id,
            TranscriptSegment.start_time <= end_time,
            TranscriptSegment.end_time >= start_time
        ).order_by(TranscriptSegment.start_time).all()

        if segments:
            # Use actual transcript text and times
            actual_text = ' '.join(seg.text for seg in segments)
            actual_start = float(segments[0].start_time)
            actual_end = float(segments[-1].end_time)

            # Return corrected clip
            return {
                **clip,
                'video_id': str(video.id),
                'video_title': video.filename,
                'start_time': actual_start,
                'end_time': actual_end,
                'text': actual_text,
                'speaker': video.speaker or 'Unknown',
                'event_name': video.event_name or 'Unknown',
                'validation_status': 'corrected'
            }
        else:
            print(f"[VALIDATION] No transcript segments found for time range {start_time}-{end_time}")
            return None

    @staticmethod
    def clean_clip_text(text: str) -> str:
        """
        Clean and normalize clip text for better readability.

        Args:
            text: Raw clip text

        Returns:
            Cleaned text
        """
        if not text:
            return text

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove filler words at the start
        text = re.sub(r'^(um|uh|like|you know|so|well|actually)\s+', '', text, flags=re.IGNORECASE)

        # Remove trailing ellipsis and clean up endings
        text = re.sub(r'\.{2,}$', '.', text)
        text = re.sub(r'\s+([.!?])', r'\1', text)

        # Ensure proper capitalization
        text = text.strip()
        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        return text