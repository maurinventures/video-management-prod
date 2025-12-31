"""Cut clips from videos based on timestamps."""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from .config_loader import get_config
from .db import Clip, DatabaseSession, Video

logger = logging.getLogger(__name__)


def get_s3_client():
    """Get configured S3 client."""
    config = get_config()
    return boto3.client(
        "s3",
        region_name=config.aws_region,
        aws_access_key_id=config.aws_access_key,
        aws_secret_access_key=config.aws_secret_key,
    )


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def download_video(video: Video, dest_path: Path) -> bool:
    """Download video from S3 to local path."""
    s3_client = get_s3_client()
    try:
        logger.info(f"Downloading {video.s3_key} to {dest_path}")
        s3_client.download_file(video.s3_bucket, video.s3_key, str(dest_path))
        return True
    except ClientError as e:
        logger.error(f"Failed to download video: {e}")
        return False


def cut_clip_ffmpeg(
    input_path: Path,
    output_path: Path,
    start_time: float,
    end_time: float,
) -> bool:
    """
    Cut a clip from video using ffmpeg with exact timestamps (no fading).

    Uses -c copy for fast cutting when possible, falls back to re-encoding
    for frame-accurate cuts.
    """
    config = get_config()
    duration = end_time - start_time

    # First try with stream copy (fast but may not be frame-accurate)
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-ss", str(start_time),  # Seek position (before -i for fast seek)
        "-i", str(input_path),
        "-t", str(duration),
        "-c", "copy",  # Copy streams without re-encoding
        "-avoid_negative_ts", "make_zero",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(f"Created clip (stream copy): {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.warning(f"Stream copy failed, trying re-encode: {e.stderr}")

    # Fall back to re-encoding for precise cuts
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start_time),
        "-i", str(input_path),
        "-t", str(duration),
        "-c:v", config.video_codec,
        "-c:a", config.audio_codec,
        "-avoid_negative_ts", "make_zero",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(f"Created clip (re-encoded): {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create clip: {e.stderr}")
        return False


def create_clip(
    video_id: UUID,
    start_time: float,
    end_time: float,
    clip_name: str,
    notes: Optional[str] = None,
    created_by: Optional[str] = None,
) -> Optional[UUID]:
    """
    Create a clip from a video.

    Args:
        video_id: Source video ID
        start_time: Start time in seconds
        end_time: End time in seconds
        clip_name: Name for the clip
        notes: Optional notes about the clip
        created_by: Username of creator

    Returns:
        clip_id or None on failure
    """
    config = get_config()
    s3_client = get_s3_client()

    if start_time >= end_time:
        logger.error(f"Invalid time range: {start_time} >= {end_time}")
        return None

    with DatabaseSession() as session:
        video = session.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video not found: {video_id}")
            return None

        # Validate times against video duration
        if video.duration_seconds and end_time > float(video.duration_seconds):
            logger.error(f"End time {end_time} exceeds video duration {video.duration_seconds}")
            return None

        # Create clip record (pending)
        clip_s3_key = f"{config.s3_prefixes.get('clips', 'clips/')}{video_id}/{clip_name}.mp4"
        clip = Clip(
            source_video_id=video_id,
            clip_name=clip_name,
            s3_key=clip_s3_key,
            start_time=start_time,
            end_time=end_time,
            status="processing",
            notes=notes,
            created_by=created_by,
        )
        session.add(clip)
        session.flush()
        clip_id = clip.id

    # Download source video
    temp_video_path = config.temp_dir / f"{video_id}.mp4"
    temp_clip_path = config.temp_dir / f"{clip_id}.mp4"

    try:
        with DatabaseSession() as session:
            video = session.query(Video).filter(Video.id == video_id).first()
            if not download_video(video, temp_video_path):
                raise Exception("Failed to download video")

        # Cut the clip
        if not cut_clip_ffmpeg(temp_video_path, temp_clip_path, start_time, end_time):
            raise Exception("Failed to cut clip")

        # Upload clip to S3
        file_size = temp_clip_path.stat().st_size
        s3_client.upload_file(str(temp_clip_path), config.s3_bucket, clip_s3_key)
        logger.info(f"Uploaded clip to s3://{config.s3_bucket}/{clip_s3_key}")

        # Update clip record
        with DatabaseSession() as session:
            clip = session.query(Clip).filter(Clip.id == clip_id).first()
            clip.status = "completed"
            clip.file_size_bytes = file_size

        return clip_id

    except Exception as e:
        logger.error(f"Failed to create clip: {e}")
        with DatabaseSession() as session:
            clip = session.query(Clip).filter(Clip.id == clip_id).first()
            if clip:
                clip.status = "error"
        return None

    finally:
        # Clean up temp files
        if temp_video_path.exists():
            temp_video_path.unlink()
        if temp_clip_path.exists():
            temp_clip_path.unlink()


def create_clips_batch(
    video_id: UUID,
    clips_data: List[dict],
    created_by: Optional[str] = None,
) -> List[UUID]:
    """
    Create multiple clips from a video.

    Args:
        video_id: Source video ID
        clips_data: List of dicts with keys: start_time, end_time, clip_name, notes
        created_by: Username of creator

    Returns:
        List of created clip IDs
    """
    config = get_config()
    s3_client = get_s3_client()
    created_clips = []

    with DatabaseSession() as session:
        video = session.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video not found: {video_id}")
            return []

    # Download video once
    temp_video_path = config.temp_dir / f"{video_id}.mp4"

    try:
        with DatabaseSession() as session:
            video = session.query(Video).filter(Video.id == video_id).first()
            if not download_video(video, temp_video_path):
                return []

        for clip_data in clips_data:
            start_time = clip_data["start_time"]
            end_time = clip_data["end_time"]
            clip_name = clip_data["clip_name"]
            notes = clip_data.get("notes")

            if start_time >= end_time:
                logger.warning(f"Skipping invalid clip {clip_name}: {start_time} >= {end_time}")
                continue

            # Create clip record
            clip_s3_key = f"{config.s3_prefixes.get('clips', 'clips/')}{video_id}/{clip_name}.mp4"
            with DatabaseSession() as session:
                clip = Clip(
                    source_video_id=video_id,
                    clip_name=clip_name,
                    s3_key=clip_s3_key,
                    start_time=start_time,
                    end_time=end_time,
                    status="processing",
                    notes=notes,
                    created_by=created_by,
                )
                session.add(clip)
                session.flush()
                clip_id = clip.id

            # Cut clip
            temp_clip_path = config.temp_dir / f"{clip_id}.mp4"
            try:
                if cut_clip_ffmpeg(temp_video_path, temp_clip_path, start_time, end_time):
                    file_size = temp_clip_path.stat().st_size
                    s3_client.upload_file(str(temp_clip_path), config.s3_bucket, clip_s3_key)

                    with DatabaseSession() as session:
                        clip = session.query(Clip).filter(Clip.id == clip_id).first()
                        clip.status = "completed"
                        clip.file_size_bytes = file_size

                    created_clips.append(clip_id)
                    logger.info(f"Created clip {clip_name}: {clip_id}")
                else:
                    with DatabaseSession() as session:
                        clip = session.query(Clip).filter(Clip.id == clip_id).first()
                        clip.status = "error"

            finally:
                if temp_clip_path.exists():
                    temp_clip_path.unlink()

        return created_clips

    finally:
        if temp_video_path.exists():
            temp_video_path.unlink()


def get_clip(clip_id: UUID) -> Optional[Clip]:
    """Get a clip by ID."""
    with DatabaseSession() as session:
        return session.query(Clip).filter(Clip.id == clip_id).first()


def list_clips(video_id: Optional[UUID] = None, status: Optional[str] = None) -> List[Clip]:
    """List clips, optionally filtered by video or status."""
    with DatabaseSession() as session:
        query = session.query(Clip)
        if video_id:
            query = query.filter(Clip.source_video_id == video_id)
        if status:
            query = query.filter(Clip.status == status)
        return query.order_by(Clip.created_at.desc()).all()


def delete_clip(clip_id: UUID, delete_from_s3: bool = True) -> bool:
    """Delete a clip from database and optionally S3."""
    config = get_config()
    s3_client = get_s3_client()

    with DatabaseSession() as session:
        clip = session.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            logger.error(f"Clip not found: {clip_id}")
            return False

        if delete_from_s3 and clip.s3_key:
            try:
                s3_client.delete_object(Bucket=config.s3_bucket, Key=clip.s3_key)
                logger.info(f"Deleted from S3: {clip.s3_key}")
            except ClientError as e:
                logger.error(f"Failed to delete from S3: {e}")

        session.delete(clip)
        logger.info(f"Deleted clip: {clip_id}")
        return True


def download_clip(clip_id: UUID, output_path: Optional[Path] = None) -> Optional[Path]:
    """Download a clip from S3 to local path."""
    config = get_config()
    s3_client = get_s3_client()

    with DatabaseSession() as session:
        clip = session.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            logger.error(f"Clip not found: {clip_id}")
            return None

        if not clip.s3_key:
            logger.error(f"Clip has no S3 key: {clip_id}")
            return None

        if output_path is None:
            output_path = config.temp_dir / f"{clip.clip_name}.mp4"

        try:
            s3_client.download_file(config.s3_bucket, clip.s3_key, str(output_path))
            logger.info(f"Downloaded clip to {output_path}")
            return output_path
        except ClientError as e:
            logger.error(f"Failed to download clip: {e}")
            return None
