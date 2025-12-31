#!/usr/bin/env python3
"""Video Management System CLI."""

import logging
import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

import click

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.config_loader import get_config
from scripts.db import init_db

# Set up logging
def setup_logging():
    config = get_config()
    log_file = Path(config.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format=config.settings.get("logging", {}).get(
            "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ),
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug: bool):
    """Video Management System - Upload, transcribe, clip, and compile videos."""
    setup_logging()
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)


# ============ Video Commands ============

@cli.group()
def video():
    """Video upload and management commands."""
    pass


@video.command("upload")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--user", "-u", help="Username of uploader")
@click.option("--name", "-n", help="Custom filename")
def video_upload(file_path: str, user: Optional[str], name: Optional[str]):
    """Upload a video to S3."""
    from scripts.upload_video import upload_video

    video_id, s3_key = upload_video(file_path, uploaded_by=user, custom_filename=name)
    if video_id:
        click.echo(f"Uploaded successfully!")
        click.echo(f"  Video ID: {video_id}")
        click.echo(f"  S3 Key: {s3_key}")
    else:
        click.echo("Upload failed.", err=True)
        sys.exit(1)


@video.command("list")
@click.option("--status", "-s", help="Filter by status")
@click.option("--limit", "-l", default=20, help="Max results")
def video_list(status: Optional[str], limit: int):
    """List videos in the database."""
    from scripts.upload_video import list_videos

    videos = list_videos(status=status, limit=limit)
    if not videos:
        click.echo("No videos found.")
        return

    click.echo(f"{'ID':<36} {'Filename':<30} {'Status':<12} {'Duration':<10}")
    click.echo("-" * 90)
    for v in videos:
        duration = f"{float(v['duration_seconds']):.1f}s" if v['duration_seconds'] else "N/A"
        click.echo(f"{str(v['id']):<36} {v['filename'][:28]:<30} {v['status']:<12} {duration:<10}")


@video.command("info")
@click.argument("video_id")
def video_info(video_id: str):
    """Show details for a video."""
    from scripts.upload_video import get_video

    video = get_video(UUID(video_id))
    if not video:
        click.echo("Video not found.", err=True)
        sys.exit(1)

    click.echo(f"ID: {video['id']}")
    click.echo(f"Filename: {video['filename']}")
    click.echo(f"Original: {video['original_filename']}")
    click.echo(f"S3 Key: {video['s3_key']}")
    click.echo(f"Status: {video['status']}")
    click.echo(f"Duration: {video['duration_seconds']}s" if video['duration_seconds'] else "Duration: N/A")
    click.echo(f"Resolution: {video['resolution'] or 'N/A'}")
    click.echo(f"Size: {video['file_size_bytes']:,} bytes" if video['file_size_bytes'] else "Size: N/A")
    click.echo(f"Uploaded: {video['created_at']}")


@video.command("delete")
@click.argument("video_id")
@click.option("--keep-s3", is_flag=True, help="Keep file in S3")
@click.confirmation_option(prompt="Are you sure you want to delete this video?")
def video_delete(video_id: str, keep_s3: bool):
    """Delete a video."""
    from scripts.upload_video import delete_video

    if delete_video(UUID(video_id), delete_from_s3=not keep_s3):
        click.echo("Video deleted.")
    else:
        click.echo("Failed to delete video.", err=True)
        sys.exit(1)


# ============ Transcription Commands ============

@cli.group()
def transcribe():
    """Transcription commands."""
    pass


@transcribe.command("start")
@click.argument("video_id")
@click.option("--provider", "-p", type=click.Choice(["aws", "whisper"]), help="Transcription provider")
@click.option("--no-wait", is_flag=True, help="Don't wait for completion (AWS only)")
def transcribe_start(video_id: str, provider: Optional[str], no_wait: bool):
    """Transcribe a video."""
    from scripts.transcribe import transcribe_video

    click.echo(f"Starting transcription for video {video_id}...")
    transcript_id = transcribe_video(UUID(video_id), provider=provider, wait=not no_wait)

    if transcript_id:
        click.echo(f"Transcription completed!")
        click.echo(f"  Transcript ID: {transcript_id}")
    else:
        click.echo("Transcription failed.", err=True)
        sys.exit(1)


@transcribe.command("status")
@click.argument("job_name")
def transcribe_status(job_name: str):
    """Check AWS Transcribe job status."""
    from scripts.transcribe import check_transcription_status

    status = check_transcription_status(job_name)
    click.echo(f"Status: {status['status']}")
    if status.get("output_uri"):
        click.echo(f"Output: {status['output_uri']}")
    if status.get("failure_reason"):
        click.echo(f"Error: {status['failure_reason']}")


@transcribe.command("view")
@click.argument("video_id")
def transcribe_view(video_id: str):
    """View transcript for a video."""
    from scripts.transcribe import get_transcript_for_video, get_transcript_segments

    transcript = get_transcript_for_video(UUID(video_id))
    if not transcript:
        click.echo("No transcript found for this video.", err=True)
        sys.exit(1)

    click.echo(f"Transcript ID: {transcript.id}")
    click.echo(f"Provider: {transcript.provider}")
    click.echo(f"Word count: {transcript.word_count}")
    click.echo(f"Status: {transcript.status}")
    click.echo("")
    click.echo("Segments:")
    click.echo("-" * 80)

    segments = get_transcript_segments(transcript.id)
    for seg in segments:
        start = f"{float(seg.start_time):.1f}s"
        end = f"{float(seg.end_time):.1f}s"
        click.echo(f"[{start} - {end}] {seg.text}")


@transcribe.command("search")
@click.argument("video_id")
@click.argument("query")
def transcribe_search(video_id: str, query: str):
    """Search transcript for a phrase."""
    from scripts.transcribe import search_transcript

    results = search_transcript(UUID(video_id), query)
    if not results:
        click.echo("No matches found.")
        return

    click.echo(f"Found {len(results)} matches:")
    click.echo("-" * 80)
    for r in results:
        click.echo(f"[{r['start_time']:.1f}s - {r['end_time']:.1f}s] {r['text']}")


# ============ Clip Commands ============

@cli.group()
def clip():
    """Clip management commands."""
    pass


@clip.command("create")
@click.argument("video_id")
@click.argument("start_time", type=float)
@click.argument("end_time", type=float)
@click.argument("clip_name")
@click.option("--notes", "-n", help="Notes about the clip")
@click.option("--user", "-u", help="Username of creator")
def clip_create(video_id: str, start_time: float, end_time: float, clip_name: str, notes: Optional[str], user: Optional[str]):
    """Create a clip from a video.

    START_TIME and END_TIME are in seconds.
    """
    from scripts.clip_video import create_clip

    click.echo(f"Creating clip from {start_time}s to {end_time}s...")
    clip_id = create_clip(
        UUID(video_id),
        start_time,
        end_time,
        clip_name,
        notes=notes,
        created_by=user,
    )

    if clip_id:
        click.echo(f"Clip created!")
        click.echo(f"  Clip ID: {clip_id}")
    else:
        click.echo("Failed to create clip.", err=True)
        sys.exit(1)


@clip.command("batch")
@click.argument("video_id")
@click.argument("clips_file", type=click.Path(exists=True))
@click.option("--user", "-u", help="Username of creator")
def clip_batch(video_id: str, clips_file: str, user: Optional[str]):
    """Create multiple clips from a JSON file.

    CLIPS_FILE should be a JSON file with array of objects:
    [{"start_time": 0, "end_time": 10, "clip_name": "intro", "notes": "optional"}]
    """
    import json
    from scripts.clip_video import create_clips_batch

    with open(clips_file) as f:
        clips_data = json.load(f)

    click.echo(f"Creating {len(clips_data)} clips...")
    clip_ids = create_clips_batch(UUID(video_id), clips_data, created_by=user)

    click.echo(f"Created {len(clip_ids)} clips:")
    for cid in clip_ids:
        click.echo(f"  {cid}")


@clip.command("list")
@click.option("--video", "-v", "video_id", help="Filter by source video ID")
@click.option("--status", "-s", help="Filter by status")
def clip_list(video_id: Optional[str], status: Optional[str]):
    """List clips."""
    from scripts.clip_video import list_clips

    vid = UUID(video_id) if video_id else None
    clips = list_clips(video_id=vid, status=status)

    if not clips:
        click.echo("No clips found.")
        return

    click.echo(f"{'ID':<36} {'Name':<25} {'Start':<8} {'End':<8} {'Status':<10}")
    click.echo("-" * 90)
    for c in clips:
        click.echo(f"{str(c.id):<36} {c.clip_name[:23]:<25} {float(c.start_time):<8.1f} {float(c.end_time):<8.1f} {c.status:<10}")


@clip.command("delete")
@click.argument("clip_id")
@click.option("--keep-s3", is_flag=True, help="Keep file in S3")
@click.confirmation_option(prompt="Are you sure you want to delete this clip?")
def clip_delete(clip_id: str, keep_s3: bool):
    """Delete a clip."""
    from scripts.clip_video import delete_clip

    if delete_clip(UUID(clip_id), delete_from_s3=not keep_s3):
        click.echo("Clip deleted.")
    else:
        click.echo("Failed to delete clip.", err=True)
        sys.exit(1)


# ============ Compile Commands ============

@cli.group()
def compile():
    """Compile videos from clips."""
    pass


@compile.command("create")
@click.argument("title")
@click.argument("clip_ids", nargs=-1, required=True)
@click.option("--description", "-d", help="Video description")
@click.option("--user", "-u", help="Username of creator")
@click.option("--no-normalize", is_flag=True, help="Skip resolution normalization")
def compile_create(title: str, clip_ids: tuple, description: Optional[str], user: Optional[str], no_normalize: bool):
    """Compile clips into a final video.

    CLIP_IDS are the UUIDs of clips to combine, in order.
    """
    from scripts.compile_video import compile_video

    clip_uuids = [UUID(cid) for cid in clip_ids]
    click.echo(f"Compiling {len(clip_uuids)} clips into '{title}'...")

    compiled_id = compile_video(
        title,
        clip_uuids,
        description=description,
        created_by=user,
        normalize_resolution=not no_normalize,
    )

    if compiled_id:
        click.echo(f"Video compiled!")
        click.echo(f"  Compiled Video ID: {compiled_id}")
    else:
        click.echo("Failed to compile video.", err=True)
        sys.exit(1)


@compile.command("list")
@click.option("--status", "-s", help="Filter by status")
@click.option("--limit", "-l", default=20, help="Max results")
def compile_list(status: Optional[str], limit: int):
    """List compiled videos."""
    from scripts.compile_video import list_compiled_videos

    videos = list_compiled_videos(status=status, limit=limit)
    if not videos:
        click.echo("No compiled videos found.")
        return

    click.echo(f"{'ID':<36} {'Title':<30} {'Duration':<12} {'Status':<10}")
    click.echo("-" * 90)
    for v in videos:
        duration = f"{v.total_duration_seconds:.1f}s" if v.total_duration_seconds else "N/A"
        click.echo(f"{str(v.id):<36} {v.title[:28]:<30} {duration:<12} {v.status:<10}")


@compile.command("info")
@click.argument("compiled_id")
def compile_info(compiled_id: str):
    """Show details for a compiled video."""
    from scripts.compile_video import get_compiled_video, get_compiled_video_clips

    video = get_compiled_video(UUID(compiled_id))
    if not video:
        click.echo("Compiled video not found.", err=True)
        sys.exit(1)

    click.echo(f"ID: {video.id}")
    click.echo(f"Title: {video.title}")
    click.echo(f"Description: {video.description or 'N/A'}")
    click.echo(f"S3 Key: {video.s3_key}")
    click.echo(f"Status: {video.status}")
    click.echo(f"Duration: {video.total_duration_seconds}s" if video.total_duration_seconds else "Duration: N/A")
    click.echo(f"Resolution: {video.resolution or 'N/A'}")
    click.echo(f"Size: {video.file_size_bytes:,} bytes" if video.file_size_bytes else "Size: N/A")
    click.echo(f"Created: {video.created_at}")
    click.echo("")
    click.echo("Clips:")

    clips = get_compiled_video_clips(UUID(compiled_id))
    for i, c in enumerate(clips):
        if c:
            click.echo(f"  {i+1}. {c.clip_name} ({float(c.end_time - c.start_time):.1f}s)")


@compile.command("delete")
@click.argument("compiled_id")
@click.option("--keep-s3", is_flag=True, help="Keep file in S3")
@click.confirmation_option(prompt="Are you sure you want to delete this compiled video?")
def compile_delete(compiled_id: str, keep_s3: bool):
    """Delete a compiled video."""
    from scripts.compile_video import delete_compiled_video

    if delete_compiled_video(UUID(compiled_id), delete_from_s3=not keep_s3):
        click.echo("Compiled video deleted.")
    else:
        click.echo("Failed to delete compiled video.", err=True)
        sys.exit(1)


@compile.command("download")
@click.argument("compiled_id")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def compile_download(compiled_id: str, output: Optional[str]):
    """Download a compiled video to local storage."""
    from scripts.compile_video import download_compiled_video

    output_path = Path(output) if output else None
    result = download_compiled_video(UUID(compiled_id), output_path)

    if result:
        click.echo(f"Downloaded to: {result}")
    else:
        click.echo("Failed to download video.", err=True)
        sys.exit(1)


# ============ Database Commands ============

@cli.group()
def db():
    """Database management commands."""
    pass


@db.command("init")
def db_init():
    """Initialize database tables (use SQL script for production)."""
    init_db()
    click.echo("Database tables created.")


@db.command("test")
def db_test():
    """Test database connection."""
    from scripts.db import get_engine

    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            click.echo("Database connection successful!")
    except Exception as e:
        click.echo(f"Database connection failed: {e}", err=True)
        sys.exit(1)


# ============ Storyline Commands ============

@cli.group()
def storylines():
    """AI-powered storyline generator and auto-editor."""
    pass


@storylines.command("generate")
@click.option("--refresh", is_flag=True, help="Force regeneration (ignore cache)")
def storylines_generate(refresh: bool):
    """Generate 5 storylines from all transcripts using AI."""
    from scripts.storylines import generate_storylines, format_storylines_display

    click.echo("Analyzing transcripts and generating storylines...")
    click.echo("(This may take 30-60 seconds)\n")

    try:
        storyline_list = generate_storylines(force_refresh=refresh)
        click.echo(format_storylines_display(storyline_list))
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Failed to generate storylines: {e}", err=True)
        sys.exit(1)


@storylines.command("preview")
@click.argument("storyline_id", type=int)
def storylines_preview(storyline_id: int):
    """Preview clips for a specific storyline."""
    from scripts.storylines import preview_storyline, format_storyline_preview, get_cached_storylines

    storylines_list = get_cached_storylines()
    if not storylines_list:
        click.echo("No storylines found. Run 'storylines generate' first.", err=True)
        sys.exit(1)

    storyline = preview_storyline(storyline_id)
    if not storyline:
        click.echo(f"Storyline {storyline_id} not found.", err=True)
        click.echo(f"Available: {[s.id for s in storylines_list]}")
        sys.exit(1)

    click.echo(format_storyline_preview(storyline))


@storylines.command("create")
@click.argument("storyline_id", type=int)
@click.option("--output", "-o", help="Output filename")
def storylines_create(storyline_id: int, output: Optional[str]):
    """Create the final video for a storyline."""
    from scripts.storylines import create_storyline_video, preview_storyline

    storyline = preview_storyline(storyline_id)
    if not storyline:
        click.echo(f"Storyline {storyline_id} not found. Run 'storylines generate' first.", err=True)
        sys.exit(1)

    click.echo(f"Creating video: {storyline.title}")
    click.echo(f"Clips: {len(storyline.clips)}")
    click.echo(f"Duration: ~{storyline.estimated_duration:.1f}s")
    click.echo("")

    result = create_storyline_video(storyline_id, output_name=output)

    if result:
        click.echo(f"\nVideo created successfully!")
        click.echo(f"Output: {result}")
        click.echo(f"Size: {result.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        click.echo("Failed to create video.", err=True)
        sys.exit(1)


@storylines.command("list")
def storylines_list():
    """List cached storylines without regenerating."""
    from scripts.storylines import get_cached_storylines, format_storylines_display

    storylines_list = get_cached_storylines()
    if not storylines_list:
        click.echo("No storylines cached. Run 'storylines generate' first.")
        return

    click.echo(format_storylines_display(storylines_list))


if __name__ == "__main__":
    cli()
