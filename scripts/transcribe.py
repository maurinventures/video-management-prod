"""Transcribe videos using AWS Transcribe or Whisper."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from .config_loader import get_config
from .db import DatabaseSession, ProcessingJob, Transcript, TranscriptSegment, Video

logger = logging.getLogger(__name__)


def get_transcribe_client():
    """Get configured AWS Transcribe client."""
    config = get_config()
    return boto3.client(
        "transcribe",
        region_name=config.aws_region,
        aws_access_key_id=config.aws_access_key,
        aws_secret_access_key=config.aws_secret_key,
    )


def get_s3_client():
    """Get configured S3 client."""
    config = get_config()
    return boto3.client(
        "s3",
        region_name=config.aws_region,
        aws_access_key_id=config.aws_access_key,
        aws_secret_access_key=config.aws_secret_key,
    )


def start_aws_transcription(video_id: UUID) -> Tuple[Optional[UUID], Optional[str]]:
    """
    Start AWS Transcribe job for a video.

    Returns:
        Tuple of (transcript_id, aws_job_name) or (None, None) on failure
    """
    config = get_config()

    with DatabaseSession() as session:
        video = session.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video not found: {video_id}")
            return None, None

        # Store values before session closes
        s3_uri = f"s3://{video.s3_bucket}/{video.s3_key}"
        video_format = video.format or "mp4"

        # Generate unique job name
        job_name = f"transcribe_{video_id}_{int(time.time())}"

        # Output location for transcript
        transcript_key = f"{config.s3_prefixes.get('transcripts', 'transcripts/')}{video_id}.json"

        # Create transcript record
        transcript = Transcript(
            video_id=video_id,
            s3_key=transcript_key,
            provider="aws",
            language=config.transcription_language,
            status="processing",
        )
        session.add(transcript)
        session.flush()
        transcript_id = transcript.id

        # Create processing job record
        job = ProcessingJob(
            job_type="transcribe",
            reference_id=transcript_id,
            reference_type="transcript",
            aws_job_id=job_name,
            status="running",
            started_at=datetime.utcnow(),
        )
        session.add(job)

        # Update video status
        video.status = "processing"

    # Start AWS Transcribe job
    transcribe_client = get_transcribe_client()
    try:
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": s3_uri},
            MediaFormat=video_format,
            LanguageCode=config.transcription_language,
            OutputBucketName=config.s3_bucket,
            OutputKey=transcript_key,
            Settings={
                "ShowSpeakerLabels": True,
                "MaxSpeakerLabels": 10,
            },
        )
        logger.info(f"Started transcription job: {job_name}")
        return transcript_id, job_name

    except ClientError as e:
        logger.error(f"Failed to start transcription: {e}")
        with DatabaseSession() as session:
            transcript = session.query(Transcript).filter(Transcript.id == transcript_id).first()
            if transcript:
                transcript.status = "error"
                transcript.error_message = str(e)
        return None, None


def check_transcription_status(job_name: str) -> dict:
    """Check the status of an AWS Transcribe job."""
    transcribe_client = get_transcribe_client()
    try:
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        job = response["TranscriptionJob"]
        return {
            "status": job["TranscriptionJobStatus"],
            "output_uri": job.get("Transcript", {}).get("TranscriptFileUri"),
            "failure_reason": job.get("FailureReason"),
        }
    except ClientError as e:
        logger.error(f"Failed to check job status: {e}")
        return {"status": "FAILED", "failure_reason": str(e)}


def wait_for_transcription(job_name: str, poll_interval: int = 30, max_wait: int = 3600) -> bool:
    """Wait for transcription job to complete."""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        status = check_transcription_status(job_name)
        if status["status"] == "COMPLETED":
            logger.info(f"Transcription completed: {job_name}")
            return True
        elif status["status"] == "FAILED":
            logger.error(f"Transcription failed: {status.get('failure_reason')}")
            return False
        logger.info(f"Transcription status: {status['status']}. Waiting...")
        time.sleep(poll_interval)
    logger.error(f"Transcription timed out after {max_wait} seconds")
    return False


def parse_aws_transcript(transcript_data: dict) -> Tuple[str, List[dict]]:
    """Parse AWS Transcribe output into text and segments."""
    results = transcript_data.get("results", {})

    # Get full transcript text
    transcripts = results.get("transcripts", [])
    full_text = " ".join(t.get("transcript", "") for t in transcripts)

    # Parse segments with timestamps
    segments = []
    items = results.get("items", [])

    current_segment = {"text": "", "start_time": None, "end_time": None, "confidence": []}

    for item in items:
        if item.get("type") == "punctuation":
            current_segment["text"] += item.get("alternatives", [{}])[0].get("content", "")
        else:
            start = float(item.get("start_time", 0))
            end = float(item.get("end_time", 0))
            content = item.get("alternatives", [{}])[0].get("content", "")
            confidence = float(item.get("alternatives", [{}])[0].get("confidence", 0))

            if current_segment["start_time"] is None:
                current_segment["start_time"] = start

            current_segment["end_time"] = end
            current_segment["text"] += (" " if current_segment["text"] else "") + content
            current_segment["confidence"].append(confidence)

            # Create segment every ~10 seconds or at sentence end
            if end - current_segment["start_time"] >= 10 or content.endswith((".", "!", "?")):
                if current_segment["text"].strip():
                    avg_conf = sum(current_segment["confidence"]) / len(current_segment["confidence"])
                    segments.append({
                        "start_time": current_segment["start_time"],
                        "end_time": current_segment["end_time"],
                        "text": current_segment["text"].strip(),
                        "confidence": avg_conf,
                    })
                current_segment = {"text": "", "start_time": None, "end_time": None, "confidence": []}

    # Don't forget last segment
    if current_segment["text"].strip():
        avg_conf = sum(current_segment["confidence"]) / len(current_segment["confidence"]) if current_segment["confidence"] else 0
        segments.append({
            "start_time": current_segment["start_time"],
            "end_time": current_segment["end_time"],
            "text": current_segment["text"].strip(),
            "confidence": avg_conf,
        })

    return full_text, segments


def process_completed_transcription(transcript_id: UUID, job_name: str) -> bool:
    """Process a completed AWS Transcribe job and store results."""
    config = get_config()
    s3_client = get_s3_client()

    with DatabaseSession() as session:
        transcript = session.query(Transcript).filter(Transcript.id == transcript_id).first()
        if not transcript:
            logger.error(f"Transcript not found: {transcript_id}")
            return False

        # Download transcript from S3
        try:
            response = s3_client.get_object(Bucket=config.s3_bucket, Key=transcript.s3_key)
            transcript_data = json.loads(response["Body"].read().decode("utf-8"))
        except ClientError as e:
            logger.error(f"Failed to download transcript: {e}")
            transcript.status = "error"
            transcript.error_message = str(e)
            return False

        # Parse transcript
        full_text, segments = parse_aws_transcript(transcript_data)

        # Update transcript record
        transcript.full_text = full_text
        transcript.word_count = len(full_text.split())
        transcript.status = "completed"

        # Add segments
        for i, seg in enumerate(segments):
            segment = TranscriptSegment(
                transcript_id=transcript_id,
                segment_index=i,
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                text=seg["text"],
                confidence=seg["confidence"],
            )
            session.add(segment)

        # Update video status
        video = transcript.video
        video.status = "transcribed"

        # Update processing job
        job = session.query(ProcessingJob).filter(ProcessingJob.aws_job_id == job_name).first()
        if job:
            job.status = "completed"
            job.completed_at = datetime.utcnow()

        logger.info(f"Processed transcript: {transcript_id} ({len(segments)} segments)")
        return True


def transcribe_with_whisper(video_id: UUID) -> Optional[UUID]:
    """Transcribe video using local Whisper model."""
    import whisper

    config = get_config()
    s3_client = get_s3_client()

    with DatabaseSession() as session:
        video = session.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video not found: {video_id}")
            return None

        # Download video to temp location
        temp_path = config.temp_dir / f"{video_id}.mp4"
        try:
            s3_client.download_file(video.s3_bucket, video.s3_key, str(temp_path))
        except ClientError as e:
            logger.error(f"Failed to download video: {e}")
            return None

        # Create transcript record
        transcript_key = f"{config.s3_prefixes.get('transcripts', 'transcripts/')}{video_id}_whisper.json"
        transcript = Transcript(
            video_id=video_id,
            s3_key=transcript_key,
            provider="whisper",
            language=config.transcription_language.split("-")[0],
            status="processing",
        )
        session.add(transcript)
        session.flush()
        transcript_id = transcript.id
        video.status = "processing"

    # Run Whisper
    try:
        logger.info("Loading Whisper model...")
        model = whisper.load_model("base")
        logger.info(f"Transcribing {temp_path}...")
        result = model.transcribe(str(temp_path))

        full_text = result["text"]
        segments = []
        for i, seg in enumerate(result["segments"]):
            segments.append({
                "start_time": seg["start"],
                "end_time": seg["end"],
                "text": seg["text"].strip(),
                "confidence": seg.get("no_speech_prob", 0),
            })

        # Save to database
        with DatabaseSession() as session:
            transcript = session.query(Transcript).filter(Transcript.id == transcript_id).first()
            transcript.full_text = full_text
            transcript.word_count = len(full_text.split())
            transcript.status = "completed"

            for i, seg in enumerate(segments):
                segment = TranscriptSegment(
                    transcript_id=transcript_id,
                    segment_index=i,
                    start_time=seg["start_time"],
                    end_time=seg["end_time"],
                    text=seg["text"],
                    confidence=1 - seg["confidence"],  # Invert no_speech_prob
                )
                session.add(segment)

            video = transcript.video
            video.status = "transcribed"

        # Upload transcript JSON to S3
        transcript_json = json.dumps(result, indent=2)
        s3_client.put_object(
            Bucket=config.s3_bucket,
            Key=transcript_key,
            Body=transcript_json.encode("utf-8"),
            ContentType="application/json",
        )

        logger.info(f"Whisper transcription completed: {transcript_id}")
        return transcript_id

    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        with DatabaseSession() as session:
            transcript = session.query(Transcript).filter(Transcript.id == transcript_id).first()
            if transcript:
                transcript.status = "error"
                transcript.error_message = str(e)
        return None

    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


def transcribe_video(video_id: UUID, provider: Optional[str] = None, wait: bool = True) -> Optional[UUID]:
    """
    Transcribe a video using configured provider.

    Args:
        video_id: ID of the video to transcribe
        provider: Override provider (aws or whisper)
        wait: Wait for completion (AWS only)

    Returns:
        transcript_id or None on failure
    """
    config = get_config()
    provider = provider or config.transcription_provider

    if provider == "whisper":
        return transcribe_with_whisper(video_id)
    else:
        transcript_id, job_name = start_aws_transcription(video_id)
        if not transcript_id:
            return None

        if wait:
            if wait_for_transcription(job_name):
                process_completed_transcription(transcript_id, job_name)
                return transcript_id
            return None
        return transcript_id


def get_transcript(transcript_id: UUID) -> Optional[Transcript]:
    """Get a transcript by ID."""
    with DatabaseSession() as session:
        return session.query(Transcript).filter(Transcript.id == transcript_id).first()


def get_transcript_for_video(video_id: UUID) -> Optional[Transcript]:
    """Get the transcript for a video."""
    with DatabaseSession() as session:
        return session.query(Transcript).filter(
            Transcript.video_id == video_id,
            Transcript.status == "completed"
        ).first()


def get_transcript_segments(transcript_id: UUID) -> List[TranscriptSegment]:
    """Get all segments for a transcript."""
    with DatabaseSession() as session:
        return session.query(TranscriptSegment).filter(
            TranscriptSegment.transcript_id == transcript_id
        ).order_by(TranscriptSegment.segment_index).all()


def search_transcript(video_id: UUID, query: str) -> List[dict]:
    """Search transcript segments for a query string."""
    with DatabaseSession() as session:
        transcript = session.query(Transcript).filter(
            Transcript.video_id == video_id,
            Transcript.status == "completed"
        ).first()

        if not transcript:
            return []

        segments = session.query(TranscriptSegment).filter(
            TranscriptSegment.transcript_id == transcript.id,
            TranscriptSegment.text.ilike(f"%{query}%")
        ).order_by(TranscriptSegment.start_time).all()

        return [
            {
                "index": s.segment_index,
                "start_time": float(s.start_time),
                "end_time": float(s.end_time),
                "text": s.text,
            }
            for s in segments
        ]
