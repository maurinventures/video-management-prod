"""Compile multiple clips into a final video."""

import logging
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from .config_loader import get_config
from .db import Clip, CompiledVideo, CompiledVideoClip, DatabaseSession

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


def download_clip_file(clip: Clip, dest_path: Path) -> bool:
    """Download clip from S3 to local path."""
    config = get_config()
    s3_client = get_s3_client()
    try:
        s3_client.download_file(config.s3_bucket, clip.s3_key, str(dest_path))
        return True
    except ClientError as e:
        logger.error(f"Failed to download clip {clip.id}: {e}")
        return False


def get_video_resolution(video_path: Path) -> Optional[str]:
    """Get video resolution using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        parts = result.stdout.strip().split(",")
        if len(parts) == 2:
            return f"{parts[0]}x{parts[1]}"
    except subprocess.CalledProcessError:
        pass
    return None


def concatenate_clips_ffmpeg(
    clip_paths: List[Path],
    output_path: Path,
    normalize_resolution: bool = True,
) -> bool:
    """
    Concatenate clips using ffmpeg concat demuxer (no transitions, exact cuts).

    Args:
        clip_paths: Ordered list of clip file paths
        output_path: Path for output video
        normalize_resolution: Re-encode to ensure consistent resolution/codec

    Returns:
        True if successful
    """
    config = get_config()

    if not clip_paths:
        logger.error("No clips to concatenate")
        return False

    # Create concat file list
    concat_file = output_path.parent / f"{output_path.stem}_concat.txt"
    with open(concat_file, "w") as f:
        for clip_path in clip_paths:
            # Escape single quotes in path
            escaped_path = str(clip_path).replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")

    try:
        if normalize_resolution:
            # Re-encode to ensure consistent format
            # Get resolution from first clip
            resolution = get_video_resolution(clip_paths[0])
            width, height = (1920, 1080)  # Default
            if resolution:
                try:
                    w, h = resolution.split("x")
                    width, height = int(w), int(h)
                except ValueError:
                    pass

            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:v", config.video_codec,
                "-c:a", config.audio_codec,
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-r", "30",  # Consistent frame rate
                str(output_path),
            ]
        else:
            # Stream copy (fast, but clips must have same codec/resolution)
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output_path),
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Created compiled video: {output_path}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to concatenate clips: {e.stderr}")
        return False

    finally:
        # Clean up concat file
        if concat_file.exists():
            concat_file.unlink()


def compile_video(
    title: str,
    clip_ids: List[UUID],
    description: Optional[str] = None,
    created_by: Optional[str] = None,
    normalize_resolution: bool = True,
) -> Optional[UUID]:
    """
    Compile multiple clips into a final video.

    Args:
        title: Title for the compiled video
        clip_ids: Ordered list of clip IDs to combine
        description: Optional description
        created_by: Username of creator
        normalize_resolution: Re-encode to ensure consistent resolution

    Returns:
        compiled_video_id or None on failure
    """
    config = get_config()
    s3_client = get_s3_client()

    if not clip_ids:
        logger.error("No clips provided")
        return None

    # Validate all clips exist and are completed
    with DatabaseSession() as session:
        clips = []
        for clip_id in clip_ids:
            clip = session.query(Clip).filter(Clip.id == clip_id).first()
            if not clip:
                logger.error(f"Clip not found: {clip_id}")
                return None
            if clip.status != "completed":
                logger.error(f"Clip not completed: {clip_id} (status: {clip.status})")
                return None
            clips.append(clip)

        # Calculate total duration
        total_duration = sum(float(c.end_time - c.start_time) for c in clips)

        # Create compiled video record
        safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)
        s3_key = f"{config.s3_prefixes.get('compiled', 'compiled/')}{safe_title}.mp4"

        compiled = CompiledVideo(
            title=title,
            description=description,
            s3_key=s3_key,
            total_duration_seconds=Decimal(str(total_duration)),
            status="processing",
            created_by=created_by,
        )
        session.add(compiled)
        session.flush()
        compiled_id = compiled.id

        # Create junction records
        for i, clip_id in enumerate(clip_ids):
            junction = CompiledVideoClip(
                compiled_video_id=compiled_id,
                clip_id=clip_id,
                sequence_order=i,
                transition_type="cut",
            )
            session.add(junction)

    # Download all clips
    clip_paths = []
    temp_files = []

    try:
        with DatabaseSession() as session:
            for i, clip_id in enumerate(clip_ids):
                clip = session.query(Clip).filter(Clip.id == clip_id).first()
                temp_path = config.temp_dir / f"compile_{compiled_id}_clip_{i}.mp4"
                temp_files.append(temp_path)

                if not download_clip_file(clip, temp_path):
                    raise Exception(f"Failed to download clip {clip_id}")

                clip_paths.append(temp_path)

        # Concatenate clips
        output_path = config.temp_dir / f"{compiled_id}.mp4"
        temp_files.append(output_path)

        if not concatenate_clips_ffmpeg(clip_paths, output_path, normalize_resolution):
            raise Exception("Failed to concatenate clips")

        # Get file size and resolution
        file_size = output_path.stat().st_size
        resolution = get_video_resolution(output_path)

        # Upload to S3
        s3_client.upload_file(str(output_path), config.s3_bucket, s3_key)
        logger.info(f"Uploaded compiled video to s3://{config.s3_bucket}/{s3_key}")

        # Update record
        with DatabaseSession() as session:
            compiled = session.query(CompiledVideo).filter(CompiledVideo.id == compiled_id).first()
            compiled.status = "completed"
            compiled.file_size_bytes = file_size
            compiled.resolution = resolution

        logger.info(f"Compiled video created: {compiled_id}")
        return compiled_id

    except Exception as e:
        logger.error(f"Failed to compile video: {e}")
        with DatabaseSession() as session:
            compiled = session.query(CompiledVideo).filter(CompiledVideo.id == compiled_id).first()
            if compiled:
                compiled.status = "error"
        return None

    finally:
        # Clean up temp files
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()


def get_compiled_video(compiled_id: UUID) -> Optional[CompiledVideo]:
    """Get a compiled video by ID."""
    with DatabaseSession() as session:
        return session.query(CompiledVideo).filter(CompiledVideo.id == compiled_id).first()


def list_compiled_videos(status: Optional[str] = None, limit: int = 50) -> List[CompiledVideo]:
    """List compiled videos."""
    with DatabaseSession() as session:
        query = session.query(CompiledVideo)
        if status:
            query = query.filter(CompiledVideo.status == status)
        return query.order_by(CompiledVideo.created_at.desc()).limit(limit).all()


def get_compiled_video_clips(compiled_id: UUID) -> List[Clip]:
    """Get clips in a compiled video in order."""
    with DatabaseSession() as session:
        junctions = session.query(CompiledVideoClip).filter(
            CompiledVideoClip.compiled_video_id == compiled_id
        ).order_by(CompiledVideoClip.sequence_order).all()

        return [
            session.query(Clip).filter(Clip.id == j.clip_id).first()
            for j in junctions
        ]


def delete_compiled_video(compiled_id: UUID, delete_from_s3: bool = True) -> bool:
    """Delete a compiled video from database and optionally S3."""
    config = get_config()
    s3_client = get_s3_client()

    with DatabaseSession() as session:
        compiled = session.query(CompiledVideo).filter(CompiledVideo.id == compiled_id).first()
        if not compiled:
            logger.error(f"Compiled video not found: {compiled_id}")
            return False

        if delete_from_s3 and compiled.s3_key:
            try:
                s3_client.delete_object(Bucket=config.s3_bucket, Key=compiled.s3_key)
                logger.info(f"Deleted from S3: {compiled.s3_key}")
            except ClientError as e:
                logger.error(f"Failed to delete from S3: {e}")

        session.delete(compiled)
        logger.info(f"Deleted compiled video: {compiled_id}")
        return True


def download_compiled_video(compiled_id: UUID, output_path: Optional[Path] = None) -> Optional[Path]:
    """Download a compiled video from S3 to local path."""
    config = get_config()
    s3_client = get_s3_client()

    with DatabaseSession() as session:
        compiled = session.query(CompiledVideo).filter(CompiledVideo.id == compiled_id).first()
        if not compiled:
            logger.error(f"Compiled video not found: {compiled_id}")
            return None

        if not compiled.s3_key:
            logger.error(f"Compiled video has no S3 key: {compiled_id}")
            return None

        if output_path is None:
            safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in compiled.title)
            output_path = config.temp_dir / f"{safe_title}.mp4"

        try:
            s3_client.download_file(config.s3_bucket, compiled.s3_key, str(output_path))
            logger.info(f"Downloaded compiled video to {output_path}")
            return output_path
        except ClientError as e:
            logger.error(f"Failed to download compiled video: {e}")
            return None
