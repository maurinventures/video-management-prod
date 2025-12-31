"""Upload videos to S3 and register in database."""

import hashlib
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from tqdm import tqdm

from .config_loader import get_config
from .db import DatabaseSession, Video

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


def get_video_metadata(file_path: Path) -> dict:
    """Extract video metadata using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        data = json.loads(result.stdout)

        # Extract relevant info
        format_info = data.get("format", {})
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            {}
        )

        duration = float(format_info.get("duration", 0))
        width = video_stream.get("width", 0)
        height = video_stream.get("height", 0)

        return {
            "duration_seconds": duration,
            "resolution": f"{width}x{height}" if width and height else None,
            "format": format_info.get("format_name", "").split(",")[0],
            "bitrate": format_info.get("bit_rate"),
            "codec": video_stream.get("codec_name"),
        }
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.warning(f"Could not extract video metadata: {e}")
        return {}


def generate_s3_key(original_filename: str, prefix: str = "videos/") -> str:
    """Generate a unique S3 key for the video."""
    # Create a hash-based unique filename to avoid collisions
    name = Path(original_filename).stem
    ext = Path(original_filename).suffix
    hash_suffix = hashlib.md5(f"{name}{ext}".encode()).hexdigest()[:8]
    return f"{prefix}{name}_{hash_suffix}{ext}"


def upload_to_s3(
    file_path: Path,
    s3_key: str,
    bucket: Optional[str] = None,
    show_progress: bool = True,
) -> bool:
    """Upload a file to S3 with optional progress bar."""
    config = get_config()
    bucket = bucket or config.s3_bucket
    s3_client = get_s3_client()

    file_size = file_path.stat().st_size

    try:
        if show_progress:
            with tqdm(total=file_size, unit="B", unit_scale=True, desc="Uploading") as pbar:
                s3_client.upload_file(
                    str(file_path),
                    bucket,
                    s3_key,
                    Callback=lambda bytes_transferred: pbar.update(bytes_transferred),
                )
        else:
            s3_client.upload_file(str(file_path), bucket, s3_key)

        logger.info(f"Uploaded {file_path.name} to s3://{bucket}/{s3_key}")
        return True

    except ClientError as e:
        logger.error(f"Failed to upload to S3: {e}")
        return False


def check_s3_exists(s3_key: str, bucket: Optional[str] = None) -> bool:
    """Check if an object exists in S3."""
    config = get_config()
    bucket = bucket or config.s3_bucket
    s3_client = get_s3_client()

    try:
        s3_client.head_object(Bucket=bucket, Key=s3_key)
        return True
    except ClientError:
        return False


def upload_video(
    file_path: str,
    uploaded_by: Optional[str] = None,
    custom_filename: Optional[str] = None,
    show_progress: bool = True,
) -> Tuple[Optional[UUID], Optional[str]]:
    """
    Upload a video to S3 and register it in the database.

    Args:
        file_path: Path to the video file
        uploaded_by: Username of uploader
        custom_filename: Optional custom filename for S3
        show_progress: Show upload progress bar

    Returns:
        Tuple of (video_id, s3_key) or (None, None) on failure
    """
    config = get_config()
    path = Path(file_path)

    if not path.exists():
        logger.error(f"File not found: {file_path}")
        return None, None

    if not path.is_file():
        logger.error(f"Not a file: {file_path}")
        return None, None

    # Check file extension
    supported = config.settings.get("video", {}).get("supported_formats", ["mp4", "mov", "avi", "mkv"])
    ext = path.suffix.lower().lstrip(".")
    if ext not in supported:
        logger.error(f"Unsupported format: {ext}. Supported: {supported}")
        return None, None

    original_filename = path.name
    filename = custom_filename or original_filename
    s3_key = generate_s3_key(filename, config.s3_prefixes.get("videos", "videos/"))

    # Check if already exists in S3
    if check_s3_exists(s3_key):
        logger.warning(f"File already exists in S3: {s3_key}")
        # Generate new key with timestamp
        import time
        ts = int(time.time())
        name = Path(filename).stem
        ext = Path(filename).suffix
        s3_key = f"{config.s3_prefixes.get('videos', 'videos/')}{name}_{ts}{ext}"

    # Get video metadata
    metadata = get_video_metadata(path)
    file_size = path.stat().st_size

    # Upload to S3
    if not upload_to_s3(path, s3_key, show_progress=show_progress):
        return None, None

    # Register in database
    with DatabaseSession() as session:
        video = Video(
            filename=filename,
            original_filename=original_filename,
            s3_key=s3_key,
            s3_bucket=config.s3_bucket,
            file_size_bytes=file_size,
            duration_seconds=metadata.get("duration_seconds"),
            resolution=metadata.get("resolution"),
            format=metadata.get("format"),
            status="uploaded",
            uploaded_by=uploaded_by,
            extra_data=metadata,
        )
        session.add(video)
        session.flush()
        video_id = video.id

        logger.info(f"Registered video in database: {video_id}")
        return video_id, s3_key


def list_videos(status: Optional[str] = None, limit: int = 50) -> list:
    """List videos from database."""
    with DatabaseSession() as session:
        query = session.query(Video)
        if status:
            query = query.filter(Video.status == status)
        query = query.order_by(Video.created_at.desc()).limit(limit)
        videos = query.all()
        # Convert to dicts to avoid detached instance issues
        return [
            {
                "id": v.id,
                "filename": v.filename,
                "original_filename": v.original_filename,
                "s3_key": v.s3_key,
                "duration_seconds": v.duration_seconds,
                "status": v.status,
                "resolution": v.resolution,
                "file_size_bytes": v.file_size_bytes,
                "created_at": v.created_at,
            }
            for v in videos
        ]


def get_video(video_id: UUID) -> Optional[dict]:
    """Get a video by ID."""
    with DatabaseSession() as session:
        v = session.query(Video).filter(Video.id == video_id).first()
        if not v:
            return None
        return {
            "id": v.id,
            "filename": v.filename,
            "original_filename": v.original_filename,
            "s3_key": v.s3_key,
            "s3_bucket": v.s3_bucket,
            "duration_seconds": v.duration_seconds,
            "status": v.status,
            "resolution": v.resolution,
            "format": v.format,
            "file_size_bytes": v.file_size_bytes,
            "uploaded_by": v.uploaded_by,
            "created_at": v.created_at,
            "updated_at": v.updated_at,
        }


def delete_video(video_id: UUID, delete_from_s3: bool = True) -> bool:
    """Delete a video from database and optionally S3."""
    with DatabaseSession() as session:
        video = session.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video not found: {video_id}")
            return False

        if delete_from_s3:
            try:
                s3_client = get_s3_client()
                s3_client.delete_object(Bucket=video.s3_bucket, Key=video.s3_key)
                logger.info(f"Deleted from S3: {video.s3_key}")
            except ClientError as e:
                logger.error(f"Failed to delete from S3: {e}")

        session.delete(video)
        logger.info(f"Deleted video: {video_id}")
        return True
