#!/usr/bin/env python3
"""Pre-generate thumbnails for all videos and store in S3."""

import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from uuid import UUID

# Add the scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import boto3

from config_loader import get_config
from sqlalchemy import create_engine, Column, String, BigInteger, Numeric, Date, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import sessionmaker, declarative_base
import uuid
from datetime import datetime

Base = declarative_base()


class Video(Base):
    """Simplified Video model for thumbnail generation."""
    __tablename__ = "videos"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    s3_key = Column(String(1000), nullable=False, unique=True)
    thumbnail_s3_key = Column(String(1000))


CACHE_DIR = Path("/home/ec2-user/video_cache")


def get_or_download_video(video_id, s3_key, s3_client, bucket):
    """Download video to local cache if not present, return local path."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    local_path = CACHE_DIR / f"{video_id}.mp4"

    if local_path.exists() and local_path.stat().st_size > 0:
        return str(local_path)

    # Download from S3
    try:
        s3_client.download_file(bucket, s3_key, str(local_path))
        return str(local_path)
    except Exception as e:
        print(f"  Download error: {e}")
        return None


def generate_thumbnail_for_video(video, s3_client, bucket, ffmpeg_path):
    """Generate a thumbnail for a single video and upload to S3."""
    local_video = None
    thumb_path = None
    try:
        # Download video locally first (FFmpeg works better with local files)
        local_video = get_or_download_video(str(video.id), video.s3_key, s3_client, bucket)
        if not local_video:
            return None

        # Create temp file for thumbnail
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            thumb_path = tmp.name

        # Extract thumbnail at 5 seconds (or beginning if video is short)
        cmd = [
            ffmpeg_path, '-y',
            '-ss', '5',  # 5 seconds in
            '-i', local_video,
            '-vframes', '1',
            '-vf', 'scale=400:-1',  # 400px wide, maintain aspect
            '-q:v', '2',  # High quality
            thumb_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)

        if result.returncode != 0:
            # Try at 0 seconds if 5s failed
            cmd[3] = '0'
            result = subprocess.run(cmd, capture_output=True, timeout=120)

        if result.returncode != 0 or not Path(thumb_path).exists():
            print(f"  FAILED: {result.stderr.decode()[:100]}")
            return None

        # Upload to S3
        thumb_s3_key = f"thumbnails/{video.id}.jpg"
        s3_client.upload_file(
            thumb_path,
            bucket,
            thumb_s3_key,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )

        return thumb_s3_key

    except Exception as e:
        print(f"  ERROR: {e}")
        return None
    finally:
        # Always clean up cached video and temp thumbnail to free disk space
        if thumb_path:
            Path(thumb_path).unlink(missing_ok=True)
        if local_video:
            Path(local_video).unlink(missing_ok=True)


def main():
    config = get_config()
    bucket = config.s3_bucket

    s3_client = boto3.client(
        's3',
        aws_access_key_id=config.aws_access_key,
        aws_secret_access_key=config.aws_secret_key,
        region_name=config.aws_region
    )

    ffmpeg_path = shutil.which('ffmpeg') or '/usr/local/bin/ffmpeg'

    # Create database session directly
    engine = create_engine(config.db_connection_string, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db_session = Session()

    try:
        # Get videos without thumbnails
        videos = db_session.query(Video).filter(
            Video.thumbnail_s3_key.is_(None),
            Video.s3_key.isnot(None)
        ).all()

        print(f"Generating thumbnails for {len(videos)} videos...")

        for i, video in enumerate(videos):
            print(f"[{i+1}/{len(videos)}] {video.filename}...", end=" ", flush=True)

            thumb_key = generate_thumbnail_for_video(video, s3_client, bucket, ffmpeg_path)

            if thumb_key:
                video.thumbnail_s3_key = thumb_key
                db_session.commit()
                print("OK")
            else:
                print("FAILED")

        print("Done!")
    finally:
        db_session.close()


if __name__ == "__main__":
    main()
