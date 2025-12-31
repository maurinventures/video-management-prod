"""AI-powered storyline generator and auto-editor."""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID
import hashlib

from openai import OpenAI

from .config_loader import get_config
from .db import DatabaseSession, Transcript, TranscriptSegment, Video, Clip, CompiledVideo, CompiledVideoClip

logger = logging.getLogger(__name__)

# Cache file for generated storylines
STORYLINES_CACHE = Path("local_transcripts/storylines_cache.json")


@dataclass
class ClipSpec:
    """Specification for a single clip in a storyline."""
    video_id: str
    video_title: str
    start_time: float
    end_time: float
    text: str
    duration: float = field(init=False)

    def __post_init__(self):
        self.duration = self.end_time - self.start_time

    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "video_title": self.video_title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClipSpec":
        return cls(
            video_id=data["video_id"],
            video_title=data["video_title"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            text=data["text"],
        )


@dataclass
class Storyline:
    """A generated storyline with clips."""
    id: int
    title: str
    hook: str
    why_compelling: str
    estimated_duration: float
    clips: List[ClipSpec]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "hook": self.hook,
            "why_compelling": self.why_compelling,
            "estimated_duration": self.estimated_duration,
            "clips": [c.to_dict() for c in self.clips],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Storyline":
        return cls(
            id=data["id"],
            title=data["title"],
            hook=data["hook"],
            why_compelling=data["why_compelling"],
            estimated_duration=data["estimated_duration"],
            clips=[ClipSpec.from_dict(c) for c in data["clips"]],
        )


def get_openai_client() -> OpenAI:
    """Get configured OpenAI client."""
    config = get_config()
    api_key = config.secrets.get("openai", {}).get("api_key")
    if not api_key:
        raise ValueError("OpenAI API key not found in secrets.yaml")
    return OpenAI(api_key=api_key)


def get_all_transcripts() -> List[Dict[str, Any]]:
    """Fetch all completed transcripts with their segments."""
    transcripts_data = []

    with DatabaseSession() as session:
        transcripts = session.query(Transcript).filter(
            Transcript.status == "completed"
        ).all()

        for transcript in transcripts:
            video = session.query(Video).filter(Video.id == transcript.video_id).first()
            segments = session.query(TranscriptSegment).filter(
                TranscriptSegment.transcript_id == transcript.id
            ).order_by(TranscriptSegment.start_time).all()

            transcript_data = {
                "video_id": str(video.id),
                "video_title": video.filename,
                "duration": float(video.duration_seconds) if video.duration_seconds else 0,
                "segments": [
                    {
                        "start": float(seg.start_time),
                        "end": float(seg.end_time),
                        "text": seg.text,
                    }
                    for seg in segments
                ]
            }
            transcripts_data.append(transcript_data)

    return transcripts_data


def generate_storylines_prompt(transcripts: List[Dict]) -> str:
    """Build the prompt for the LLM."""

    # Format transcripts for the prompt
    transcript_text = ""
    for t in transcripts:
        transcript_text += f"\n\n=== VIDEO: {t['video_title']} (ID: {t['video_id']}) ===\n"
        transcript_text += f"Total duration: {t['duration']:.1f} seconds\n\n"
        for seg in t['segments']:
            transcript_text += f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}\n"

    prompt = f"""You are a professional video editor creating compelling short-form content. Analyze the following video transcripts and create 5 different 60-second storylines that could be created by stitching clips together.

TRANSCRIPTS:
{transcript_text}

REQUIREMENTS:
1. Each storyline should be approximately 60 seconds total (between 45-75 seconds)
2. Use clips from ANY of the available videos - mix and match for the best narrative
3. Each clip should be a complete thought/sentence (don't cut mid-sentence)
4. Focus on: compelling quotes, interesting insights, emotional moments, surprising statements
5. Create DIVERSE storylines - different themes, different tones, different focuses

For each storyline, provide:
1. A catchy title
2. A one-sentence hook/theme
3. Why it's compelling (one sentence)
4. The exact clips to use with precise timestamps

CRITICAL: You must use the EXACT timestamps from the transcripts. Each clip must reference a real segment from the source material.

Respond in this exact JSON format:
{{
  "storylines": [
    {{
      "id": 1,
      "title": "The Title",
      "hook": "One sentence describing the theme",
      "why_compelling": "One sentence on why this works",
      "estimated_duration": 58.5,
      "clips": [
        {{
          "video_id": "uuid-here",
          "video_title": "Video Name",
          "start_time": 10.0,
          "end_time": 25.0,
          "text": "The exact text from that segment"
        }}
      ]
    }}
  ]
}}

Generate 5 diverse, compelling storylines now:"""

    return prompt


def generate_storylines(force_refresh: bool = False) -> List[Storyline]:
    """Generate storylines from all transcripts using LLM."""

    # Check cache first
    if not force_refresh and STORYLINES_CACHE.exists():
        try:
            with open(STORYLINES_CACHE, 'r') as f:
                cache_data = json.load(f)
                return [Storyline.from_dict(s) for s in cache_data["storylines"]]
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")

    # Fetch all transcripts
    transcripts = get_all_transcripts()
    if not transcripts:
        raise ValueError("No transcripts found. Please transcribe some videos first.")

    logger.info(f"Analyzing {len(transcripts)} transcripts...")

    # Generate prompt and call LLM
    prompt = generate_storylines_prompt(transcripts)

    client = get_openai_client()

    logger.info("Generating storylines with AI...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert video editor who creates compelling short-form content. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=4000,
    )

    # Parse response
    response_text = response.choices[0].message.content

    # Extract JSON from response (handle markdown code blocks)
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        logger.error(f"Response was: {response_text[:500]}")
        raise ValueError("Failed to parse storyline response from AI")

    storylines = [Storyline.from_dict(s) for s in data["storylines"]]

    # Cache results
    STORYLINES_CACHE.parent.mkdir(exist_ok=True)
    with open(STORYLINES_CACHE, 'w') as f:
        json.dump({"storylines": [s.to_dict() for s in storylines]}, f, indent=2)

    logger.info(f"Generated {len(storylines)} storylines")
    return storylines


def get_cached_storylines() -> Optional[List[Storyline]]:
    """Get storylines from cache without regenerating."""
    if not STORYLINES_CACHE.exists():
        return None
    try:
        with open(STORYLINES_CACHE, 'r') as f:
            cache_data = json.load(f)
            return [Storyline.from_dict(s) for s in cache_data["storylines"]]
    except Exception:
        return None


def preview_storyline(storyline_id: int) -> Optional[Storyline]:
    """Get a specific storyline by ID."""
    storylines = get_cached_storylines()
    if not storylines:
        return None

    for s in storylines:
        if s.id == storyline_id:
            return s
    return None


def extract_clip_with_audio_normalization(
    input_path: Path,
    output_path: Path,
    start_time: float,
    end_time: float,
) -> bool:
    """Extract a clip with normalized audio using ffmpeg."""
    duration = end_time - start_time

    # Two-pass loudnorm for consistent audio levels
    # First pass: analyze
    analyze_cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", str(input_path),
        "-t", str(duration),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-"
    ]

    try:
        result = subprocess.run(analyze_cmd, capture_output=True, text=True)
        # Parse loudnorm stats from stderr (ffmpeg outputs to stderr)
        # For simplicity, we'll use single-pass with target levels
    except subprocess.CalledProcessError:
        pass

    # Single pass with target normalization (simpler and usually good enough)
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", str(input_path),
        "-t", str(duration),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-avoid_negative_ts", "make_zero",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract clip: {e.stderr}")
        return False


def concatenate_clips_normalized(clip_paths: List[Path], output_path: Path) -> bool:
    """Concatenate clips that have already been normalized."""
    if not clip_paths:
        return False

    # Create concat file
    concat_file = output_path.parent / f"{output_path.stem}_concat.txt"
    with open(concat_file, 'w') as f:
        for path in clip_paths:
            escaped = str(path).replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        concat_file.unlink()
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to concatenate clips: {e.stderr}")
        if concat_file.exists():
            concat_file.unlink()
        return False


def get_local_video_path(video_id: str) -> Optional[Path]:
    """Get the local path for a video (check common locations)."""
    # Check local_videos directory
    local_dir = Path("local_videos")
    if local_dir.exists():
        for f in local_dir.glob("*.mp4"):
            if video_id in f.name:
                return f

    # Check the original source locations
    source_dirs = [
        Path("/Users/josephs./Desktop/video/base"),
        Path("/Users/josephs./Downloads"),
    ]

    with DatabaseSession() as session:
        video = session.query(Video).filter(Video.id == UUID(video_id)).first()
        if video:
            original_name = video.original_filename
            for source_dir in source_dirs:
                potential_path = source_dir / original_name
                if potential_path.exists():
                    return potential_path

    return None


def create_storyline_video(
    storyline_id: int,
    output_name: Optional[str] = None,
) -> Optional[Path]:
    """Create the final video for a storyline."""
    config = get_config()

    storyline = preview_storyline(storyline_id)
    if not storyline:
        logger.error(f"Storyline {storyline_id} not found")
        return None

    logger.info(f"Creating video for: {storyline.title}")

    # Create temp directory for clips
    temp_dir = config.temp_dir / f"storyline_{storyline_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    extracted_clips = []

    try:
        for i, clip_spec in enumerate(storyline.clips):
            logger.info(f"Processing clip {i+1}/{len(storyline.clips)}: {clip_spec.text[:50]}...")

            # Find source video
            source_path = get_local_video_path(clip_spec.video_id)
            if not source_path:
                logger.error(f"Could not find source video: {clip_spec.video_id}")
                return None

            # Extract clip with normalized audio
            clip_path = temp_dir / f"clip_{i:03d}.mp4"
            if not extract_clip_with_audio_normalization(
                source_path,
                clip_path,
                clip_spec.start_time,
                clip_spec.end_time,
            ):
                logger.error(f"Failed to extract clip {i+1}")
                return None

            extracted_clips.append(clip_path)

        # Concatenate all clips
        safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in storyline.title)
        output_name = output_name or f"{safe_title}.mp4"
        output_path = Path("local_clips") / output_name
        output_path.parent.mkdir(exist_ok=True)

        logger.info("Stitching clips together...")
        if not concatenate_clips_normalized(extracted_clips, output_path):
            logger.error("Failed to concatenate clips")
            return None

        logger.info(f"Video created: {output_path}")

        # Record in database
        with DatabaseSession() as session:
            compiled = CompiledVideo(
                title=storyline.title,
                description=f"{storyline.hook}\n\n{storyline.why_compelling}",
                s3_key=None,  # Not uploaded to S3 yet
                total_duration_seconds=storyline.estimated_duration,
                file_size_bytes=output_path.stat().st_size,
                status="completed",
                created_by="storyline_generator",
            )
            session.add(compiled)
            session.flush()
            compiled_id = compiled.id

        logger.info(f"Recorded as compiled video: {compiled_id}")
        return output_path

    finally:
        # Clean up temp files
        for clip_path in extracted_clips:
            if clip_path.exists():
                clip_path.unlink()
        if temp_dir.exists():
            try:
                temp_dir.rmdir()
            except OSError:
                pass


def format_storylines_display(storylines: List[Storyline]) -> str:
    """Format storylines for CLI display."""
    output = []
    output.append("=" * 70)
    output.append("GENERATED STORYLINES")
    output.append("=" * 70)

    for s in storylines:
        output.append(f"\n[{s.id}] {s.title}")
        output.append(f"    Hook: {s.hook}")
        output.append(f"    Why: {s.why_compelling}")
        output.append(f"    Duration: {s.estimated_duration:.1f}s ({len(s.clips)} clips)")

    output.append("\n" + "=" * 70)
    output.append("Use 'storylines preview <id>' to see clip details")
    output.append("Use 'storylines create <id>' to generate the video")
    output.append("=" * 70)

    return "\n".join(output)


def format_storyline_preview(storyline: Storyline) -> str:
    """Format a single storyline with clip details."""
    output = []
    output.append("=" * 70)
    output.append(f"STORYLINE {storyline.id}: {storyline.title}")
    output.append("=" * 70)
    output.append(f"Hook: {storyline.hook}")
    output.append(f"Why compelling: {storyline.why_compelling}")
    output.append(f"Total duration: {storyline.estimated_duration:.1f}s")
    output.append("")
    output.append("CLIPS:")
    output.append("-" * 70)

    for i, clip in enumerate(storyline.clips, 1):
        output.append(f"\n[Clip {i}] {clip.video_title}")
        output.append(f"  Time: {clip.start_time:.1f}s - {clip.end_time:.1f}s ({clip.duration:.1f}s)")
        output.append(f"  Text: \"{clip.text}\"")

    output.append("\n" + "-" * 70)
    output.append(f"Total: {len(storyline.clips)} clips, {storyline.estimated_duration:.1f}s")
    output.append("")
    output.append("Use 'storylines create " + str(storyline.id) + "' to generate this video")

    return "\n".join(output)
