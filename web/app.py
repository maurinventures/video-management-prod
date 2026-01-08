"""Flask web application for video management dashboard."""

import os
import sys
import json
import re
import secrets
import uuid
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for, session
from flask_cors import CORS

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
from sqlalchemy import or_, text
from scripts.db import DatabaseSession, Video, Transcript, TranscriptSegment, CompiledVideo, ScriptFeedback, Conversation, ChatMessage, User, AILog, Persona, Document, SocialPost, AudioRecording, AudioSegment, Project, ExternalContent, ExternalContentSegment
from web.services.external_content_service import ExternalContentService
from web.services.auth_service import AuthService
from web.services.transcript_service import TranscriptService
from web.services.video_service import VideoService
from web.services.ai_service import AIService
import time
import hashlib
import pyotp
import qrcode
import io
import base64
from scripts.config_loader import get_config


def get_s3_client():
    """Get configured S3 client."""
    config = get_config()
    return boto3.client(
        "s3",
        aws_access_key_id=config.secrets.get("aws", {}).get("access_key_id"),
        aws_secret_access_key=config.secrets.get("aws", {}).get("secret_access_key"),
        region_name=config.settings.get("aws", {}).get("region", "us-east-1"),
    )


def get_ses_client():
    """Get configured SES client."""
    config = get_config()
    return boto3.client(
        "ses",
        aws_access_key_id=config.secrets.get("aws", {}).get("access_key_id"),
        aws_secret_access_key=config.secrets.get("aws", {}).get("secret_access_key"),
        region_name="us-east-1",
    )


def send_verification_email(to_email: str, name: str, verification_token: str) -> bool:
    """Send email verification link via AWS SES."""
    try:
        ses = get_ses_client()
        verification_url = f"https://maurinventuresinternal.com/verify-email?token={verification_token}"

        html_body = f"""
        <html>
        <body style="font-family: 'Inter', Arial, sans-serif; background-color: #f5f4ef; padding: 40px;">
            <div style="max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="display: inline-block; width: 50px; height: 50px; background: #d97757; border-radius: 10px; line-height: 50px; color: white; font-size: 24px; font-weight: bold;">M</div>
                </div>
                <h1 style="color: #1a1a1a; font-size: 24px; margin-bottom: 20px; text-align: center;">Verify Your Email</h1>
                <p style="color: #444; font-size: 16px; line-height: 1.6;">Hi {name},</p>
                <p style="color: #444; font-size: 16px; line-height: 1.6;">Welcome to MV Internal! Please verify your email address by clicking the button below:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" style="display: inline-block; background: #d97757; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">Verify Email</a>
                </div>
                <p style="color: #666; font-size: 14px; line-height: 1.6;">This link expires in 24 hours.</p>
                <p style="color: #666; font-size: 14px; line-height: 1.6;">If you didn't create an account, you can safely ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #e5e4df; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">MV Internal - Maurin Ventures</p>
            </div>
        </body>
        </html>
        """

        text_body = f"""
Hi {name},

Welcome to MV Internal! Please verify your email address by clicking this link:

{verification_url}

This link expires in 24 hours.

If you didn't create an account, you can safely ignore this email.

- MV Internal Team
        """

        ses.send_email(
            Source="MV Internal <noreply@maurinventuresinternal.com>",
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": "Verify your email - MV Internal", "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
        return True
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False


def send_invite_email(to_email: str, name: str, password: str) -> bool:
    """Send account invite email with credentials via AWS SES."""
    try:
        ses = get_ses_client()
        login_url = "https://maurinventuresinternal.com/login"

        html_body = f"""
        <html>
        <body style="font-family: 'Inter', Arial, sans-serif; background-color: #f5f4ef; padding: 40px;">
            <div style="max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="display: inline-block; width: 50px; height: 50px; background: #d97757; border-radius: 10px; line-height: 50px; color: white; font-size: 24px; font-weight: bold;">M</div>
                </div>
                <h1 style="color: #1a1a1a; font-size: 24px; margin-bottom: 20px; text-align: center;">Welcome to MV Internal</h1>
                <p style="color: #444; font-size: 16px; line-height: 1.6;">Hi {name},</p>
                <p style="color: #444; font-size: 16px; line-height: 1.6;">You've been invited to join MV Internal. Here are your login credentials:</p>
                <div style="background: #f5f4ef; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="color: #444; font-size: 14px; margin: 0 0 10px 0;"><strong>Email:</strong> {to_email}</p>
                    <p style="color: #444; font-size: 14px; margin: 0;"><strong>Password:</strong> {password}</p>
                </div>
                <p style="color: #d97757; font-size: 14px; line-height: 1.6; font-weight: 600;">⚠️ Two-Factor Authentication Required</p>
                <p style="color: #444; font-size: 14px; line-height: 1.6;">For security, you'll be required to set up 2FA (two-factor authentication) when you first log in. Have your authenticator app ready (Google Authenticator, Authy, etc.).</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{login_url}" style="display: inline-block; background: #d97757; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">Log In Now</a>
                </div>
                <p style="color: #666; font-size: 14px; line-height: 1.6;">Please change your password after your first login.</p>
                <hr style="border: none; border-top: 1px solid #e5e4df; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">MV Internal - Maurin Ventures</p>
            </div>
        </body>
        </html>
        """

        text_body = f"""
Hi {name},

You've been invited to join MV Internal. Here are your login credentials:

Email: {to_email}
Password: {password}

⚠️ Two-Factor Authentication Required
For security, you'll be required to set up 2FA when you first log in. Have your authenticator app ready.

Log in at: {login_url}

Please change your password after your first login.

- MV Internal Team
        """

        ses.send_email(
            Source="MV Internal <noreply@maurinventuresinternal.com>",
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": "You're invited to MV Internal", "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
        return True
    except Exception as e:
        print(f"Failed to send invite email: {e}")
        return False


# Flask web application initialization
app = Flask(__name__)

# CORS configuration for React frontend
CORS(app,
     origins=['http://localhost:3000'],
     supports_credentials=True,
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'])

# Session configuration - persistent sessions that survive browser close
# Secret key is fixed so sessions persist across server restarts
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'mv-internal-secret-key-2026-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP for development
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 604800  # 7 days in seconds


def format_duration(seconds):
    """Format seconds as MM:SS or HH:MM:SS."""
    if seconds is None:
        return "--:--"
    seconds = int(seconds)
    if seconds >= 3600:
        return f"{seconds // 3600}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
    return f"{seconds // 60}:{seconds % 60:02d}"


def format_timestamp(dt):
    """Format datetime for display."""
    if dt is None:
        return "--"
    return dt.strftime("%b %d, %Y %H:%M")


# DISABLED: Jinja filters for web interface
app.jinja_env.filters['duration'] = format_duration
app.jinja_env.filters['timestamp'] = format_timestamp


# DISABLED: Authentication middleware for web routes
# PUBLIC_ROUTES = {'login', 'register', 'logout', 'verify_2fa', 'verify_email', 'setup_2fa_after_verify', 'static'}

# @app.before_request
# def require_login():
#     """Require authentication for all routes except public ones."""
#     # Allow public routes
#     if request.endpoint in PUBLIC_ROUTES:
#         return None
#
#     # Allow static files
#     if request.path.startswith('/static/'):
#         return None
#
#     # Check if user is logged in
#     if 'user_id' not in session:
#         # For API requests, return JSON error
#         if request.path.startswith('/api/'):
#             return jsonify({'error': 'Authentication required'}), 401
#         # For page requests, redirect to login
#         return redirect(url_for('login'))
#
#     return None


# DISABLED: Web routes (CLI-only mode)
@app.route('/')
def index():
    """Redirect to chat (requires login)."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('chat'))


# @app.route('/videos')
def videos():
    """List all videos."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = UUID(session['user_id'])
    search_query = request.args.get('q', '').strip()

    with DatabaseSession() as db_session:
        query = db_session.query(Video)

        if search_query:
            search_filter = f'%{search_query}%'
            query = query.filter(
                (Video.speaker.ilike(search_filter)) |
                (Video.event_name.ilike(search_filter)) |
                (Video.filename.ilike(search_filter)) |
                (Video.description.ilike(search_filter))
            )

        videos = query.order_by(Video.created_at.desc()).all()
        video_list = []
        for v in videos:
            transcript = db_session.query(Transcript).filter(
                Transcript.video_id == v.id,
                Transcript.status == "completed"
            ).first()
            video_list.append({
                'id': str(v.id),
                'filename': v.filename,
                'duration': v.duration_seconds,
                'status': v.status,
                'created_at': v.created_at,
                'has_transcript': transcript is not None,
                'transcript_id': str(transcript.id) if transcript else None,
                's3_key': v.s3_key,
                'speaker': getattr(v, 'speaker', None),
                'event_name': getattr(v, 'event_name', None),
                'event_date': getattr(v, 'event_date', None),
                'description': getattr(v, 'description', None),
                'extra_data': getattr(v, 'extra_data', None) or {},
            })

    return render_with_sidebar('videos_new.html', 'videos', videos=video_list, search_query=search_query)


# @app.route('/audio')
def audio():
    """List all audio recordings."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = UUID(session['user_id'])
    search_query = request.args.get('q', '').strip()

    with DatabaseSession() as db_session:
        query = db_session.query(AudioRecording)

        if search_query:
            search_filter = f'%{search_query}%'
            query = query.filter(
                (AudioRecording.title.ilike(search_filter)) |
                (AudioRecording.filename.ilike(search_filter)) |
                (AudioRecording.source.ilike(search_filter))
            )

        recordings = query.order_by(AudioRecording.created_at.desc()).all()
        audio_list = []
        for a in recordings:
            # Count segments for this recording
            segment_count = db_session.query(AudioSegment).filter(
                AudioSegment.audio_id == a.id
            ).count()
            audio_list.append({
                'id': str(a.id),
                'filename': a.filename,
                'title': a.title,
                'duration': float(a.duration_seconds) if a.duration_seconds else None,
                'recording_date': a.recording_date,
                'source': a.source,
                'created_at': a.created_at,
                'segment_count': segment_count,
                's3_key': a.s3_key,
            })

    return render_with_sidebar('audio_new.html', 'audio', recordings=audio_list, search_query=search_query)


# @app.route('/api/audio')
def api_audio_list():
    """API endpoint to list all audio recordings."""
    with DatabaseSession() as session:
        recordings = session.query(AudioRecording).order_by(AudioRecording.created_at.desc()).all()
        return jsonify({
            'recordings': [{
                'id': str(a.id),
                'filename': a.filename,
                'title': a.title,
                'duration': float(a.duration_seconds) if a.duration_seconds else None,
                'recording_date': a.recording_date.isoformat() if a.recording_date else None,
                'source': a.source,
                'created_at': a.created_at.isoformat() if a.created_at else None,
            } for a in recordings]
        })


# @app.route('/transcripts')
def transcripts():
    """List all transcripts."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = UUID(session['user_id'])

    with DatabaseSession() as db_session:
        transcript_list = []
        transcripts = db_session.query(Transcript).filter(
            Transcript.status == "completed"
        ).order_by(Transcript.created_at.desc()).all()

        for t in transcripts:
            video = db_session.query(Video).filter(Video.id == t.video_id).first()
            segment_count = db_session.query(TranscriptSegment).filter(
                TranscriptSegment.transcript_id == t.id
            ).count()
            transcript_list.append({
                'id': str(t.id),
                'video_id': str(t.video_id),
                'video_title': video.filename if video else "Unknown",
                'segment_count': segment_count,
                'created_at': t.created_at,
            })

    return render_with_sidebar('transcripts_new.html', 'transcripts', transcripts=transcript_list)


# @app.route('/transcripts/<transcript_id>')
def transcript_detail(transcript_id):
    """View a single transcript with all segments."""
    with DatabaseSession() as session:
        transcript = session.query(Transcript).filter(
            Transcript.id == transcript_id
        ).first()

        if not transcript:
            return "Transcript not found", 404

        video = session.query(Video).filter(Video.id == transcript.video_id).first()
        segments = session.query(TranscriptSegment).filter(
            TranscriptSegment.transcript_id == transcript.id
        ).order_by(TranscriptSegment.start_time).all()

        # Get known speakers from video metadata
        known_speaker = video.speaker if video else None

        segment_list = [{
            'id': str(s.id),
            'start': float(s.start_time),
            'end': float(s.end_time),
            'text': s.text,
            'speaker': s.speaker or None,
        } for s in segments]

        return render_with_sidebar('transcript_detail.html', 'transcripts',
                                  transcript_id=transcript_id,
                                  video_id=str(video.id) if video else None,
                                  video_title=video.filename if video else "Unknown",
                                  known_speaker=known_speaker,
                                  segments=segment_list,
                                  total_duration=float(video.duration_seconds) if video and video.duration_seconds else 0)


# @app.route('/transcripts/search')
def search_transcripts():
    """Search across all transcripts."""
    query = request.args.get('q', '').strip()
    results = []

    if query:
        with DatabaseSession() as session:
            segments = session.query(TranscriptSegment).filter(
                TranscriptSegment.text.ilike(f'%{query}%')
            ).limit(100).all()

            for seg in segments:
                transcript = session.query(Transcript).filter(
                    Transcript.id == seg.transcript_id
                ).first()
                if transcript:
                    video = session.query(Video).filter(
                        Video.id == transcript.video_id
                    ).first()
                    results.append({
                        'video_id': str(transcript.video_id),
                        'video_title': video.filename if video else "Unknown",
                        'transcript_id': str(transcript.id),
                        'start': float(seg.start_time),
                        'end': float(seg.end_time),
                        'text': seg.text,
                    })

    return render_template('search.html', query=query, results=results)


# ============================================================================
# CHAT INTERFACE FOR SCRIPT GENERATION
# ============================================================================








def search_audio_for_context(query: str, limit: int = 100):
    """Search audio recordings for relevant segments based on query keywords.

    Returns audio segments with S3 URLs for playback, similar to video transcript search.
    """
    stop_words = {'want', 'need', 'like', 'make', 'create', 'find', 'give', 'about', 'from', 'with', 'that', 'this', 'have', 'will', 'would', 'could', 'should', 'audio', 'clip', 'clips', 'second', 'minute', 'the', 'and', 'for', 'how', 'know', 'talking', 'talk', 'good', 'great', 'thing', 'things', 'way', 'just', 'really', 'very', 'also', 'can', 'get', 'got', 'say', 'said', 'think', 'going', 'look', 'see', 'time', 'year', 'years', 'people', 'work', 'working'}
    keywords = [w for w in re.findall(r'\b\w{3,}\b', query.lower()) if w not in stop_words]
    keywords = list(dict.fromkeys(keywords))

    results = []
    results_by_id = {}

    with DatabaseSession() as db_session:
        # Get audio recording metadata
        recordings = db_session.query(AudioRecording).filter(
            AudioRecording.status == 'transcribed'
        ).all()
        recording_map = {str(r.id): {
            'title': r.title,
            'filename': r.filename,
            's3_key': r.s3_key,
            's3_bucket': r.s3_bucket,
            'speakers': r.speakers or [],
            'recording_date': r.recording_date,
            'duration': float(r.duration_seconds) if r.duration_seconds else None
        } for r in recordings}

        # Search for matching segments
        for keyword in keywords[:10]:
            segments = db_session.query(AudioSegment).filter(
                AudioSegment.text.ilike(f'%{keyword}%')
            ).limit(50).all()

            for seg in segments:
                audio_id = str(seg.audio_id)
                if audio_id not in recording_map:
                    continue

                audio_info = recording_map[audio_id]
                recording_date = audio_info.get('recording_date')
                date_str = recording_date.strftime('%Y-%m-%d') if recording_date else 'Unknown date'

                seg_key = str(seg.id)
                if seg_key in results_by_id:
                    results_by_id[seg_key]['score'] += 1
                    results_by_id[seg_key]['matched_keywords'].add(keyword)
                else:
                    # Generate presigned URL for audio clip
                    s3_key = audio_info.get('s3_key')

                    results_by_id[seg_key] = {
                        'type': 'audio',
                        'audio_id': audio_id,
                        'audio_title': audio_info.get('title', 'Unknown'),
                        'filename': audio_info.get('filename'),
                        's3_key': s3_key,
                        's3_bucket': audio_info.get('s3_bucket', 'mv-brain'),
                        'speaker': seg.speaker or (audio_info.get('speakers', ['Unknown'])[0] if audio_info.get('speakers') else 'Unknown'),
                        'recording_date': date_str,
                        'start': float(seg.start_time),
                        'end': float(seg.end_time),
                        'text': seg.text,
                        'segment_id': seg_key,
                        'score': 1,
                        'matched_keywords': {keyword}
                    }

        # Sort by score
        results = sorted(results_by_id.values(), key=lambda x: -x['score'])

    # Deduplicate and limit
    seen = set()
    unique_results = []
    for r in results:
        key = (r['audio_id'], r['start'], r['end'])
        if key not in seen:
            seen.add(key)
            # Convert matched_keywords set to list for JSON serialization
            r['matched_keywords'] = list(r.get('matched_keywords', set()))
            unique_results.append(r)
            if len(unique_results) >= limit:
                break

    print(f"[DEBUG] Audio search: {len(unique_results)} results for keywords: {keywords[:5]}")
    return unique_results


def validate_clips_against_database(clips: list) -> list:
    """Validate that clips reference real videos AND that the text actually exists in transcripts."""
    validated = []

    with DatabaseSession() as db_session:
        # Pre-load all video IDs for fuzzy matching
        all_videos = db_session.query(Video).all()
        video_id_map = {str(v.id): v for v in all_videos}
        video_title_map = {v.filename.lower(): v for v in all_videos}

        for clip in clips:
            video_id = clip.get('video_id')
            video_title = clip.get('video_title', '')
            start_time = clip.get('start_time', 0)
            end_time = clip.get('end_time', 0)
            claimed_text = clip.get('text', '')

            video = None

            # 1. Try exact video ID match
            try:
                video = db_session.query(Video).filter(Video.id == UUID(video_id)).first()
            except:
                pass

            # 2. If not found, try fuzzy ID matching (1-2 character difference)
            if not video and video_id:
                for existing_id, existing_video in video_id_map.items():
                    # Compare IDs character by character
                    if len(existing_id) == len(video_id):
                        diff_count = sum(1 for a, b in zip(existing_id, video_id) if a != b)
                        if diff_count <= 2:  # Allow up to 2 character differences
                            video = existing_video
                            print(f"[FUZZY MATCH] ID {video_id} -> {existing_id} (diff: {diff_count})")
                            break

            # 3. If still not found, try matching by video title
            if not video and video_title:
                title_lower = video_title.lower()
                # Exact title match
                if title_lower in video_title_map:
                    video = video_title_map[title_lower]
                    print(f"[TITLE MATCH] Found video by exact title: {video_title}")
                else:
                    # Partial title match - find videos containing the title
                    for filename, v in video_title_map.items():
                        if title_lower in filename or filename in title_lower:
                            video = v
                            print(f"[TITLE MATCH] Found video by partial title: {video_title} -> {v.filename}")
                            break

            if not video:
                print(f"[VALIDATION] No video found for ID: {video_id}, title: {video_title}")
                continue

            # Find matching or nearby segments
            transcript = db_session.query(Transcript).filter(
                Transcript.video_id == video.id,
                Transcript.status == 'completed'
            ).first()

            if not transcript:
                continue

            # Search for the claimed text in the transcript
            # Extract key phrase to search for - use multiple words for better matching
            search_phrase = claimed_text[:100].strip().lower()
            # Remove common starting words and punctuation
            for prefix in ['"', "'", 'and ', 'but ', 'so ', 'the ', 'that ', 'we ', 'i ', 'you ']:
                if search_phrase.startswith(prefix):
                    search_phrase = search_phrase[len(prefix):]
            # Extract meaningful words (skip first word if it's short)
            words = search_phrase.split()
            if len(words) > 3:
                # Use 3-4 consecutive words for matching
                search_phrase = ' '.join(words[1:4]) if len(words[0]) < 4 else ' '.join(words[:3])
            else:
                search_phrase = ' '.join(words[:3])

            # Search for this text in transcript segments
            matching_segments = db_session.query(TranscriptSegment).filter(
                TranscriptSegment.transcript_id == transcript.id,
                TranscriptSegment.text.ilike(f'%{search_phrase}%')
            ).order_by(TranscriptSegment.start_time).all()

            if matching_segments:
                # Found matching text - use the actual segment data
                seg = matching_segments[0]

                # Get surrounding segments for MORE complete context (30 seconds)
                nearby = db_session.query(TranscriptSegment).filter(
                    TranscriptSegment.transcript_id == transcript.id,
                    TranscriptSegment.start_time >= float(seg.start_time) - 15,
                    TranscriptSegment.end_time <= float(seg.end_time) + 15
                ).order_by(TranscriptSegment.start_time).all()

                actual_text = ' '.join(s.text for s in nearby)
                actual_start = float(nearby[0].start_time)
                actual_end = float(nearby[-1].end_time)
                event_date = video.event_date.strftime('%Y-%m-%d') if video.event_date else 'Unknown'

                validated.append({
                    'video_id': str(video.id),
                    'video_title': video.filename,
                    'speaker': video.speaker or 'Unknown',
                    'event_name': video.event_name or 'Unknown',
                    'event_date': event_date,
                    'start_time': actual_start,
                    'end_time': actual_end,
                    'duration': actual_end - actual_start,
                    'text': actual_text,
                    'verified': True,
                    'original_text': claimed_text
                })
            # If text not found, skip this clip entirely (it's hallucinated)

    return validated


def clean_clip_text(text: str) -> str:
    """Clean clip text - minimal processing to preserve original content."""
    text = text.strip()

    if not text:
        return "..."

    # Just trim to reasonable length if too long
    if len(text) > 500:
        # Find a good stopping point
        text = text[:500]
        last_period = text.rfind('.')
        if last_period > 200:
            text = text[:last_period + 1]

    return text






# ============================================================================
# COPY GENERATION (LinkedIn posts, tweets, etc.)
# ============================================================================





def generate_general_response(user_message: str, conversation_history: list, model: str = "claude-sonnet", user_id: str = None, conversation_id: str = None):
    """Generate a general conversational response without video/script focus."""

    # Check for demo mode (when API keys aren't configured)
    config = get_config()
    openai_key = config.openai_api_key
    anthropic_key = config.anthropic_api_key
    is_demo_mode = (not openai_key or len(openai_key) < 10) and (not anthropic_key or len(anthropic_key) < 10)

    if is_demo_mode:
        # Return demo response when API keys aren't configured
        return {
            'message': f'🤖 **Demo Response from {model.upper()}**\n\nHello! I received your message: "{user_message}"\n\nThis is a demonstration of the chat interface with model selection. To connect to real AI APIs, please configure your API keys in `config/credentials.yaml`:\n\n```yaml\nopenai:\n  api_key: YOUR_OPENAI_API_KEY\n\nanthropic:\n  api_key: YOUR_ANTHROPIC_API_KEY\n```\n\n✅ Model routing works correctly\n✅ All 6 models supported (Claude Sonnet/Opus/Haiku + GPT-4o/4-turbo/3.5-turbo)\n✅ Frontend integration complete',
            'model': model
        }

    system_prompt = """You are Claude, a helpful AI assistant created by Anthropic.

You're here to help with a wide variety of tasks - answering questions, having conversations, analyzing information, helping with research, writing, coding, and more.

You should be friendly, clear, and direct. Focus on being genuinely helpful.

The user has access to a video management system with transcripts, but you should only discuss that if they specifically ask about it. Otherwise, be a general-purpose assistant."""

    # Build messages from conversation history
    messages = []
    for msg in conversation_history[-10:]:  # Keep last 10 messages for context
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })

    # Add current message
    messages.append({"role": "user", "content": user_message})

    # Model mapping for API calls
    model_mapping = {
        'claude-sonnet': 'claude-sonnet-4-20250514',
        'claude-opus': 'claude-opus-4-20241120',
        'claude-haiku': 'claude-haiku-3-5-20241120',
        'gpt-4o': 'gpt-4o',
        'gpt-4-turbo': 'gpt-4-turbo',
        'gpt-3.5-turbo': 'gpt-3.5-turbo'
    }

    api_model = model_mapping.get(model, 'claude-sonnet-4-20250514')
    is_claude = model.startswith('claude')

    try:
        start_time = time.time()

        if is_claude:
            # Use Anthropic API for Claude models
            client = AIService.get_anthropic_client()

            response = client.messages.create(
                model=api_model,
                max_tokens=2000,
                system=system_prompt,
                messages=messages
            )

            response_text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

        else:
            # Use OpenAI API for GPT models
            client = AIService.get_openai_client()

            # Convert system prompt to OpenAI format
            openai_messages = [{"role": "system", "content": system_prompt}] + messages

            response = client.chat.completions.create(
                model=api_model,
                max_tokens=2000,
                messages=openai_messages,
                temperature=0.7
            )

            response_text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

        latency_ms = int((time.time() - start_time) * 1000)

        # Log to database
        if user_id and conversation_id:
            with DatabaseSession() as db_session:
                ai_log = AILog(
                    mode="chat",
                    model=api_model,
                    prompt=user_message[:5000],
                    response=response_text[:10000],
                    success=True,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    user_id=UUID(user_id) if user_id else None,
                    conversation_id=UUID(conversation_id) if conversation_id else None
                )
                db_session.add(ai_log)
                db_session.commit()

        return {
            'message': response_text,
            'model': model  # Return the frontend model name
        }

    except Exception as e:
        print(f"Error in general chat: {str(e)}")
        return {
            'message': f"I encountered an error: {str(e)}",
            'model': model
        }


def generate_copy_with_ai(
    user_message: str,
    persona_name: str,
    platform: str,
    transcript_context: list,
    conversation_history: list,
    model: str = "claude-sonnet",
    user_id: str = None,
    conversation_id: str = None
) -> dict:
    """Generate copy in a persona's voice using their content as reference."""

    start_time = time.time()

    # Load persona and extract all needed data within session
    with DatabaseSession() as db_session:
        persona = db_session.query(Persona).filter(
            Persona.name == persona_name,
            Persona.is_active == 1
        ).first()

        if not persona:
            return {
                "message": f"Persona '{persona_name}' not found.",
                "copy": None,
                "is_copy": True
            }

        # Extract all needed data while session is open
        p_name = persona.name
        p_description = persona.description or 'Not specified'
        p_tone = persona.tone or 'Not specified'
        p_style_notes = persona.style_notes or 'Not specified'
        p_topics = ', '.join(persona.topics) if persona.topics else 'Not specified'
        p_vocabulary = ', '.join(persona.vocabulary) if persona.vocabulary else 'Not specified'
        persona_id = persona.id

        # Load sample social posts if available
        sample_posts = db_session.query(SocialPost).filter(
            SocialPost.persona_id == persona_id
        ).order_by(SocialPost.posted_at.desc()).limit(5).all()

        samples_text = ""
        if sample_posts:
            samples_text = "\n\nEXAMPLE POSTS FROM THIS PERSONA (match this style):\n"
            for post in sample_posts:
                samples_text += f"\n[{post.platform}]: {post.content[:500]}\n"

    # Build persona voice profile (outside session, using extracted data)
    voice_profile = f"""PERSONA: {p_name}

DESCRIPTION: {p_description}

TONE: {p_tone}

STYLE NOTES: {p_style_notes}

KEY TOPICS: {p_topics}

VOCABULARY/PHRASES: {p_vocabulary}
"""

    # Build transcript context for reference material
    context_text = ""
    for t in transcript_context[:50]:  # Limit context
        text = t["text"].strip()
        if len(text) > 30:
            context_text += f'"{text}"\n\n'

    # Platform-specific instructions
    platform_instructions = {
        'linkedin': """LinkedIn Post Guidelines:
- Professional but personable tone
- Can be 1-3 paragraphs or use bullet points
- Often starts with a hook or personal insight
- May include a call to action or question
- Appropriate hashtags (2-5)""",
        'x': """X/Twitter Post Guidelines:
- Must be under 280 characters
- Punchy and memorable
- Can use thread format for longer thoughts (indicate with 1/, 2/, etc.)
- Hashtags sparingly (1-2)""",
        'email': """Email Guidelines:
- Clear subject line
- Professional greeting
- Concise body with clear purpose
- Appropriate closing""",
        'blog': """Blog Post Guidelines:
- Engaging headline
- Introduction that hooks the reader
- Clear structure with subheadings
- Conclusion with takeaway"""
    }

    platform_guide = platform_instructions.get(platform, "Write in a professional, engaging tone.")

    system_prompt = f"""You are a ghostwriter creating content in the voice of {p_name}.

{voice_profile}
{samples_text}

{platform_guide}

REFERENCE MATERIAL (use these as source material/inspiration):
{context_text[:15000]}

IMPORTANT:
1. Write EXACTLY as {p_name} would write - use first person ("I", "my", "we")
2. Match their tone, vocabulary, and style precisely
3. Draw on the reference material for facts and insights, but rephrase in their voice
4. Make it authentic - this should sound like {p_name} actually wrote it
5. Do NOT use generic corporate speak - be specific and personal
"""

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history
    for msg in conversation_history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    try:
        # Use Claude for copy generation (better at voice matching)
        client = AIService.get_anthropic_client()
        model_id = AIService.MODEL_MAP.get(model, "claude-sonnet-4-20250514")

        response = client.messages.create(
            model=model_id,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        copy_text = response.content[0].text
        latency_ms = (time.time() - start_time) * 1000

        # Log the AI call
        AIService.log_ai_call(
            request_type="copy_generation",
            model=model_id,
            prompt=user_message,
            context_summary=f"Persona: {persona_name}, Platform: {platform}",
            response=copy_text,
            success=True,
            latency_ms=latency_ms,
            user_id=user_id,
            conversation_id=conversation_id
        )

        return {
            "message": copy_text,
            "copy": copy_text,
            "is_copy": True,
            "persona": persona_name,
            "platform": platform,
            "clips": []  # No video clips for copy
        }

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        AIService.log_ai_call(
            request_type="copy_generation",
            model=model,
            prompt=user_message,
            context_summary=f"Persona: {persona_name}, Platform: {platform}",
            success=False,
            error_message=str(e),
            latency_ms=latency_ms,
            user_id=user_id,
            conversation_id=conversation_id
        )
        return {
            "message": f"Error generating copy: {str(e)}",
            "copy": None,
            "is_copy": True,
            "error": True
        }


def get_sidebar_data(user_id):
    """Get projects and conversations for sidebar rendering."""
    from datetime import datetime, timezone

    def format_date(dt):
        """Format datetime as relative time."""
        if not dt:
            return ''
        now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
        diff = now - dt
        seconds = diff.total_seconds()
        if seconds < 60:
            return 'Just now'
        if seconds < 3600:
            return f'{int(seconds // 60)}m ago'
        if seconds < 86400:
            return f'{int(seconds // 3600)}h ago'
        if seconds < 604800:
            return f'{int(seconds // 86400)}d ago'
        return dt.strftime('%b %d')

    with DatabaseSession() as db_session:
        # Fetch projects
        projects = db_session.query(Project).filter(
            Project.user_id == user_id,
            Project.is_archived == 0
        ).order_by(Project.created_at.desc()).all()

        sidebar_projects = [{
            'id': str(p.id),
            'name': p.name,
            'color': p.color or '#d97757',
            'conversation_count': len([c for c in p.conversations if len(c.messages) > 0])
        } for p in projects]

        # Fetch conversations (non-empty ones for sidebar)
        conversations = db_session.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.starred.desc(), Conversation.updated_at.desc()).all()

        # Group conversations by project
        project_groups = {}
        ungrouped = []

        for c in conversations:
            if len(c.messages) == 0:
                continue  # Skip empty conversations

            conv_data = {
                'id': str(c.id),
                'title': c.title,
                'updated_at': format_date(c.updated_at),
                'message_count': len(c.messages),
                'starred': c.starred if hasattr(c, 'starred') else False
            }

            if c.project:
                project_id = str(c.project.id)
                if project_id not in project_groups:
                    project_groups[project_id] = {
                        'project': {
                            'id': project_id,
                            'name': c.project.name,
                            'color': c.project.color or '#d97757'
                        },
                        'conversations': []
                    }
                project_groups[project_id]['conversations'].append(conv_data)
            else:
                ungrouped.append(conv_data)

        # Sort conversations within each project group (starred first, then by date)
        for group in project_groups.values():
            group['conversations'].sort(key=lambda x: (not x['starred'], x['id']), reverse=False)

        # Sort ungrouped conversations (starred first, then by date) - should already be sorted from query
        ungrouped.sort(key=lambda x: (not x['starred'], x['id']), reverse=False)

        return sidebar_projects, list(project_groups.values()), ungrouped


def get_sidebar_context(user_id):
    """Get standardized sidebar data for template rendering."""
    sidebar_projects, conv_groups, conv_ungrouped = get_sidebar_data(user_id)

    # Get current user info
    with DatabaseSession() as db_session:
        user = db_session.query(User).filter(User.id == user_id).first()
        user_data = {
            'name': user.name if user else 'User',
            'email': user.email if user else '',
            'is_admin': user.email in ['joy@maurinventures.com'] if user else False
        } if user else {'name': 'User', 'email': '', 'is_admin': False}

    return {
        'recent_projects': conv_groups,
        'standalone_chats': conv_ungrouped,
        'user': user_data
    }


def render_with_sidebar(template, active_page, **kwargs):
    """Render any template with consistent sidebar data included."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = UUID(session['user_id'])
    context = get_sidebar_context(user_id)
    context['active_page'] = active_page
    context.update(kwargs)

    return render_template(template, **context)


# @app.route('/test-shared')
def test_shared():
    """Test route for new shared template structure."""
    return render_with_sidebar('test_shared.html', active_page='test')


@app.route('/chat')
def chat():
    """New chat - shows welcome screen for starting a new conversation."""
    # Support ?project=<id> to create new chat in a specific project
    project_id = request.args.get('project')
    return render_with_sidebar('chat_new.html', 'new_chat', view='new', project_id=project_id)


@app.route('/chat/recents')
def chat_recents():
    """Chat list - shows all recent conversations."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = UUID(session['user_id'])

    # Fetch all conversations for main content area
    with DatabaseSession() as db_session:
        conversations = db_session.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.starred.desc(), Conversation.updated_at.desc()).all()

        conversations_data = [{
            'id': str(c.id),
            'title': c.title,
            'updated_at': c.updated_at.isoformat(),
            'message_count': len(c.messages),
            'starred': c.starred if hasattr(c, 'starred') else False
        } for c in conversations]

    return render_with_sidebar('chat_new.html', 'chats', view='recents', conversations=conversations_data)


# @app.route('/chat/<conversation_id>')
def chat_conversation(conversation_id):
    """Specific conversation view."""
    return render_with_sidebar('chat_new.html', 'new_chat', view='conversation', conversation_id=conversation_id)


# @app.route('/new')
def new_chat():
    """Legacy /new route - redirect to /chat."""
    return redirect(url_for('chat'))


# @app.route('/projects')
def projects_page():
    """Projects list page."""
    return render_with_sidebar('projects_new.html', 'projects')


# @app.route('/project/<project_id>')
def project_detail(project_id):
    """Project detail page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = UUID(session['user_id'])

    # Verify project exists and belongs to user
    with DatabaseSession() as db_session:
        project = db_session.query(Project).filter(
            Project.id == UUID(project_id),
            Project.user_id == user_id
        ).first()

        if not project:
            return redirect(url_for('projects_page'))

    return render_with_sidebar('project.html', 'projects', project_id=project_id)


# @app.route('/ai-logs')
def ai_logs():
    """View AI call logs for quality monitoring."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_with_sidebar('ai_logs.html', 'ai_logs')


# @app.route('/api/ai-logs', methods=['GET'])
def api_ai_logs():
    """API endpoint to fetch AI logs with filtering."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    # Get query parameters
    request_type = request.args.get('request_type')
    model = request.args.get('model')
    success = request.args.get('success')
    limit = min(int(request.args.get('limit', 50)), 200)
    offset = int(request.args.get('offset', 0))

    with DatabaseSession() as db_session:
        query = db_session.query(AILog).order_by(AILog.created_at.desc())

        # Apply filters
        if request_type:
            query = query.filter(AILog.request_type == request_type)
        if model:
            query = query.filter(AILog.model.ilike(f'%{model}%'))
        if success is not None and success != '':
            query = query.filter(AILog.success == int(success))

        # Get total count for pagination
        total = query.count()

        # Apply pagination
        logs = query.offset(offset).limit(limit).all()

        return jsonify({
            'logs': [{
                'id': str(log.id),
                'request_type': log.request_type,
                'model': log.model,
                'prompt': log.prompt[:500] + '...' if log.prompt and len(log.prompt) > 500 else log.prompt,
                'context_summary': log.context_summary,
                'response': log.response[:1000] + '...' if log.response and len(log.response) > 1000 else log.response,
                'clips_generated': log.clips_generated,
                'success': log.success == 1,
                'error_message': log.error_message,
                'latency_ms': round(log.latency_ms) if log.latency_ms else None,
                'input_tokens': log.input_tokens,
                'output_tokens': log.output_tokens,
                'user_id': str(log.user_id) if log.user_id else None,
                'conversation_id': str(log.conversation_id) if log.conversation_id else None,
                'created_at': log.created_at.isoformat() if log.created_at else None
            } for log in logs],
            'total': total,
            'limit': limit,
            'offset': offset
        })


# @app.route('/api/ai-logs/<log_id>', methods=['GET'])
def api_ai_log_detail(log_id):
    """Get full details of a specific AI log entry."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    with DatabaseSession() as db_session:
        log = db_session.query(AILog).filter(AILog.id == UUID(log_id)).first()

        if not log:
            return jsonify({'error': 'Log not found'}), 404

        return jsonify({
            'id': str(log.id),
            'request_type': log.request_type,
            'model': log.model,
            'prompt': log.prompt,
            'context_summary': log.context_summary,
            'response': log.response,
            'clips_generated': log.clips_generated,
            'response_json': log.response_json,
            'success': log.success == 1,
            'error_message': log.error_message,
            'latency_ms': round(log.latency_ms) if log.latency_ms else None,
            'input_tokens': log.input_tokens,
            'output_tokens': log.output_tokens,
            'user_id': str(log.user_id) if log.user_id else None,
            'conversation_id': str(log.conversation_id) if log.conversation_id else None,
            'created_at': log.created_at.isoformat() if log.created_at else None
        })


# ============================================================================
# PERSONAS MANAGEMENT
# ============================================================================

# @app.route('/personas')
def personas():
    """List all personas (voice profiles)."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = UUID(session['user_id'])

    with DatabaseSession() as db_session:
        persona_list = db_session.query(Persona).filter(Persona.is_active == 1).order_by(Persona.name).all()

        # Get counts for each persona
        personas_data = []
        for p in persona_list:
            doc_count = db_session.query(Document).filter(Document.persona_id == p.id).count()
            post_count = db_session.query(SocialPost).filter(SocialPost.persona_id == p.id).count()
            video_count = db_session.query(Video).filter(Video.speaker == p.speaker_name_in_videos).count() if p.speaker_name_in_videos else 0

            personas_data.append({
                'id': str(p.id),
                'name': p.name,
                'description': p.description,
                'tone': p.tone,
                'avatar_url': p.avatar_url,
                'document_count': doc_count,
                'social_post_count': post_count,
                'video_count': video_count,
                'created_at': p.created_at
            })

    return render_with_sidebar('personas_new.html', 'personas', personas=personas_data)


# @app.route('/personas/<persona_id>')
def persona_detail(persona_id):
    """View and edit a single persona."""
    with DatabaseSession() as db_session:
        persona = db_session.query(Persona).filter(Persona.id == UUID(persona_id)).first()
        if not persona:
            return "Persona not found", 404

        # Get related content
        documents = db_session.query(Document).filter(Document.persona_id == persona.id).order_by(Document.created_at.desc()).limit(20).all()
        social_posts = db_session.query(SocialPost).filter(SocialPost.persona_id == persona.id).order_by(SocialPost.posted_at.desc()).limit(20).all()
        videos = db_session.query(Video).filter(Video.speaker == persona.speaker_name_in_videos).order_by(Video.created_at.desc()).limit(20).all() if persona.speaker_name_in_videos else []

        return render_with_sidebar('persona_detail.html', 'personas',
                                  persona=persona,
                                  documents=documents,
                                  social_posts=social_posts,
                                  videos=videos)


# @app.route('/api/personas', methods=['GET'])
def api_list_personas():
    """API: List all personas."""
    with DatabaseSession() as db_session:
        personas = db_session.query(Persona).filter(Persona.is_active == 1).order_by(Persona.name).all()
        return jsonify([{
            'id': str(p.id),
            'name': p.name,
            'description': p.description,
            'tone': p.tone,
            'speaker_name_in_videos': p.speaker_name_in_videos
        } for p in personas])


# @app.route('/api/personas', methods=['POST'])
def api_create_persona():
    """API: Create a new persona."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json or {}
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    with DatabaseSession() as db_session:
        # Check if name already exists
        existing = db_session.query(Persona).filter(Persona.name == name).first()
        if existing:
            return jsonify({'error': 'A persona with this name already exists'}), 400

        persona = Persona(
            name=name,
            description=data.get('description', ''),
            tone=data.get('tone', ''),
            style_notes=data.get('style_notes', ''),
            topics=data.get('topics', []),
            vocabulary=data.get('vocabulary', []),
            speaker_name_in_videos=data.get('speaker_name_in_videos', ''),
            avatar_url=data.get('avatar_url', ''),
            created_by=UUID(session['user_id'])
        )
        db_session.add(persona)
        db_session.commit()

        return jsonify({
            'success': True,
            'id': str(persona.id),
            'name': persona.name
        })


# @app.route('/api/personas/<persona_id>', methods=['PUT'])
def api_update_persona(persona_id):
    """API: Update a persona."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json or {}

    with DatabaseSession() as db_session:
        persona = db_session.query(Persona).filter(Persona.id == UUID(persona_id)).first()
        if not persona:
            return jsonify({'error': 'Persona not found'}), 404

        # Update fields
        if 'name' in data:
            persona.name = data['name']
        if 'description' in data:
            persona.description = data['description']
        if 'tone' in data:
            persona.tone = data['tone']
        if 'style_notes' in data:
            persona.style_notes = data['style_notes']
        if 'topics' in data:
            persona.topics = data['topics']
        if 'vocabulary' in data:
            persona.vocabulary = data['vocabulary']
        if 'speaker_name_in_videos' in data:
            persona.speaker_name_in_videos = data['speaker_name_in_videos']
        if 'avatar_url' in data:
            persona.avatar_url = data['avatar_url']

        persona.updated_at = datetime.utcnow()
        db_session.commit()

        return jsonify({'success': True})


# @app.route('/api/personas/<persona_id>', methods=['DELETE'])
def api_delete_persona(persona_id):
    """API: Soft delete a persona."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    with DatabaseSession() as db_session:
        persona = db_session.query(Persona).filter(Persona.id == UUID(persona_id)).first()
        if not persona:
            return jsonify({'error': 'Persona not found'}), 404

        persona.is_active = 0
        persona.updated_at = datetime.utcnow()
        db_session.commit()

        return jsonify({'success': True})


# ============================================================
# PROJECTS API
# ============================================================

# @app.route('/api/projects', methods=['GET'])
def api_list_projects():
    """API: List all projects for current user."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = UUID(session['user_id'])
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'

    with DatabaseSession() as db_session:
        query = db_session.query(Project).filter(Project.user_id == user_id)
        if not include_archived:
            query = query.filter(Project.is_archived == 0)
        projects = query.order_by(Project.created_at.desc()).all()

        return jsonify({
            'projects': [{
                'id': str(p.id),
                'name': p.name,
                'description': p.description,
                'custom_instructions': p.custom_instructions,
                'color': p.color,
                'is_archived': p.is_archived,
                'conversation_count': len([c for c in p.conversations if len(c.messages) > 0]),
                'created_at': p.created_at.isoformat() if p.created_at else None,
                'updated_at': p.updated_at.isoformat() if p.updated_at else None
            } for p in projects]
        })


# @app.route('/api/projects', methods=['POST'])
def api_create_project():
    """API: Create a new project."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = UUID(session['user_id'])
    data = request.json or {}
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    with DatabaseSession() as db_session:
        project = Project(
            user_id=user_id,
            name=name,
            description=data.get('description', '').strip() or None,
            custom_instructions=data.get('custom_instructions', '').strip() or None,
            color=data.get('color', '#d97757')
        )
        db_session.add(project)
        db_session.commit()

        return jsonify({
            'id': str(project.id),
            'name': project.name,
            'description': project.description,
            'custom_instructions': project.custom_instructions,
            'color': project.color,
            'created_at': project.created_at.isoformat() if project.created_at else None
        }), 201


# @app.route('/api/projects/<project_id>', methods=['GET'])
def api_get_project(project_id):
    """API: Get project details with conversations."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = UUID(session['user_id'])

    with DatabaseSession() as db_session:
        project = db_session.query(Project).filter(
            Project.id == UUID(project_id),
            Project.user_id == user_id
        ).first()

        if not project:
            return jsonify({'error': 'Project not found'}), 404

        conversations = [{
            'id': str(c.id),
            'title': c.title,
            'message_count': len(c.messages),
            'created_at': c.created_at.isoformat() if c.created_at else None,
            'updated_at': c.updated_at.isoformat() if c.updated_at else None
        } for c in project.conversations]

        return jsonify({
            'id': str(project.id),
            'name': project.name,
            'description': project.description,
            'custom_instructions': project.custom_instructions,
            'color': project.color,
            'is_archived': project.is_archived,
            'conversations': conversations,
            'created_at': project.created_at.isoformat() if project.created_at else None,
            'updated_at': project.updated_at.isoformat() if project.updated_at else None
        })


# @app.route('/api/projects/<project_id>', methods=['PUT'])
def api_update_project(project_id):
    """API: Update a project."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = UUID(session['user_id'])
    data = request.json or {}

    with DatabaseSession() as db_session:
        project = db_session.query(Project).filter(
            Project.id == UUID(project_id),
            Project.user_id == user_id
        ).first()

        if not project:
            return jsonify({'error': 'Project not found'}), 404

        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'error': 'Name cannot be empty'}), 400
            project.name = name

        if 'description' in data:
            project.description = data['description'].strip() or None

        if 'custom_instructions' in data:
            project.custom_instructions = data['custom_instructions'].strip() or None

        if 'color' in data:
            project.color = data['color']

        if 'is_archived' in data:
            project.is_archived = 1 if data['is_archived'] else 0

        project.updated_at = datetime.utcnow()
        db_session.commit()

        return jsonify({
            'id': str(project.id),
            'name': project.name,
            'description': project.description,
            'custom_instructions': project.custom_instructions,
            'color': project.color,
            'is_archived': project.is_archived,
            'updated_at': project.updated_at.isoformat() if project.updated_at else None
        })


# @app.route('/api/projects/<project_id>', methods=['DELETE'])
def api_delete_project(project_id):
    """API: Delete a project. Use ?permanent=true for permanent deletion."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = UUID(session['user_id'])
    permanent = request.args.get('permanent', 'false').lower() == 'true'

    with DatabaseSession() as db_session:
        project = db_session.query(Project).filter(
            Project.id == UUID(project_id),
            Project.user_id == user_id
        ).first()

        if not project:
            return jsonify({'error': 'Project not found'}), 404

        if permanent:
            # Permanent delete - conversations will have project_id set to NULL
            db_session.delete(project)
        else:
            # Soft delete (archive)
            project.is_archived = 1
            project.updated_at = datetime.utcnow()

        db_session.commit()
        return jsonify({'success': True})


# @app.route('/api/conversations/<conversation_id>/project', methods=['PUT'])
def api_set_conversation_project(conversation_id):
    """API: Assign a conversation to a project."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = UUID(session['user_id'])
    data = request.json or {}
    project_id = data.get('project_id')

    with DatabaseSession() as db_session:
        conversation = db_session.query(Conversation).filter(
            Conversation.id == UUID(conversation_id),
            Conversation.user_id == user_id
        ).first()

        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404

        if project_id:
            # Verify project exists and belongs to user
            project = db_session.query(Project).filter(
                Project.id == UUID(project_id),
                Project.user_id == user_id
            ).first()
            if not project:
                return jsonify({'error': 'Project not found'}), 404
            conversation.project_id = project.id
        else:
            # Remove from project
            conversation.project_id = None

        conversation.updated_at = datetime.utcnow()
        db_session.commit()

        return jsonify({'success': True, 'project_id': str(conversation.project_id) if conversation.project_id else None})


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if request.method == 'POST':
        data = request.form
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return render_template('login.html', error='Email and password required')

        with DatabaseSession() as db_session:
            user = db_session.query(User).filter(User.email == email).first()
            if not user:
                return render_template('login.html', error='Invalid email or password')

            # Check password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if user.password_hash != password_hash:
                return render_template('login.html', error='Invalid email or password')

            if not user.is_active:
                return render_template('login.html', error='Account is disabled')

            # Check if email is verified
            if not user.email_verified:
                return render_template('login.html', error='Please verify your email first. Check your inbox for the verification link.')

            # Check if 2FA is enabled - IT IS MANDATORY
            if user.totp_enabled == 1 and user.totp_secret:
                # Store pending auth in session
                session['pending_2fa_user_id'] = str(user.id)
                session['pending_2fa_email'] = user.email
                return redirect(url_for('verify_2fa'))

            # 2FA not set up - force setup (mandatory for all users)
            session['pending_2fa_setup_user_id'] = str(user.id)
            session['pending_2fa_setup_email'] = user.email
            session['pending_2fa_setup_name'] = user.name
            session.modified = True  # Explicitly mark session as modified
            return redirect(url_for('setup_2fa_after_verify'))

    return render_template('login.html')


# @app.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    """2FA verification page."""
    if 'pending_2fa_user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()

        with DatabaseSession() as db_session:
            user = db_session.query(User).filter(
                User.id == session['pending_2fa_user_id']
            ).first()

            if not user or not user.totp_secret:
                session.pop('pending_2fa_user_id', None)
                session.pop('pending_2fa_email', None)
                return redirect(url_for('login'))

            # Verify TOTP code
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(code, valid_window=1):  # Allow 1 window tolerance
                # 2FA verified - complete login
                user.last_login = datetime.utcnow()
                db_session.commit()

                # Set up persistent session (7 days)
                session.permanent = True
                session['user_id'] = str(user.id)
                session['user_name'] = user.name
                session['user_email'] = user.email
                session.pop('pending_2fa_user_id', None)
                session.pop('pending_2fa_email', None)

                return redirect(url_for('chat'))
            else:
                return render_template('verify_2fa.html',
                    email=session.get('pending_2fa_email'),
                    error='Invalid code. Please try again.')

    return render_template('verify_2fa.html', email=session.get('pending_2fa_email'))


# @app.route('/setup-2fa', methods=['GET', 'POST'])
def setup_2fa():
    """2FA setup page - requires login."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with DatabaseSession() as db_session:
        user = db_session.query(User).filter(User.id == session['user_id']).first()
        if not user:
            return redirect(url_for('login'))

        if request.method == 'POST':
            code = request.form.get('code', '').strip()
            secret = request.form.get('secret', '')

            # Verify the code before enabling
            totp = pyotp.TOTP(secret)
            if totp.verify(code, valid_window=1):
                user.totp_secret = secret
                user.totp_enabled = 1
                db_session.commit()
                return render_template('setup_2fa.html', success=True, user_name=user.name)
            else:
                # Regenerate QR for retry
                provisioning_uri = totp.provisioning_uri(
                    name=user.email,
                    issuer_name="MV Internal"
                )
                qr_data = generate_qr_base64(provisioning_uri)
                return render_template('setup_2fa.html',
                    secret=secret,
                    qr_code=qr_data,
                    user_name=user.name,
                    error='Invalid code. Please try again.')

        # Generate new secret
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="MV Internal"
        )

        # Generate QR code as base64
        qr_data = generate_qr_base64(provisioning_uri)

        return render_template('setup_2fa.html',
            secret=secret,
            qr_code=qr_data,
            user_name=user.name,
            already_enabled=user.totp_enabled == 1)


def generate_qr_base64(data):
    """Generate QR code as base64 data URI."""
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return 'data:image/png;base64,' + base64.b64encode(buffer.read()).decode()


# @app.route('/logout')
def logout():
    """User logout."""
    session.clear()
    return redirect(url_for('login'))


# @app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page with email verification."""
    if request.method == 'POST':
        data = request.form
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm = data.get('confirm', '')

        if not name or not email or not password:
            return render_template('register.html', error='All fields are required')

        if password != confirm:
            return render_template('register.html', error='Passwords do not match')

        if len(password) < 8:
            return render_template('register.html', error='Password must be at least 8 characters')

        with DatabaseSession() as db_session:
            # Check if email exists
            existing = db_session.query(User).filter(User.email == email).first()
            if existing:
                return render_template('register.html', error='Email already registered')

            # Generate verification token
            verification_token = secrets.token_urlsafe(32)
            token_expires = datetime.utcnow() + timedelta(hours=24)

            # Create user (unverified)
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            user = User(
                name=name,
                email=email,
                password_hash=password_hash,
                email_verified=0,
                verification_token=verification_token,
                verification_token_expires=token_expires
            )
            db_session.add(user)
            db_session.commit()

            # Send verification email
            if send_verification_email(email, name, verification_token):
                return render_template('register.html',
                    success=True,
                    message=f'Check your email ({email}) for a verification link.')
            else:
                return render_template('register.html',
                    success=True,
                    message=f'Account created. Check your email ({email}) for verification.')

    return render_template('register.html')


# @app.route('/verify-email')
def verify_email():
    """Email verification endpoint."""
    token = request.args.get('token', '')

    if not token:
        return render_template('login.html', error='Invalid verification link')

    with DatabaseSession() as db_session:
        user = db_session.query(User).filter(User.verification_token == token).first()

        if not user:
            return render_template('login.html', error='Invalid or expired verification link')

        # Check if token is expired
        if user.verification_token_expires and user.verification_token_expires < datetime.utcnow():
            return render_template('login.html', error='Verification link has expired. Please register again.')

        # Mark email as verified
        user.email_verified = 1
        user.verification_token = None
        user.verification_token_expires = None
        db_session.commit()

        # Store user ID in session for 2FA setup
        session['pending_2fa_setup_user_id'] = str(user.id)
        session['pending_2fa_setup_email'] = user.email
        session['pending_2fa_setup_name'] = user.name
        session.modified = True  # Explicitly mark session as modified

        # Redirect to 2FA setup (mandatory)
        return redirect(url_for('setup_2fa_after_verify'))


# @app.route('/setup-2fa-required', methods=['GET', 'POST'])
def setup_2fa_after_verify():
    """Mandatory 2FA setup after email verification."""
    if 'pending_2fa_setup_user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['pending_2fa_setup_user_id']
    user_email = session.get('pending_2fa_setup_email', '')
    user_name = session.get('pending_2fa_setup_name', '')

    with DatabaseSession() as db_session:
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            session.pop('pending_2fa_setup_user_id', None)
            return redirect(url_for('login'))

        if request.method == 'POST':
            code = request.form.get('code', '').strip()
            secret = request.form.get('secret', '')

            # Verify the code before enabling
            totp = pyotp.TOTP(secret)
            if totp.verify(code, valid_window=1):
                user.totp_secret = secret
                user.totp_enabled = 1
                db_session.commit()

                # Clear pending session
                session.pop('pending_2fa_setup_user_id', None)
                session.pop('pending_2fa_setup_email', None)
                session.pop('pending_2fa_setup_name', None)

                # Complete login
                session.permanent = True
                session['user_id'] = str(user.id)
                session['user_name'] = user.name
                session['user_email'] = user.email

                return redirect(url_for('chat'))
            else:
                # Regenerate QR for retry
                provisioning_uri = totp.provisioning_uri(
                    name=user.email,
                    issuer_name="MV Internal"
                )
                qr_data = generate_qr_base64(provisioning_uri)
                return render_template('setup_2fa.html',
                    secret=secret,
                    qr_code=qr_data,
                    user_name=user_name,
                    mandatory=True,
                    error='Invalid code. Please try again.')

        # Generate new secret
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="MV Internal"
        )

        # Generate QR code as base64
        qr_data = generate_qr_base64(provisioning_uri)

        return render_template('setup_2fa.html',
            secret=secret,
            qr_code=qr_data,
            user_name=user_name,
            mandatory=True,
            email_just_verified=True)


# ============================================================================
# CONVERSATION API ENDPOINTS
# ============================================================================

# @app.route('/api/conversations', methods=['GET'])
def api_list_conversations():
    """List all conversations for the current user."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    with DatabaseSession() as db_session:
        conversations = db_session.query(Conversation).filter(
            Conversation.user_id == UUID(session['user_id'])
        ).order_by(Conversation.updated_at.desc()).all()

        return jsonify({
            'conversations': [{
                'id': str(c.id),
                'title': c.title,
                'video_id': str(c.video_id) if c.video_id else None,
                'project_id': str(c.project_id) if c.project_id else None,
                'project': {
                    'id': str(c.project.id),
                    'name': c.project.name,
                    'color': c.project.color
                } if c.project else None,
                'preferred_model': c.preferred_model,
                'created_at': c.created_at.isoformat(),
                'updated_at': c.updated_at.isoformat(),
                'message_count': len(c.messages)
            } for c in conversations]
        })


# @app.route('/api/conversations', methods=['POST'])
def api_create_conversation():
    """Create a new conversation."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json or {}
    title = data.get('title', 'New Chat')
    video_id = data.get('video_id')
    project_id = data.get('project_id')
    preferred_model = data.get('preferred_model', 'gpt-4o')

    user_id = UUID(session['user_id'])

    with DatabaseSession() as db_session:
        # Verify project belongs to user if provided
        if project_id:
            project = db_session.query(Project).filter(
                Project.id == UUID(project_id),
                Project.user_id == user_id
            ).first()
            if not project:
                return jsonify({'error': 'Project not found'}), 404

        conversation = Conversation(
            user_id=user_id,
            title=title,
            video_id=UUID(video_id) if video_id else None,
            project_id=UUID(project_id) if project_id else None,
            preferred_model=preferred_model
        )
        db_session.add(conversation)
        db_session.commit()

        # Get project info if project_id was provided
        project_info = None
        if project_id and project:
            project_info = {
                'id': str(project.id),
                'name': project.name,
                'color': project.color
            }

        return jsonify({
            'id': str(conversation.id),
            'title': conversation.title,
            'project_id': str(conversation.project_id) if conversation.project_id else None,
            'project': project_info,
            'preferred_model': conversation.preferred_model,
            'created_at': conversation.created_at.isoformat()
        })


# @app.route('/api/conversations/<conversation_id>', methods=['GET'])
def api_get_conversation(conversation_id):
    """Get a conversation with all messages."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    with DatabaseSession() as db_session:
        conversation = db_session.query(Conversation).filter(
            Conversation.id == UUID(conversation_id),
            Conversation.user_id == UUID(session['user_id'])
        ).first()

        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404

        # Get project info if available
        project_info = None
        if conversation.project:
            project_info = {
                'id': str(conversation.project.id),
                'name': conversation.project.name,
                'color': conversation.project.color
            }

        return jsonify({
            'id': str(conversation.id),
            'title': conversation.title,
            'video_id': str(conversation.video_id) if conversation.video_id else None,
            'project_id': str(conversation.project_id) if conversation.project_id else None,
            'project': project_info,
            'preferred_model': conversation.preferred_model,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
            'messages': [{
                'id': str(m.id),
                'role': m.role,
                'content': m.content,
                'clips': m.clips_json or [],
                'model': m.model,
                'created_at': m.created_at.isoformat()
            } for m in conversation.messages]
        })


# @app.route('/api/conversations/<conversation_id>', methods=['PUT'])
def api_update_conversation(conversation_id):
    """Update conversation title."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json or {}

    with DatabaseSession() as db_session:
        conversation = db_session.query(Conversation).filter(
            Conversation.id == UUID(conversation_id),
            Conversation.user_id == UUID(session['user_id'])
        ).first()

        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404

        if 'title' in data:
            conversation.title = data['title']

        if 'preferred_model' in data:
            conversation.preferred_model = data['preferred_model']

        db_session.commit()

        return jsonify({'success': True})


# @app.route('/api/conversations/<conversation_id>/star', methods=['PUT'])
def api_star_conversation(conversation_id):
    """Star or unstar a conversation."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json or {}
    starred = data.get('starred', True)  # Default to starring if not specified

    with DatabaseSession() as db_session:
        conversation = db_session.query(Conversation).filter(
            Conversation.id == UUID(conversation_id),
            Conversation.user_id == UUID(session['user_id'])
        ).first()

        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404

        conversation.starred = starred
        db_session.commit()

        return jsonify({
            'success': True,
            'starred': starred,
            'message': 'Starred' if starred else 'Unstarred'
        })


# @app.route('/api/conversations/<conversation_id>/generate-title', methods=['POST'])
def api_generate_conversation_title(conversation_id):
    """Generate a title for a conversation using AI based on first message."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json or {}
    first_message = data.get('message', '')

    if not first_message:
        return jsonify({'error': 'No message provided'}), 400

    with DatabaseSession() as db_session:
        conversation = db_session.query(Conversation).filter(
            Conversation.id == UUID(conversation_id),
            Conversation.user_id == UUID(session['user_id'])
        ).first()

        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404

        # Generate title using Claude (fast, cheap)
        try:
            client = AIService.get_anthropic_client()
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=50,
                messages=[{
                    "role": "user",
                    "content": f"Generate a very short (2-5 words) title for a chat that starts with this message. Return ONLY the title, nothing else:\n\n{first_message[:500]}"
                }]
            )
            title = response.content[0].text.strip().strip('"\'')
            # Limit length
            if len(title) > 60:
                title = title[:57] + '...'
        except Exception as e:
            # Fallback to truncated message
            title = first_message[:50] + ('...' if len(first_message) > 50 else '')

        conversation.title = title
        db_session.commit()

        return jsonify({'success': True, 'title': title})


# @app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def api_delete_conversation(conversation_id):
    """Delete a conversation."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    with DatabaseSession() as db_session:
        conversation = db_session.query(Conversation).filter(
            Conversation.id == UUID(conversation_id),
            Conversation.user_id == UUID(session['user_id'])
        ).first()

        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404

        db_session.delete(conversation)
        db_session.commit()

        return jsonify({'success': True})


# ============================================================================
# COLLABORATION API ENDPOINTS
# ============================================================================

# @app.route('/api/users/search', methods=['GET'])
def api_search_users():
    """Search users by name or email for inviting to conversations."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'users': []})

    with DatabaseSession() as db_session:
        users = db_session.query(User).filter(
            User.is_active == 1,
            User.id != UUID(session['user_id']),
            (User.name.ilike(f'%{query}%') | User.email.ilike(f'%{query}%'))
        ).limit(10).all()

        return jsonify({
            'users': [{
                'id': str(u.id),
                'name': u.name,
                'email': u.email
            } for u in users]
        })


# @app.route('/api/conversations/<conversation_id>/participants', methods=['GET'])
def api_get_participants(conversation_id):
    """Get participants of a conversation."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    from scripts.db import ChatParticipant

    with DatabaseSession() as db_session:
        # Check access
        conversation = db_session.query(Conversation).filter(
            Conversation.id == UUID(conversation_id)
        ).first()

        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404

        # Owner always has access
        is_owner = str(conversation.user_id) == session['user_id']
        is_participant = db_session.query(ChatParticipant).filter(
            ChatParticipant.conversation_id == UUID(conversation_id),
            ChatParticipant.user_id == UUID(session['user_id'])
        ).first() is not None

        if not is_owner and not is_participant:
            return jsonify({'error': 'Access denied'}), 403

        # Get owner
        owner = db_session.query(User).filter(User.id == conversation.user_id).first()

        # Get participants
        participants = db_session.query(ChatParticipant).filter(
            ChatParticipant.conversation_id == UUID(conversation_id)
        ).all()

        result = [{
            'id': str(owner.id) if owner else None,
            'name': owner.name if owner else 'Unknown',
            'email': owner.email if owner else '',
            'role': 'owner'
        }]

        for p in participants:
            user = db_session.query(User).filter(User.id == p.user_id).first()
            if user:
                result.append({
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email,
                    'role': p.role,
                    'joined_at': p.joined_at.isoformat() if p.joined_at else None
                })

        return jsonify({'participants': result, 'is_collaborative': conversation.is_collaborative})


# @app.route('/api/conversations/<conversation_id>/invite', methods=['POST'])
def api_invite_participant(conversation_id):
    """Invite a user to collaborate on a conversation."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    from scripts.db import ChatParticipant

    data = request.json or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400

    with DatabaseSession() as db_session:
        # Check ownership
        conversation = db_session.query(Conversation).filter(
            Conversation.id == UUID(conversation_id),
            Conversation.user_id == UUID(session['user_id'])
        ).first()

        if not conversation:
            return jsonify({'error': 'Conversation not found or access denied'}), 404

        # Check user exists
        invitee = db_session.query(User).filter(User.id == UUID(user_id)).first()
        if not invitee:
            return jsonify({'error': 'User not found'}), 404

        # Check not already participant
        existing = db_session.query(ChatParticipant).filter(
            ChatParticipant.conversation_id == UUID(conversation_id),
            ChatParticipant.user_id == UUID(user_id)
        ).first()

        if existing:
            return jsonify({'error': 'User already a participant'}), 400

        # Add participant
        participant = ChatParticipant(
            conversation_id=UUID(conversation_id),
            user_id=UUID(user_id),
            role='member',
            invited_by=UUID(session['user_id'])
        )
        db_session.add(participant)

        # Mark conversation as collaborative
        conversation.is_collaborative = 1

        db_session.commit()

        return jsonify({
            'success': True,
            'participant': {
                'id': str(invitee.id),
                'name': invitee.name,
                'email': invitee.email,
                'role': 'member'
            }
        })


# @app.route('/api/conversations/<conversation_id>/leave', methods=['POST'])
def api_leave_conversation(conversation_id):
    """Leave a conversation (for participants, not owners)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    from scripts.db import ChatParticipant

    with DatabaseSession() as db_session:
        participant = db_session.query(ChatParticipant).filter(
            ChatParticipant.conversation_id == UUID(conversation_id),
            ChatParticipant.user_id == UUID(session['user_id'])
        ).first()

        if not participant:
            return jsonify({'error': 'Not a participant'}), 404

        db_session.delete(participant)
        db_session.commit()

        return jsonify({'success': True})


# @app.route('/api/conversations/<conversation_id>/attachments', methods=['POST'])
def api_upload_attachment(conversation_id):
    """Upload file attachment to a conversation."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = UUID(session['user_id'])

    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    with DatabaseSession() as db_session:
        # Verify conversation exists and user has access
        conversation = db_session.query(Conversation).filter(
            Conversation.id == UUID(conversation_id),
            Conversation.user_id == user_id
        ).first()

        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404

        try:
            # Generate unique filename and S3 key
            file_extension = os.path.splitext(file.filename)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            s3_key = f"attachments/{conversation_id}/{unique_filename}"

            # Detect MIME type
            mime_type = mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'

            # Get file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            # Upload to S3
            config = get_config()
            bucket = config.s3_bucket
            s3_client = get_s3_client()

            s3_client.upload_fileobj(
                file,
                bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': mime_type,
                    'Metadata': {
                        'original_filename': file.filename,
                        'uploaded_by': str(user_id),
                        'conversation_id': conversation_id
                    }
                }
            )

            # Generate presigned URL for preview (valid for 24 hours)
            preview_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': s3_key},
                ExpiresIn=86400  # 24 hours
            )

            # Create attachment metadata
            attachment_data = {
                'id': str(uuid.uuid4()),
                'filename': file.filename,
                's3_key': s3_key,
                'file_type': mime_type,
                'file_size': file_size,
                'preview_url': preview_url,
                'uploaded_at': datetime.utcnow().isoformat()
            }

            return jsonify({
                'success': True,
                'attachment': attachment_data
            })

        except Exception as e:
            return jsonify({'error': f'Upload failed: {str(e)}'}), 500


# @app.route('/api/clips/<conversation_id>/<int:clip_index>/comments', methods=['GET'])
def api_get_clip_comments(conversation_id, clip_index):
    """Get comments on a specific clip."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    from scripts.db import ClipComment

    with DatabaseSession() as db_session:
        comments = db_session.query(ClipComment).filter(
            ClipComment.conversation_id == UUID(conversation_id),
            ClipComment.clip_index == clip_index
        ).order_by(ClipComment.created_at).all()

        return jsonify({
            'comments': [{
                'id': str(c.id),
                'user_id': str(c.user_id),
                'user_name': db_session.query(User).filter(User.id == c.user_id).first().name if c.user_id else 'Unknown',
                'content': c.content,
                'mentions': c.mentions or [],
                'is_regenerate_request': c.is_regenerate_request,
                'created_at': c.created_at.isoformat()
            } for c in comments]
        })


# @app.route('/api/clips/<conversation_id>/<int:clip_index>/comments', methods=['POST'])
def api_add_clip_comment(conversation_id, clip_index):
    """Add a comment on a clip. Use @mv-video to request regeneration."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    from scripts.db import ClipComment

    data = request.json or {}
    content = data.get('content', '').strip()
    message_id = data.get('message_id')

    if not content:
        return jsonify({'error': 'Comment content required'}), 400

    # Parse mentions from content
    mentions = re.findall(r'@(\w+(?:-\w+)*)', content)
    is_regenerate = 'mv-video' in mentions or 'mv_video' in mentions

    with DatabaseSession() as db_session:
        comment = ClipComment(
            conversation_id=UUID(conversation_id),
            message_id=UUID(message_id) if message_id else None,
            user_id=UUID(session['user_id']),
            clip_index=clip_index,
            content=content,
            mentions=mentions,
            is_regenerate_request=1 if is_regenerate else 0
        )
        db_session.add(comment)
        db_session.commit()

        user = db_session.query(User).filter(User.id == UUID(session['user_id'])).first()

        return jsonify({
            'success': True,
            'comment': {
                'id': str(comment.id),
                'user_id': str(comment.user_id),
                'user_name': user.name if user else 'Unknown',
                'content': comment.content,
                'mentions': mentions,
                'is_regenerate_request': is_regenerate,
                'created_at': comment.created_at.isoformat()
            }
        })


# @app.route('/api/clips/<conversation_id>/<int:clip_index>/regenerate', methods=['POST'])
def api_regenerate_clip(conversation_id, clip_index):
    """Regenerate a specific clip based on feedback."""
    print(f"[DEBUG] Regenerate clip called: conversation={conversation_id}, clip_index={clip_index}")

    if 'user_id' not in session:
        print("[DEBUG] Regenerate failed: Not logged in")
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json or {}
    feedback = data.get('feedback', '').strip()
    original_clip = data.get('original_clip', {})
    conversation_history = data.get('history', [])
    model = data.get('model', 'claude-sonnet')

    print(f"[DEBUG] Regenerate params: feedback='{feedback}', original_clip={original_clip.get('text', '')[:50] if original_clip else 'MISSING'}, model={model}")

    if not original_clip:
        print("[DEBUG] Regenerate failed: No original clip data")
        return jsonify({'error': 'Original clip data required'}), 400

    # Build prompt for regeneration
    regenerate_prompt = f"""The user wants to find a DIFFERENT clip to replace this one.

ORIGINAL CLIP (to replace):
- Video: {original_clip.get('video_title', 'Unknown')}
- Time: {original_clip.get('start_time', 0):.1f}s - {original_clip.get('end_time', 0):.1f}s
- Text: "{original_clip.get('text', '')}"

USER FEEDBACK: {feedback if feedback else 'Find a better alternative'}

Find ONE alternative clip that:
1. Covers a similar topic/theme but with different content
2. Is from a DIFFERENT part of the video OR a different video entirely
3. Better matches what the user is looking for

Output format:
```json
{{"clips": [{{"video_id": "...", "video_title": "...", "start_time": 0.0, "end_time": 0.0, "text": "..."}}]}}
```"""

    # Search for relevant context
    search_query = feedback or original_clip.get('text', '')[:100]
    print(f"[DEBUG] Regenerate searching with query: '{search_query[:80]}...'")
    context = TranscriptService.search_for_context(search_query)

    if not context:
        print("[DEBUG] Regenerate failed: No context found from search")
        return jsonify({'error': 'No relevant content found'}), 404

    print(f"[DEBUG] Regenerate found {len(context)} context segments, generating with AI...")

    # Generate with AI
    result = AIService.generate_script_with_ai(
        regenerate_prompt, context, conversation_history, model=model,
        user_id=session.get('user_id'), conversation_id=conversation_id
    )

    print(f"[DEBUG] Regenerate AI result: clips={len(result.get('clips', []))}, message={result.get('message', '')[:100] if result.get('message') else 'none'}")

    if result.get('clips'):
        return jsonify({
            'success': True,
            'alternative_clips': result['clips'],
            'message': result.get('message', '')
        })
    else:
        print("[DEBUG] Regenerate failed: AI returned no clips")
        return jsonify({
            'success': False,
            'error': 'Could not find alternative clips',
            'message': result.get('message', '')
        })


# @app.route('/api/records/<conversation_id>/<int:record_index>/comments', methods=['POST'])
def api_add_record_comment(conversation_id, record_index):
    """Add a comment on a record/narration section. Use @mv-video to request regeneration."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    from scripts.db import ClipComment

    data = request.json or {}
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'error': 'Comment content required'}), 400

    # Parse mentions from content
    mentions = re.findall(r'@(\w+(?:-\w+)*)', content)
    is_regenerate = 'mv-video' in mentions or 'mv_video' in mentions

    with DatabaseSession() as db_session:
        # Reuse ClipComment table with negative index to indicate record sections
        comment = ClipComment(
            conversation_id=UUID(conversation_id),
            user_id=UUID(session['user_id']),
            clip_index=-1 - record_index,  # Use negative indices for records
            content=content,
            mentions=mentions,
            is_regenerate_request=1 if is_regenerate else 0
        )
        db_session.add(comment)
        db_session.commit()

        user = db_session.query(User).filter(User.id == UUID(session['user_id'])).first()

        return jsonify({
            'success': True,
            'comment': {
                'id': str(comment.id),
                'user_id': str(comment.user_id),
                'user_name': user.name if user else 'Unknown',
                'content': comment.content,
                'mentions': mentions,
                'is_regenerate_request': is_regenerate,
                'created_at': comment.created_at.isoformat()
            }
        })


# @app.route('/api/records/<conversation_id>/<int:record_index>/regenerate', methods=['POST'])
def api_regenerate_record(conversation_id, record_index):
    """Regenerate a narration/record section based on feedback."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json or {}
    feedback = data.get('feedback', '').strip()
    original_text = data.get('original_text', '').strip()
    conversation_history = data.get('history', [])
    model = data.get('model', 'claude-sonnet')

    if not original_text:
        return jsonify({'error': 'Original text required'}), 400

    # Build prompt for regeneration
    regenerate_prompt = f"""The user wants to regenerate this narration/voiceover text.

ORIGINAL NARRATION (to rewrite):
"{original_text}"

USER FEEDBACK: {feedback if feedback else 'Provide an alternative version'}

Write ONE alternative narration that:
1. Conveys a similar message but with different wording
2. Maintains a professional, engaging tone suitable for voiceover
3. Is approximately the same length as the original
4. Better matches what the user is looking for based on their feedback

Output ONLY the new narration text, nothing else. Do not include quotes or any other formatting."""

    # Generate with AI
    start_time = time.time()
    actual_model = "claude-sonnet-4-20250514"

    try:
        client = AIService.get_anthropic_client()

        response = client.messages.create(
            model=actual_model,
            max_tokens=500,
            messages=[
                {"role": "user", "content": regenerate_prompt}
            ]
        )

        new_text = response.content[0].text.strip()
        # Remove any quotes that might have been added
        new_text = new_text.strip('"\'')

        # Log successful AI call
        latency_ms = (time.time() - start_time) * 1000
        AIService.log_ai_call(
            request_type="regenerate_record",
            model=actual_model,
            prompt=regenerate_prompt,
            response=new_text,
            success=True,
            latency_ms=latency_ms,
            input_tokens=response.usage.input_tokens if hasattr(response, 'usage') else None,
            output_tokens=response.usage.output_tokens if hasattr(response, 'usage') else None,
            user_id=session.get('user_id'),
            conversation_id=conversation_id
        )

        return jsonify({
            'success': True,
            'new_text': new_text
        })
    except Exception as e:
        # Log failed AI call
        latency_ms = (time.time() - start_time) * 1000
        AIService.log_ai_call(
            request_type="regenerate_record",
            model=actual_model,
            prompt=regenerate_prompt,
            success=False,
            error_message=str(e),
            latency_ms=latency_ms,
            user_id=session.get('user_id'),
            conversation_id=conversation_id
        )

        print(f"Error regenerating record: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/chat/test', methods=['POST'])
def api_chat_test():
    """Simplified chat endpoint for testing AI integration without database dependencies."""
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        model = data.get('model', 'gpt-4o')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Call AI generation directly
        result = AIService.generate_general_response(
            user_message=user_message,
            conversation_history=[],
            model=model,
            user_id=None,
            conversation_id=None
        )

        return jsonify({
            'response': result['message'],
            'clips': [],
            'has_script': False,
            'context_segments': 0,
            'model': result['model'],
            'conversation_id': 'test-conversation'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Server error: {str(e)}',
            'response': f'Sorry, there was an error processing your request: {str(e)}',
            'clips': [],
            'has_script': False
        }), 500


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handle chat messages for script generation or copy generation."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = request.json
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])
        conversation_id = data.get('conversation_id')
        model = data.get('model')  # Model can be specified in request
        previous_clips = data.get('previous_clips', [])  # Clips from previous scripts to exclude

        # Prompt 18: RAG Integration - Configuration parameters
        use_rag = data.get('use_rag', True)  # Default to RAG enabled
        context_mode = data.get('context_mode', 'auto')  # 'rag', 'keyword', 'auto'
        rag_similarity_threshold = data.get('rag_similarity_threshold', 0.7)  # RAG similarity threshold

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400


        # Get preferred model from conversation if not specified
        if not model and conversation_id:
            # DEMO MODE: Skip database lookup for demo user
            if session.get('user_id') == 'demo-user-id':
                model = 'gpt-4o'  # Default for demo
            else:
                with DatabaseSession() as db_session:
                    conversation = db_session.query(Conversation).filter(
                        Conversation.id == UUID(conversation_id)
                    ).first()
                    if conversation:
                        model = conversation.preferred_model

        # Fall back to default if still no model
        if not model:
            model = 'gpt-4o'

        # Detect user intent
        copy_intent = AIService.detect_copy_intent(user_message)
        script_intent = AIService.detect_script_intent(user_message)

        # COPY GENERATION MODE
        if copy_intent['is_copy'] and copy_intent['persona_name']:
            # Search for relevant context for copy generation (with RAG integration)
            context = TranscriptService.search_for_context(
                user_message,
                use_rag=(use_rag and context_mode != 'keyword')
            )
            audio_context = search_audio_for_context(user_message, limit=50)
            # Use Claude for copy generation (better at voice matching)
            copy_model = 'claude-sonnet' if not model.startswith('claude') else model

            result = AIService.generate_copy_with_ai(
                user_message=user_message,
                persona_name=copy_intent['persona_name'],
                platform=copy_intent['platform'] or 'general',
                transcript_context=context or [],
                conversation_history=conversation_history,
                model=copy_model,
                user_id=session.get('user_id'),
                conversation_id=conversation_id,
                use_rag=(use_rag and context_mode != 'keyword')  # Prompt 18: RAG Integration
            )

            # Save messages to conversation
            if conversation_id and 'user_id' in session:
                with DatabaseSession() as db_session:
                    user_msg = ChatMessage(
                        conversation_id=UUID(conversation_id),
                        role='user',
                        content=user_message
                    )
                    db_session.add(user_msg)

                    assistant_msg = ChatMessage(
                        conversation_id=UUID(conversation_id),
                        role='assistant',
                        content=result['message'],
                        model=copy_model
                    )
                    db_session.add(assistant_msg)

                    conv = db_session.query(Conversation).filter(Conversation.id == UUID(conversation_id)).first()
                    if conv:
                        conv.updated_at = datetime.utcnow()
                    db_session.commit()

            # Detect search method used for copy generation (Prompt 18: RAG Integration)
            copy_search_method = 'unknown'
            if context:
                # Check if any context items have the RAG search method indicator
                rag_results = [c for c in context if c.get('search_method') == 'rag']
                copy_search_method = 'rag' if rag_results else 'keyword'
            else:
                copy_search_method = 'none'

            return jsonify({
                'response': result['message'],
                'clips': [],
                'has_script': False,
                'is_copy': True,
                'persona': copy_intent['persona_name'],
                'platform': copy_intent['platform'],
                'context_segments': len(context) if context else 0,
                'model': copy_model,
                'conversation_id': conversation_id,
                # RAG Integration Metrics (Prompt 18)
                'search_method': copy_search_method,
                'rag_enabled': use_rag,
                'context_mode': context_mode,
                'rag_config': {
                    'similarity_threshold': rag_similarity_threshold,
                    'chunks_used': len([c for c in context if c.get('search_method') == 'rag']) if context else 0
                }
            })

        # VIDEO SCRIPT MODE
        if script_intent:
            # Search for relevant transcript context (with RAG integration)
            context = TranscriptService.search_for_context(
                user_message,
                use_rag=(use_rag and context_mode != 'keyword')
            )
            audio_context = search_audio_for_context(user_message, limit=50)

            if not context:
                response_text = "I couldn't find any matching content in the video library. Try different keywords or check the Transcripts page to see what's available."

                # Save messages if conversation exists
                if conversation_id and 'user_id' in session:
                    with DatabaseSession() as db_session:
                        # Save user message
                        user_msg = ChatMessage(
                            conversation_id=UUID(conversation_id),
                            role='user',
                            content=user_message
                        )
                        db_session.add(user_msg)

                        # Save assistant response
                        assistant_msg = ChatMessage(
                            conversation_id=UUID(conversation_id),
                            role='assistant',
                            content=response_text,
                            model=model
                        )
                        db_session.add(assistant_msg)

                        # Update conversation timestamp
                        conv = db_session.query(Conversation).filter(Conversation.id == UUID(conversation_id)).first()
                        if conv:
                            conv.updated_at = datetime.utcnow()

                        db_session.commit()

                return jsonify({
                    'response': response_text,
                    'clips': [],
                    'has_script': False,
                    'context_segments': 0,
                    'model': model,
                    'conversation_id': conversation_id
                })

            # Generate response with AI (exclude previously used clips)
            result = AIService.generate_script_with_ai(
                user_message, context, conversation_history, model=model, exclude_clips=previous_clips,
                user_id=session.get('user_id'), conversation_id=conversation_id,
                use_rag=(use_rag and context_mode != 'keyword')  # Prompt 18: RAG Integration
            )

            # Save messages to conversation
            if conversation_id and 'user_id' in session:
                with DatabaseSession() as db_session:
                    # Save user message
                    user_msg = ChatMessage(
                        conversation_id=UUID(conversation_id),
                        role='user',
                        content=user_message
                    )
                    db_session.add(user_msg)

                    # Save assistant response with clips
                    assistant_msg = ChatMessage(
                        conversation_id=UUID(conversation_id),
                        role='assistant',
                        content=result['message'],
                        clips_json=result.get('clips', []),
                        model=model
                    )
                    db_session.add(assistant_msg)

                    # Update conversation timestamp and title if it's the first message
                    conv = db_session.query(Conversation).filter(Conversation.id == UUID(conversation_id)).first()
                    if conv:
                        conv.updated_at = datetime.utcnow()
                        # Auto-title based on first user message if still default
                        if conv.title == 'New Chat':
                            conv.title = user_message[:50] + ('...' if len(user_message) > 50 else '')

                    db_session.commit()

            # Detect search method used from context results (Prompt 18: RAG Integration)
            search_method_used = 'unknown'
            if context:
                # Check if any context items have the RAG search method indicator
                rag_results = [c for c in context if c.get('search_method') == 'rag']
                if rag_results:
                    search_method_used = 'rag'
                else:
                    search_method_used = 'keyword'
            else:
                search_method_used = 'none'

            return jsonify({
                'response': result['message'],
                'clips': result.get('clips', []),
                'audio_clips': audio_context[:20] if audio_context else [],  # Include relevant audio segments
                'has_script': result.get('has_script', False),
                'context_segments': len(context),
                'audio_segments': len(audio_context) if audio_context else 0,
                'model': model,
                'conversation_id': conversation_id,
                # RAG Integration Metrics (Prompt 18)
                'search_method': search_method_used,
                'rag_enabled': use_rag,
                'context_mode': context_mode,
                'rag_config': {
                    'similarity_threshold': rag_similarity_threshold,
                    'chunks_used': len([c for c in context if c.get('search_method') == 'rag']) if context else 0
                }
            })

        # GENERAL CHAT MODE (default)
        else:
            result = AIService.generate_general_response(
                user_message=user_message,
                conversation_history=conversation_history,
                model=model,
                user_id=session.get('user_id'),
                conversation_id=conversation_id
            )

            # Save messages to conversation (skip for demo mode)
            if conversation_id and 'user_id' in session and session.get('user_id') != 'demo-user-id':
                with DatabaseSession() as db_session:
                    user_msg = ChatMessage(
                        conversation_id=UUID(conversation_id),
                        role='user',
                        content=user_message
                    )
                    db_session.add(user_msg)

                    assistant_msg = ChatMessage(
                        conversation_id=UUID(conversation_id),
                        role='assistant',
                        content=result['message'],
                        model=result['model']
                    )
                    db_session.add(assistant_msg)

                    conv = db_session.query(Conversation).filter(Conversation.id == UUID(conversation_id)).first()
                    if conv:
                        conv.updated_at = datetime.utcnow()
                        if conv.title == 'New Chat':
                            conv.title = user_message[:50] + ('...' if len(user_message) > 50 else '')

                    db_session.commit()

            return jsonify({
                'response': result['message'],
                'clips': [],
                'has_script': False,
                'context_segments': 0,
                'model': result['model'],
                'conversation_id': conversation_id
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Server error: {str(e)}',
            'response': f'Sorry, there was an error processing your request: {str(e)}',
            'clips': [],
            'has_script': False
        }), 500


# @app.route('/api/script-feedback', methods=['POST'])
def api_script_feedback():
    """Save user feedback on a generated script."""
    try:
        data = request.json
        query = data.get('query', '')
        script = data.get('script', '')
        clips = data.get('clips', [])
        rating = data.get('rating', 0)  # 1 = good, -1 = bad
        model = data.get('model', 'unknown')

        if not script or rating == 0:
            return jsonify({'error': 'Script and rating required'}), 400

        with DatabaseSession() as db_session:
            feedback = ScriptFeedback(
                query=query,
                script=script,
                clips_json=clips,
                rating=rating,
                model=model
            )
            db_session.add(feedback)
            db_session.commit()

            return jsonify({
                'success': True,
                'id': str(feedback.id),
                'message': 'Thanks! This helps improve future scripts.'
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# @app.route('/api/script-examples', methods=['GET'])
def api_script_examples():
    """Get good script examples for few-shot learning."""
    try:
        with DatabaseSession() as db_session:
            # Get top-rated scripts (rating = 1)
            examples = db_session.query(ScriptFeedback).filter(
                ScriptFeedback.rating == 1
            ).order_by(ScriptFeedback.created_at.desc()).limit(5).all()

            return jsonify({
                'examples': [{
                    'id': str(e.id),
                    'query': e.query,
                    'script': e.script,
                    'clips': e.clips_json,
                    'model': e.model
                } for e in examples]
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# @app.route('/api/video-preview/<video_id>')
def api_video_preview(video_id):
    """Get presigned S3 URL for video preview."""
    try:
        with DatabaseSession() as db_session:
            video = db_session.query(Video).filter(Video.id == UUID(video_id)).first()
            if not video:
                return jsonify({'error': 'Video not found'}), 404

            if not video.s3_key:
                return jsonify({'error': 'Video not in S3'}), 404

            # Generate presigned URL (valid for 1 hour)
            config = get_config()
            bucket = config.s3_bucket

            s3_client = get_s3_client()
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': video.s3_key},
                ExpiresIn=3600  # 1 hour
            )

            return jsonify({
                'url': presigned_url,
                'video_id': str(video.id),
                'filename': video.filename,
                'duration': video.duration_seconds
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# @app.route('/api/audio-preview/<audio_id>')
def api_audio_preview(audio_id):
    """Get presigned S3 URL for audio preview."""
    try:
        with DatabaseSession() as db_session:
            audio = db_session.query(AudioRecording).filter(AudioRecording.id == UUID(audio_id)).first()
            if not audio:
                return jsonify({'error': 'Audio not found'}), 404

            if not audio.s3_key:
                return jsonify({'error': 'Audio not in S3'}), 404

            # Generate presigned URL (valid for 1 hour)
            s3_client = get_s3_client()
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': audio.s3_bucket, 'Key': audio.s3_key},
                ExpiresIn=3600  # 1 hour
            )

            return jsonify({
                'url': presigned_url,
                'audio_id': str(audio.id),
                'title': audio.title,
                'filename': audio.filename,
                'duration': float(audio.duration_seconds) if audio.duration_seconds else None
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# @app.route('/api/audio-clip/<audio_id>')
def api_audio_clip(audio_id):
    """Get audio clip info with presigned URL and time range for playback."""
    try:
        start_time = request.args.get('start', type=float, default=0)
        end_time = request.args.get('end', type=float, default=None)

        with DatabaseSession() as db_session:
            audio = db_session.query(AudioRecording).filter(AudioRecording.id == UUID(audio_id)).first()
            if not audio:
                return jsonify({'error': 'Audio not found'}), 404

            if not audio.s3_key:
                return jsonify({'error': 'Audio not in S3'}), 404

            # Generate presigned URL
            s3_client = get_s3_client()
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': audio.s3_bucket, 'Key': audio.s3_key},
                ExpiresIn=3600
            )

            return jsonify({
                'url': presigned_url,
                'audio_id': str(audio.id),
                'title': audio.title,
                'start_time': start_time,
                'end_time': end_time or (float(audio.duration_seconds) if audio.duration_seconds else None),
                'duration': float(audio.duration_seconds) if audio.duration_seconds else None
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# @app.route('/api/chat/create-video', methods=['POST'])
def api_create_video_from_chat():
    """Create video clips from chat-generated script."""
    data = request.json
    clips = data.get('clips', [])
    title = data.get('title', 'Chat Script')

    if not clips:
        return jsonify({'error': 'No clips provided'}), 400

    # Create clips folder
    safe_title = re.sub(r'[^\w\-_ ]', '_', title)
    output_dir = Path('local_clips') / safe_title
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate edit script
    script_content = f"# {title}\n"
    script_content += f"# Generated from Chat\n"
    script_content += f"# Total clips: {len(clips)}\n\n"

    total_duration = 0
    for i, clip in enumerate(clips, 1):
        duration = clip.get('duration', clip.get('end_time', 0) - clip.get('start_time', 0))
        total_duration += duration
        script_content += f"## Clip {i}\n"
        script_content += f"Source: {clip.get('video_title', 'Unknown')}\n"
        script_content += f"Time: {clip.get('start_time', 0):.1f}s - {clip.get('end_time', 0):.1f}s ({duration:.1f}s)\n"
        script_content += f"Text: \"{clip.get('text', '')}\"\n"
        script_content += f"Verified: {'Yes' if clip.get('verified') else 'No'}\n\n"

    script_content += f"\n# Total Duration: {total_duration:.1f}s\n"

    with open(output_dir / 'EDIT_SCRIPT.txt', 'w') as f:
        f.write(script_content)

    return jsonify({
        'success': True,
        'folder': str(output_dir),
        'script_path': str(output_dir / 'EDIT_SCRIPT.txt'),
        'total_duration': total_duration
    })


# @app.route('/api/chat/export-script', methods=['POST'])
def api_export_script():
    """Generate a downloadable script file."""
    from flask import Response

    data = request.json
    clips = data.get('clips', [])
    title = data.get('title', 'Video Script')
    script_text = data.get('script_text', '')

    if not clips:
        return jsonify({'error': 'No clips provided'}), 400

    # Generate edit script content
    content = f"# {title}\n"
    content += f"# Generated from MV Videos\n"
    content += f"# Total clips: {len(clips)}\n"
    content += "=" * 50 + "\n\n"

    if script_text:
        # Clean up the script text - remove JSON blocks
        clean_script = re.sub(r'```json[\s\S]*?```', '', script_text)
        clean_script = re.sub(r'---', '', clean_script)
        content += "SCRIPT:\n\n"
        content += clean_script.strip()
        content += "\n\n" + "=" * 50 + "\n\n"

    content += "CLIP DETAILS:\n\n"
    total_duration = 0
    for i, clip in enumerate(clips, 1):
        duration = clip.get('duration', clip.get('end_time', 0) - clip.get('start_time', 0))
        total_duration += duration
        content += f"--- Clip {i} ---\n"
        content += f"Source: {clip.get('video_title', 'Unknown')}\n"
        content += f"Speaker: {clip.get('speaker', 'Unknown')}\n"
        content += f"Time: {clip.get('start_time', 0):.1f}s - {clip.get('end_time', 0):.1f}s ({duration:.1f}s)\n"
        content += f"Text: \"{clip.get('text', '')}\"\n"
        content += f"Video ID: {clip.get('video_id', 'Unknown')}\n"
        content += f"Verified: {'Yes' if clip.get('verified') else 'No'}\n\n"

    content += "=" * 50 + "\n"
    content += f"Total Duration: {total_duration:.1f}s\n"

    # Create filename
    safe_title = re.sub(r'[^\w\-_ ]', '_', title)
    filename = f"{safe_title}_script.txt"

    return Response(
        content,
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


# @app.route('/api/video-thumbnail/<video_id>')
def api_video_thumbnail(video_id):
    """Return pre-generated thumbnail from S3 (fast) or redirect to placeholder."""
    try:
        with DatabaseSession() as db_session:
            video = db_session.query(Video).filter(Video.id == UUID(video_id)).first()
            if not video:
                return '', 404

            config = get_config()
            bucket = config.s3_bucket
            s3_client = get_s3_client()

            # If we have a pre-generated thumbnail, return presigned URL redirect
            if video.thumbnail_s3_key:
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': video.thumbnail_s3_key},
                    ExpiresIn=3600
                )
                return redirect(presigned_url)

            # No pre-generated thumbnail - return 404 (placeholder will show)
            return '', 404

    except Exception as e:
        print(f"[THUMB] Error: {e}")
        return '', 404


# @app.route('/api/clip-preview/<video_id>')
def api_clip_preview(video_id):
    """Return presigned URL for streaming preview - fast and reliable."""
    start_time = request.args.get('start', type=float, default=0)
    end_time = request.args.get('end', type=float, default=30)

    try:
        with DatabaseSession() as db_session:
            video = db_session.query(Video).filter(Video.id == UUID(video_id)).first()
            if not video:
                return jsonify({'error': 'Video not found'}), 404

            if not video.s3_key:
                return jsonify({'error': 'Video not in S3'}), 404

            config = get_config()
            bucket = config.s3_bucket
            s3_client = get_s3_client()

            # Generate presigned URL for streaming - browser will handle seeking
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': video.s3_key},
                ExpiresIn=3600
            )

            return jsonify({
                'url': presigned_url,
                'start': start_time,
                'end': end_time,
                'title': video.filename or video.original_filename
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/clip-download/<video_id>')
def api_clip_download(video_id):
    """Download a clip at original quality with optional metadata."""
    # Authentication check
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    start_time = request.args.get('start', type=float, default=0)
    end_time = request.args.get('end', type=float, default=30)
    include_metadata = request.args.get('metadata', type=bool, default=True)
    timeout = min(request.args.get('timeout', 300, type=int), 900)  # Max 15 minutes

    try:
        result = VideoService.process_clip_download(
            video_id=video_id,
            user_id=session['user_id'],
            start_time=start_time,
            end_time=end_time,
            include_metadata=include_metadata,
            timeout=timeout
        )

        if include_metadata:
            return jsonify(result)
        else:
            # Direct file download
            return send_file(
                result['file_path'],
                mimetype=result['mimetype'],
                as_attachment=True,
                download_name=result['filename']
            )

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except FileNotFoundError:
        return jsonify({'error': 'Video not found'}), 404
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Download timed out - clip may be too long'}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/video-download/<video_id>')
def api_video_download(video_id):
    """Download the full video with optional metadata."""
    # Authentication check
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    include_metadata = request.args.get('metadata', type=bool, default=True)

    try:
        result = VideoService.generate_download_url(video_id, session['user_id'])

        if include_metadata:
            return jsonify(result)
        else:
            # Direct redirect to S3
            return redirect(result['download_url'])

    except FileNotFoundError:
        return jsonify({'error': 'Video not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/video/<video_id>/download-options')
def api_video_download_options(video_id):
    """Get download options and metadata for a video without triggering download."""
    # Authentication check
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        options = VideoService.get_download_options(video_id, session['user_id'])
        return jsonify(options)
    except FileNotFoundError:
        return jsonify({'error': 'Video not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# @app.route('/api/transcript-segment/update', methods=['POST'])
def api_update_transcript_segment():
    """Update transcript text for a specific segment by time range."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        video_id = data.get('video_id')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        new_text = data.get('text')

        if not all([video_id, start_time is not None, end_time is not None, new_text]):
            return jsonify({'error': 'Missing required fields'}), 400

        with DatabaseSession() as db_session:
            # Find transcript for this video
            from scripts.db import Transcript, TranscriptSegment
            transcript = db_session.query(Transcript).filter(
                Transcript.video_id == UUID(video_id)
            ).first()

            if not transcript:
                return jsonify({'error': 'Transcript not found'}), 404

            # Find segments that overlap with the given time range
            segments = db_session.query(TranscriptSegment).filter(
                TranscriptSegment.transcript_id == transcript.id,
                TranscriptSegment.start_time >= float(start_time) - 0.5,
                TranscriptSegment.end_time <= float(end_time) + 0.5
            ).order_by(TranscriptSegment.start_time).all()

            if not segments:
                # Try a broader search
                segments = db_session.query(TranscriptSegment).filter(
                    TranscriptSegment.transcript_id == transcript.id,
                    TranscriptSegment.start_time >= float(start_time) - 2,
                    TranscriptSegment.start_time <= float(end_time) + 2
                ).order_by(TranscriptSegment.start_time).all()

            if not segments:
                return jsonify({'error': 'No matching segments found'}), 404

            # If multiple segments match, merge them into one with the new text
            if len(segments) > 1:
                # First segment gets the new text and expands to cover all time
                segments[0].text = new_text.strip()
                segments[0].end_time = segments[-1].end_time

                # Delete the other segments
                for seg in segments[1:]:
                    db_session.delete(seg)
            else:
                # Single segment - just update the text
                segments[0].text = new_text.strip()

            # Rebuild full_text from all segments
            all_segments = db_session.query(TranscriptSegment).filter(
                TranscriptSegment.transcript_id == transcript.id
            ).order_by(TranscriptSegment.start_time).all()

            transcript.full_text = ' '.join(seg.text for seg in all_segments if seg.text)
            transcript.word_count = len(transcript.full_text.split())

            db_session.commit()

            return jsonify({
                'success': True,
                'message': f'Updated segment and rebuilt transcript',
                'segment_id': str(segments[0].id)
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# @app.route('/api/transcripts/<transcript_id>/identify-speakers', methods=['POST'])
def api_identify_speakers(transcript_id):
    """Use AI to identify and label speakers in a transcript."""
    try:
        data = request.json or {}
        known_speakers = data.get('known_speakers', [])  # List of known speaker names

        with DatabaseSession() as db_session:
            transcript = db_session.query(Transcript).filter(
                Transcript.id == UUID(transcript_id)
            ).first()

            if not transcript:
                return jsonify({'error': 'Transcript not found'}), 404

            # Get video info
            video = db_session.query(Video).filter(Video.id == transcript.video_id).first()
            video_speaker = video.speaker if video else None

            # Get segments
            segments = db_session.query(TranscriptSegment).filter(
                TranscriptSegment.transcript_id == transcript.id
            ).order_by(TranscriptSegment.start_time).limit(100).all()

            if not segments:
                return jsonify({'error': 'No segments found'}), 404

            # Build transcript with timestamps
            transcript_text = ""
            for i, seg in enumerate(segments):
                mins = int(seg.start_time // 60)
                secs = int(seg.start_time % 60)
                transcript_text += f"[{mins}:{secs:02d}] {seg.text}\n"

            # Add known speaker context
            speaker_context = ""
            if video_speaker:
                speaker_context = f"The main speaker is: {video_speaker}\n"
            if known_speakers:
                speaker_context += f"Other known speakers: {', '.join(known_speakers)}\n"

            # Use Claude to identify speakers
            client = AIService.get_anthropic_client()

            prompt = f"""Analyze this transcript and identify different speakers. Look for:
- Changes in speaking style or tone
- Questions followed by answers
- Introductions or speaker identifications
- Different perspectives or topics

{speaker_context}

TRANSCRIPT:
{transcript_text[:8000]}

For each distinct voice/speaker you identify, provide:
1. A label (use actual name if mentioned, otherwise "Speaker 1", "Speaker 2", etc.)
2. Time ranges where they speak (approximate)
3. Key characteristics that helped identify them

Respond in JSON format:
{{
  "speakers": [
    {{
      "label": "Speaker Name or Speaker 1",
      "time_ranges": ["0:00-1:30", "3:45-5:00"],
      "characteristics": "Main presenter, discusses NASA"
    }}
  ],
  "speaker_changes": [
    {{"time": "0:00", "speaker": "Speaker 1"}},
    {{"time": "1:30", "speaker": "Speaker 2"}}
  ]
}}"""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"speakers": [], "speaker_changes": []}

            return jsonify({
                'success': True,
                'speakers': result.get('speakers', []),
                'speaker_changes': result.get('speaker_changes', [])
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# @app.route('/api/segments/<segment_id>/speaker', methods=['PUT'])
def api_update_segment_speaker(segment_id):
    """Update speaker label for a segment."""
    try:
        data = request.json
        speaker = data.get('speaker', '').strip()

        with DatabaseSession() as db_session:
            segment = db_session.query(TranscriptSegment).filter(
                TranscriptSegment.id == UUID(segment_id)
            ).first()

            if not segment:
                return jsonify({'error': 'Segment not found'}), 404

            segment.speaker = speaker if speaker else None
            db_session.commit()

            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# @app.route('/api/videos/<video_id>/autofill', methods=['POST'])
def api_autofill_video(video_id):
    """Use AI to auto-fill video metadata from transcript."""
    try:
        with DatabaseSession() as db_session:
            video = db_session.query(Video).filter(Video.id == UUID(video_id)).first()
            if not video:
                return jsonify({'error': 'Video not found'}), 404

            # Get transcript
            transcript = db_session.query(Transcript).filter(
                Transcript.video_id == video.id,
                Transcript.status == 'completed'
            ).first()

            if not transcript:
                return jsonify({'error': 'No transcript available for this video'}), 404

            # Get transcript segments
            segments = db_session.query(TranscriptSegment).filter(
                TranscriptSegment.transcript_id == transcript.id
            ).order_by(TranscriptSegment.start_time).all()

            if not segments:
                return jsonify({'error': 'Transcript has no segments'}), 404

            # Build transcript text (first 5000 chars for context)
            transcript_text = ' '.join(s.text for s in segments)[:5000]

            # Get existing video metadata for context
            existing_speaker = video.speaker or ''
            filename = video.filename or ''

            # Use Claude to analyze
            client = AIService.get_anthropic_client()

            prompt = f"""Analyze this video transcript and extract metadata. The video filename is "{filename}".

TRANSCRIPT (first part):
{transcript_text}

Based on this transcript, provide:
1. A 1-2 sentence description of what this video is about
2. The speaker's name (if mentioned or identifiable). Current value: "{existing_speaker}"
3. The event name (conference, show, interview, etc.) if mentioned
4. 3-5 relevant topic tags (comma-separated)
5. Any other speakers mentioned (comma-separated)

Respond in this exact JSON format:
{{
  "description": "...",
  "speaker": "...",
  "event_name": "...",
  "topics": "...",
  "other_speakers": "..."
}}

If you can't determine a field, use empty string. Be concise."""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            response_text = response.content[0].text

            # Extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                suggestions = json.loads(json_match.group())
            else:
                suggestions = {}

            return jsonify({
                'success': True,
                'suggestions': suggestions,
                'transcript_preview': transcript_text[:500] + '...'
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# @app.route('/api/videos/<video_id>', methods=['PUT'])
def api_update_video(video_id):
    """Update video metadata."""
    try:
        data = request.json

        with DatabaseSession() as db_session:
            video = db_session.query(Video).filter(Video.id == UUID(video_id)).first()
            if not video:
                return jsonify({'error': 'Video not found'}), 404

            # Update allowed fields
            if 'filename' in data:
                # Preserve .mp4 extension if not provided
                new_filename = data['filename']
                if new_filename and not new_filename.endswith('.mp4'):
                    new_filename = new_filename + '.mp4'
                video.filename = new_filename
            if 'speaker' in data:
                video.speaker = data['speaker'] or None
            if 'event_name' in data:
                video.event_name = data['event_name'] or None
            if 'event_date' in data:
                if data['event_date']:
                    from datetime import datetime as dt
                    video.event_date = dt.strptime(data['event_date'], '%Y-%m-%d').date()
                else:
                    video.event_date = None
            if 'description' in data:
                video.description = data['description'] or None

            # Handle custom fields via extra_data (JSONB)
            if 'tags' in data:
                extra = video.extra_data or {}
                extra['tags'] = data['tags']
                video.extra_data = extra
            if 'topics' in data:
                extra = video.extra_data or {}
                extra['topics'] = data['topics']
                video.extra_data = extra
            if 'custom_fields' in data:
                extra = video.extra_data or {}
                extra.update(data['custom_fields'])
                video.extra_data = extra

            db_session.commit()

            return jsonify({
                'success': True,
                'video_id': str(video.id),
                'message': 'Video updated successfully'
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# @app.route('/api/videos/<video_id>', methods=['GET'])
def api_get_video(video_id):
    """Get single video details."""
    try:
        with DatabaseSession() as db_session:
            video = db_session.query(Video).filter(Video.id == UUID(video_id)).first()
            if not video:
                return jsonify({'error': 'Video not found'}), 404

            return jsonify({
                'id': str(video.id),
                'filename': video.filename,
                'speaker': video.speaker,
                'event_name': video.event_name,
                'event_date': video.event_date.strftime('%Y-%m-%d') if video.event_date else None,
                'description': video.description,
                'duration': float(video.duration_seconds) if video.duration_seconds else None,
                'extra_data': video.extra_data or {},
                'tags': (video.extra_data or {}).get('tags', ''),
                'topics': (video.extra_data or {}).get('topics', ''),
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Admin emails authorized to invite users
ADMIN_EMAILS = ['joy@maurinventures.com']


# @app.route('/admin/invite', methods=['GET', 'POST'])
def admin_invite():
    """Admin page to invite new users."""
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Check if user is admin
    if session.get('user_email') not in ADMIN_EMAILS:
        return redirect(url_for('chat'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()

        if not name or not email:
            return render_template('admin_invite.html', error='Name and email are required')

        # Validate email format
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return render_template('admin_invite.html', error='Invalid email format')

        with DatabaseSession() as db_session:
            # Check if email already exists
            existing = db_session.query(User).filter(User.email == email).first()
            if existing:
                return render_template('admin_invite.html', error='Email already registered')

            # Generate a random password
            password = secrets.token_urlsafe(12)
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            # Create user (email verified since invited by admin)
            user = User(
                name=name,
                email=email,
                password_hash=password_hash,
                email_verified=1,  # Pre-verified since invited by admin
                is_active=1
            )
            db_session.add(user)
            db_session.commit()

            # Send invite email
            if send_invite_email(email, name, password):
                return render_template('admin_invite.html',
                    success=True,
                    message=f'Invitation sent to {email}')
            else:
                return render_template('admin_invite.html',
                    success=True,
                    message=f'User created but email failed. Password: {password}')

    return render_template('admin_invite.html')


# ==============================================================================
# API HEALTH AND STATUS ENDPOINTS (Prompt 26)
# ==============================================================================

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint for monitoring and smoke tests."""
    try:
        # Test database connectivity
        with DatabaseSession() as db_session:
            # Simple query to verify database is accessible
            result = db_session.execute(text("SELECT 1")).fetchone()
            db_healthy = result is not None
    except Exception as e:
        db_healthy = False
        app.logger.error(f"Health check database error: {str(e)}")

    # Check application status
    health_data = {
        'status': 'healthy' if db_healthy else 'unhealthy',
        'timestamp': time.time(),
        'version': '1.0.0',  # Could be read from environment or config
        'checks': {
            'database': 'healthy' if db_healthy else 'unhealthy',
            'application': 'healthy'  # App is running if we got here
        }
    }

    status_code = 200 if db_healthy else 503
    return jsonify(health_data), status_code


# ==============================================================================
# NEW API AUTH ENDPOINTS FOR REACT FRONTEND
# ==============================================================================

@app.route('/api/auth/me', methods=['GET'])
def api_auth_me():
    """Get current authenticated user info."""
    # Check if user has been logged out
    if session.get('logged_out'):
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    is_demo = user_id == AuthService.DEMO_USER_ID
    user = AuthService.get_user_by_id(user_id, is_demo)

    if not user:
        session.clear()
        return jsonify({'error': 'User not found'}), 401

    return jsonify({'user': user})


@app.route('/api/auth/test', methods=['POST'])
def api_auth_test():
    """Test endpoint for debugging POST requests."""
    try:
        return jsonify({
            'success': True,
            'message': 'POST request received successfully',
            'content_type': request.content_type,
            'is_json': request.is_json,
            'data': str(request.get_data())[:100]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    """API login endpoint that handles 2FA flow."""
    try:
        # Use the same approach as the working test endpoint
        import json
        raw_data = request.get_data(as_text=True)
        data = json.loads(raw_data) if raw_data else {}

        email = data.get('email', '')
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password are required'}), 400

        result = AuthService.authenticate_user(email, password)

        if not result['success']:
            return jsonify(result), 401

        # Handle demo mode
        if result.get('is_demo'):
            session['user_id'] = AuthService.DEMO_USER_ID
            session['user_email'] = email
            return jsonify(result)

        # Handle 2FA flow
        if result.get('requires_2fa'):
            session['pending_2fa_user_id'] = result['user_id']
            session['pending_2fa_email'] = result['user']['email']
            session.modified = True  # Explicitly mark session as modified
            return jsonify(result)

        if result.get('requires_2fa_setup'):
            session.permanent = True  # Make session permanent
            session['pending_2fa_setup_user_id'] = result['user_id']
            session['pending_2fa_setup_email'] = result['user']['email']
            session['pending_2fa_setup_name'] = result['user']['name']
            session.modified = True  # Explicitly mark session as modified
            return jsonify(result)

        return jsonify(result)

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Login failed'}), 500


@app.route('/api/auth/verify-2fa', methods=['POST'])
def api_auth_verify_2fa():
    """Verify 2FA code and complete login."""
    try:
        if 'pending_2fa_user_id' not in session:
            return jsonify({'success': False, 'error': 'No pending 2FA verification'}), 400

        data = request.json or {}
        token = data.get('token', '').strip()
        user_id = session['pending_2fa_user_id']

        result = AuthService.verify_2fa_token(user_id, token)

        if result['success']:
            # Set up persistent session (7 days)
            session.permanent = True
            session['user_id'] = user_id
            session['user_name'] = result['user']['name']
            session['user_email'] = result['user']['email']
            session.pop('pending_2fa_user_id', None)
            session.pop('pending_2fa_email', None)

        return jsonify(result), 200 if result['success'] else 401

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"2FA verification error: {e}")
        return jsonify({'success': False, 'error': '2FA verification failed'}), 500


@app.route('/api/auth/setup-2fa', methods=['POST'])
def api_auth_setup_2fa():
    """Set up 2FA - generate QR code or verify setup code."""
    try:
        data = request.json or {}
        token = data.get('token')

        # For initial setup (no token provided) - generate QR code
        if not token:
            if 'pending_2fa_setup_user_id' not in session:
                return jsonify({
                    'success': False,
                    'error': 'No pending 2FA setup'
                }), 400

            qr_data = AuthService.setup_2fa_secret()

            # Store secret temporarily in session for verification
            session.permanent = True  # Make session permanent
            session['totp_setup_secret'] = qr_data['secret']  # Try different key name
            session.modified = True  # Explicitly mark session as modified

            # ALSO store in database as backup (for multi-worker safety)
            user_id = session.get('pending_2fa_setup_user_id')
            if user_id:
                with DatabaseSession() as db_session:
                    user = db_session.query(User).filter(User.id == UUID(user_id)).first()
                    if user:
                        # Store in temp field - we'll clear this after completion
                        user.temp_2fa_secret = qr_data['secret']
                        db_session.commit()

            return jsonify({
                'success': True,
                'qr_code': qr_data['qr_code'],
                'secret': qr_data['secret']
            })

        # For verification (token provided) - complete setup
        else:
            user_id = session.get('pending_2fa_setup_user_id')
            secret = session.get('totp_setup_secret')

            has_user_id = bool(user_id)
            has_secret = bool(secret)

            # If session doesn't have secret, try database backup
            if not has_secret and has_user_id:
                with DatabaseSession() as db_session:
                    user = db_session.query(User).filter(User.id == UUID(user_id)).first()
                    if user and user.temp_2fa_secret:
                        secret = user.temp_2fa_secret
                        has_secret = True

            if not has_user_id or not has_secret:
                return jsonify({
                    'success': False,
                    'error': 'No pending 2FA setup'
                }), 400

            result = AuthService.complete_2fa_setup(user_id, secret, token)

            if result['success']:
                # Complete login and clear session data
                session.permanent = True
                session['user_id'] = user_id
                session['user_name'] = session.get('pending_2fa_setup_name')
                session['user_email'] = session.get('pending_2fa_setup_email')
                session.pop('pending_2fa_setup_user_id', None)
                session.pop('pending_2fa_setup_email', None)
                session.pop('pending_2fa_setup_name', None)
                session.pop('totp_setup_secret', None)

                # Clear database backup
                with DatabaseSession() as db_session:
                    user = db_session.query(User).filter(User.id == UUID(user_id)).first()
                    if user:
                        user.temp_2fa_secret = None
                        db_session.commit()

                # Get updated user data
                user = AuthService.get_user_by_id(user_id)
                result['user'] = user

            return jsonify(result), 200 if result['success'] else 401

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"2FA setup error: {e}")
        return jsonify({'success': False, 'error': '2FA setup failed'}), 500


@app.route('/api/auth/backup-codes', methods=['POST'])
def api_auth_generate_backup_codes():
    """Generate new backup codes for the authenticated user."""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401

        with DatabaseSession() as db_session:
            # Import the new models
            from scripts.db import BackupCode

            user_id = UUID(session['user_id'])

            # Delete existing backup codes
            db_session.query(BackupCode).filter(BackupCode.user_id == user_id).delete()

            # Generate 8 new backup codes
            codes = []
            for _ in range(8):
                code = secrets.token_hex(4).upper()  # 8-character hex code
                code_hash = hashlib.sha256(code.encode()).hexdigest()

                backup_code = BackupCode(
                    user_id=user_id,
                    code_hash=code_hash,
                    is_used=0
                )
                db_session.add(backup_code)
                codes.append(code)

            db_session.commit()

            return jsonify({
                'success': True,
                'codes': codes
            })

    except Exception as e:
        print(f"Backup codes generation error: {e}")
        return jsonify({'success': False, 'error': 'Failed to generate backup codes'}), 500


@app.route('/api/auth/verify-backup-code', methods=['POST'])
def api_auth_verify_backup_code():
    """Verify backup code for 2FA."""
    try:
        if 'pending_2fa_user_id' not in session:
            return jsonify({'success': False, 'error': 'No pending 2FA verification'}), 400

        data = request.json or {}
        code = data.get('code', '').strip().upper()

        if not code:
            return jsonify({'success': False, 'error': 'Backup code is required'}), 400

        with DatabaseSession() as db_session:
            # Import the new models
            from scripts.db import BackupCode

            user = db_session.query(User).filter(
                User.id == session['pending_2fa_user_id']
            ).first()

            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 400

            # Find matching backup code
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            backup_code = db_session.query(BackupCode).filter(
                BackupCode.user_id == user.id,
                BackupCode.code_hash == code_hash,
                BackupCode.is_used == 0
            ).first()

            if backup_code:
                # Mark code as used
                backup_code.is_used = 1
                backup_code.used_at = datetime.utcnow()
                user.last_login = datetime.utcnow()
                db_session.commit()

                # Complete login
                session.permanent = True
                session['user_id'] = str(user.id)
                session['user_name'] = user.name
                session['user_email'] = user.email
                session.pop('pending_2fa_user_id', None)
                session.pop('pending_2fa_email', None)

                return jsonify({
                    'success': True,
                    'user': {
                        'id': str(user.id),
                        'name': user.name,
                        'email': user.email,
                        'is_active': bool(user.is_active),
                        'email_verified': bool(user.email_verified),
                        'totp_enabled': bool(user.totp_enabled),
                        'created_at': user.created_at.isoformat(),
                        'last_login': user.last_login.isoformat() if user.last_login else None,
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'Invalid or already used backup code'}), 401

    except Exception as e:
        print(f"Backup code verification error: {e}")
        return jsonify({'success': False, 'error': 'Backup code verification failed'}), 500


@app.route('/api/auth/register', methods=['POST'])
def api_auth_register():
    """Register new user with email verification."""
    try:
        data = request.json or {}
        name = data.get('name', '')
        email = data.get('email', '')
        password = data.get('password', '')

        result = AuthService.register_user(name, email, password)
        return jsonify(result), 200 if result['success'] else 400

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'success': False, 'error': 'Registration failed'}), 500


# ==============================================================================
# CONVERSATIONS ENDPOINTS - DEMO MODE
# ==============================================================================

@app.route('/api/conversations', methods=['GET'])
def api_conversations_list():
    """List conversations for current user - Demo mode."""
    if session.get('user_id') == 'demo-user-id':
        return jsonify({
            'conversations': [
                {
                    'id': 'demo-conv-1',
                    'title': 'Demo Conversation',
                    'preferred_model': 'gpt-4o',
                    'created_at': '2026-01-06T21:30:00Z',
                    'updated_at': '2026-01-06T21:30:00Z',
                    'message_count': 0,
                    'project_id': None
                }
            ]
        })
    return jsonify({'error': 'Not authenticated'}), 401

@app.route('/api/conversations', methods=['POST'])
def api_conversations_create():
    """Create new conversation - Demo mode."""
    if session.get('user_id') == 'demo-user-id':
        data = request.json or {}
        conversation = {
            'id': f"demo-conv-{int(time.time())}",
            'title': data.get('title', 'New Conversation'),
            'preferred_model': data.get('preferred_model', 'gpt-4o'),
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'updated_at': datetime.utcnow().isoformat() + 'Z',
            'project_id': data.get('project_id'),
            'message_count': 0
        }
        return jsonify(conversation)
    return jsonify({'error': 'Not authenticated'}), 401


@app.route('/api/auth/verify-email', methods=['GET', 'POST'])
def api_auth_verify_email():
    """Verify email with token or code."""
    try:
        # Handle both GET (legacy URL-based) and POST (new code-based) requests
        if request.method == 'GET':
            token = request.args.get('token', '')
        else:  # POST
            data = request.json or {}
            token = data.get('code', '') or data.get('token', '')

        if not token:
            return jsonify({'success': False, 'error': 'Verification code is required'}), 400

        result = AuthService.verify_email(token)

        # If email verification succeeded, set up 2FA setup session
        if result['success'] and result.get('user'):
            user = result['user']
            # Since 2FA is mandatory for all users, set up the 2FA setup session
            session.permanent = True  # Make session permanent
            session['pending_2fa_setup_user_id'] = user['id']
            session['pending_2fa_setup_email'] = user['email']
            session['pending_2fa_setup_name'] = user['name']
            session.modified = True  # Explicitly mark session as modified

            # Add requires_2fa_setup to the response
            result['requires_2fa_setup'] = True

        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        print(f"Email verification error: {e}")
        return jsonify({'success': False, 'error': 'Email verification failed'}), 500


@app.route('/api/auth/resend-verification', methods=['POST'])
def api_auth_resend_verification():
    """Resend email verification."""
    try:
        data = request.json or {}
        email = data.get('email', '')

        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400

        result = AuthService.resend_verification_email(email)
        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        print(f"Resend verification error: {e}")
        return jsonify({'success': False, 'error': 'Failed to resend verification'}), 500


@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    """Logout user."""
    # Set logout flag before clearing session
    session['logged_out'] = True

    # Explicitly remove session keys
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)
    session.pop('pending_2fa_user_id', None)
    session.pop('pending_2fa_email', None)
    session.pop('totp_setup_secret', None)

    # Clear any remaining session data except logout flag
    user_logged_out = session.get('logged_out')
    session.clear()
    if user_logged_out:
        session['logged_out'] = True
    return jsonify({'success': True})


# Prompt 19: Usage Stats and Tracking API Endpoint
@app.route('/api/usage/stats', methods=['GET'])
def api_usage_stats():
    """Get usage statistics and limits for the current user."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session['user_id']

    try:
        # Import usage limits service
        from web.services.usage_limits_service import UsageLimitsService

        # Get days parameter (default 30 days)
        days = request.args.get('days', 30, type=int)
        if days < 1 or days > 365:
            days = 30

        # Get comprehensive usage stats
        stats = UsageLimitsService.get_user_usage_stats(user_id, days)

        # Get current daily usage check
        daily_check = UsageLimitsService.check_daily_user_limit(user_id)

        # Get context limits info
        context_limits = {
            'max_context_tokens': UsageLimitsService.MAX_CONTEXT_TOKENS,
            'warning_threshold': UsageLimitsService.WARNING_THRESHOLD
        }

        # Build response
        response_data = {
            'user_id': user_id,
            'current_usage': {
                'today_tokens': daily_check['usage'],
                'today_percentage': daily_check['percentage'],
                'daily_limit': daily_check['limit'],
                'warning_active': daily_check['warning'],
                'limit_reached': not daily_check['allowed']
            },
            'period_stats': {
                'period_days': stats['period_days'],
                'total_calls': stats['total_calls'],
                'total_input_tokens': stats['total_input_tokens'],
                'total_output_tokens': stats['total_output_tokens'],
                'total_tokens': stats['total_tokens'],
                'total_cost': round(stats['total_cost'], 4),
                'models_used': stats['models_used'],
                'avg_cost_per_call': round(stats['total_cost'] / max(stats['total_calls'], 1), 4)
            },
            'limits': {
                'max_daily_tokens': UsageLimitsService.MAX_DAILY_TOKENS_PER_USER,
                'max_context_tokens': UsageLimitsService.MAX_CONTEXT_TOKENS,
                'warning_threshold_percent': UsageLimitsService.WARNING_THRESHOLD * 100
            },
            'model_pricing': UsageLimitsService.MODEL_COSTS
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"[ERROR] Usage stats API error: {e}")
        return jsonify({'error': 'Failed to get usage statistics', 'details': str(e)}), 500


@app.route('/api/usage/clean-cache', methods=['POST'])
def api_clean_usage_cache():
    """Clean old cached prompts (admin only)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session['user_id']

    # Basic admin check (you might want to make this more sophisticated)
    user_email = session.get('user_email', '')
    if not user_email.endswith('@maurinventures.com'):
        return jsonify({'error': 'Admin access required'}), 403

    try:
        from web.services.usage_limits_service import UsageLimitsService

        # Get days parameter (default 30 days)
        days = request.json.get('days', 30) if request.json else 30
        if days < 1 or days > 365:
            days = 30

        deleted_count = UsageLimitsService.clean_old_cache(days)

        return jsonify({
            'success': True,
            'deleted_entries': deleted_count,
            'cutoff_days': days
        })

    except Exception as e:
        print(f"[ERROR] Cache cleanup API error: {e}")
        return jsonify({'error': 'Failed to clean cache', 'details': str(e)}), 500


@app.route('/api/usage/status', methods=['GET'])
def api_usage_status():
    """Get current usage status for the authenticated user."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session['user_id']

    try:
        from web.services.usage_limits_service import UsageLimitsService

        # Get current daily usage check
        daily_check = UsageLimitsService.check_daily_user_limit(user_id)

        response_data = {
            'user_id': user_id,
            'usage_allowed': daily_check['allowed'],
            'daily_tokens_used': daily_check['usage'],
            'daily_tokens_remaining': daily_check['limit'] - daily_check['usage'],
            'daily_percentage_used': daily_check['percentage'],
            'warning_active': daily_check['warning'],
            'limit_reached': not daily_check['allowed'],
            'max_daily_tokens': daily_check['limit']
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"[ERROR] Usage status API error: {e}")
        return jsonify({'error': 'Failed to get usage status', 'details': str(e)}), 500


@app.route('/api/usage/limits', methods=['GET'])
def api_usage_limits():
    """Get usage limits and pricing information."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        from web.services.usage_limits_service import UsageLimitsService

        response_data = {
            'limits': {
                'max_daily_tokens_per_user': UsageLimitsService.MAX_DAILY_TOKENS_PER_USER,
                'max_context_tokens_per_request': UsageLimitsService.MAX_CONTEXT_TOKENS,
                'warning_threshold_percent': UsageLimitsService.WARNING_THRESHOLD * 100
            },
            'model_pricing': {
                model: {
                    'input_cost_per_1k_tokens': input_rate,
                    'output_cost_per_1k_tokens': output_rate,
                    'currency': 'USD'
                }
                for model, (input_rate, output_rate) in UsageLimitsService.MODEL_COSTS.items()
            },
            'supported_models': list(UsageLimitsService.MODEL_COSTS.keys())
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"[ERROR] Usage limits API error: {e}")
        return jsonify({'error': 'Failed to get usage limits', 'details': str(e)}), 500


# Prompt 20: Generation Pipeline API Endpoints
@app.route('/api/generation/jobs', methods=['POST'])
def api_create_generation_job():
    """Create a new long-form content generation job."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session['user_id']

    try:
        from scripts.generation_service import GenerationService

        data = request.get_json()
        if not data or 'brief' not in data:
            return jsonify({'error': 'Brief is required'}), 400

        brief = data.get('brief', '').strip()
        if not brief:
            return jsonify({'error': 'Brief cannot be empty'}), 400

        job_id = GenerationService.create_generation_job(
            brief=brief,
            job_name=data.get('job_name'),
            job_type=data.get('job_type', 'article'),
            content_format=data.get('content_format', 'blog_post'),
            target_word_count=data.get('target_word_count'),
            target_audience=data.get('target_audience'),
            user_id=user_id
        )

        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Generation job created successfully'
        })

    except Exception as e:
        print(f"[ERROR] Create generation job error: {e}")
        return jsonify({'error': 'Failed to create generation job', 'details': str(e)}), 500


@app.route('/api/generation/jobs/<job_id>', methods=['GET'])
def api_get_generation_job(job_id):
    """Get status and details of a generation job."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        from scripts.generation_service import GenerationService

        job_status = GenerationService.get_job_status(job_id)
        if not job_status:
            return jsonify({'error': 'Job not found'}), 404

        return jsonify(job_status)

    except Exception as e:
        print(f"[ERROR] Get generation job error: {e}")
        return jsonify({'error': 'Failed to get job status', 'details': str(e)}), 500


@app.route('/api/generation/jobs/<job_id>/continue', methods=['POST'])
def api_continue_generation_job(job_id):
    """Continue pipeline execution for a generation job."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        from scripts.generation_service import GenerationService

        data = request.get_json() or {}
        model = data.get('model', 'claude-sonnet')

        result = GenerationService.continue_pipeline(job_id, model)
        return jsonify(result)

    except Exception as e:
        print(f"[ERROR] Continue generation job error: {e}")
        return jsonify({'error': 'Failed to continue job', 'details': str(e)}), 500


@app.route('/api/generation/jobs/<job_id>/content', methods=['GET'])
def api_get_generation_content(job_id):
    """Get the final assembled content for a completed job."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        from scripts.generation_service import GenerationService

        content = GenerationService.get_completed_content(job_id)
        if not content:
            return jsonify({'error': 'Job not found or not completed'}), 404

        return jsonify(content)

    except Exception as e:
        print(f"[ERROR] Get generation content error: {e}")
        return jsonify({'error': 'Failed to get content', 'details': str(e)}), 500


@app.route('/api/generation/jobs', methods=['GET'])
def api_list_generation_jobs():
    """List all generation jobs for the current user."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session['user_id']

    try:
        from scripts.generation_service import GenerationService

        jobs = GenerationService.list_user_jobs(user_id)
        return jsonify({
            'jobs': jobs,
            'total_jobs': len(jobs)
        })

    except Exception as e:
        print(f"[ERROR] List generation jobs error: {e}")
        return jsonify({'error': 'Failed to list jobs', 'details': str(e)}), 500


@app.route('/api/models', methods=['GET'])
def api_get_models():
    """Get available AI models for chat."""
    models = [
        {
            'id': 'claude-sonnet',
            'name': 'Claude Sonnet 4',
            'description': 'Anthropic\'s Claude Sonnet 4 - Balanced performance and capability',
            'provider': 'anthropic',
            'capabilities': ['chat', 'analysis', 'coding', 'creative'],
            'context_window': 200000,
            'is_recommended': True
        },
        {
            'id': 'claude-opus',
            'name': 'Claude Opus 4',
            'description': 'Anthropic\'s most capable model - Best for complex reasoning',
            'provider': 'anthropic',
            'capabilities': ['chat', 'analysis', 'coding', 'creative', 'research'],
            'context_window': 200000,
            'is_recommended': False
        },
        {
            'id': 'claude-haiku',
            'name': 'Claude Haiku 3.5',
            'description': 'Fast and efficient Claude model - Good for quick responses',
            'provider': 'anthropic',
            'capabilities': ['chat', 'analysis', 'coding'],
            'context_window': 200000,
            'is_recommended': False
        },
        {
            'id': 'gpt-4o',
            'name': 'GPT-4 Omni',
            'description': 'OpenAI\'s flagship model - Excellent for general tasks',
            'provider': 'openai',
            'capabilities': ['chat', 'analysis', 'coding', 'creative', 'vision'],
            'context_window': 128000,
            'is_recommended': True
        },
        {
            'id': 'gpt-4-turbo',
            'name': 'GPT-4 Turbo',
            'description': 'OpenAI\'s optimized model - Fast with large context',
            'provider': 'openai',
            'capabilities': ['chat', 'analysis', 'coding', 'creative'],
            'context_window': 128000,
            'is_recommended': False
        },
        {
            'id': 'gpt-3.5-turbo',
            'name': 'GPT-3.5 Turbo',
            'description': 'OpenAI\'s efficient model - Great for everyday use',
            'provider': 'openai',
            'capabilities': ['chat', 'analysis'],
            'context_window': 16000,
            'is_recommended': False
        }
    ]

    return jsonify({
        'models': models,
        'default': 'gpt-4o'
    })


# ==========================================
# EXTERNAL CONTENT LIBRARY ENDPOINTS
# ==========================================

@app.route('/api/external-content', methods=['GET'])
def api_list_external_content():
    """List external content with search and filters."""
    search_query = request.args.get('q', '').strip()
    content_type = request.args.get('type', '').strip()

    try:
        items = ExternalContentService.list_content(
            search_query=search_query,
            content_type=content_type
        )
        return jsonify(items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/external-content', methods=['POST'])
def api_create_external_content():
    """Create new external content entry."""
    data = request.json

    if not data.get('title') or not data.get('content_type'):
        return jsonify({'error': 'Title and content_type are required'}), 400

    try:
        user_id = session.get('user_id')
        result = ExternalContentService.create_content(data, user_id)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/external-content/<content_id>', methods=['GET'])
def api_get_external_content(content_id):
    """Get single external content item with full details."""
    try:
        content = ExternalContentService.get_content_with_urls(content_id)
        return jsonify(content)
    except ValueError:
        return jsonify({'error': 'Invalid content ID'}), 400
    except FileNotFoundError:
        return jsonify({'error': 'Content not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/external-content/<content_id>', methods=['PUT'])
def api_update_external_content(content_id):
    """Update external content metadata."""
    data = request.json

    try:
        result = ExternalContentService.update_content(content_id, data)
        return jsonify(result)
    except ValueError:
        return jsonify({'error': 'Invalid content ID'}), 400
    except FileNotFoundError:
        return jsonify({'error': 'Content not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/external-content/<content_id>', methods=['DELETE'])
def api_delete_external_content(content_id):
    """Delete external content and associated files."""
    try:
        result = ExternalContentService.delete_content(content_id)
        return jsonify(result)
    except ValueError:
        return jsonify({'error': 'Invalid content ID'}), 400
    except FileNotFoundError:
        return jsonify({'error': 'Content not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/external-content/<content_id>/segments', methods=['GET'])
def api_get_external_content_segments(content_id):
    """Get all segments for external content."""
    try:
        segments = ExternalContentService.get_content_segments(content_id)
        return jsonify(segments)
    except ValueError:
        return jsonify({'error': 'Invalid content ID'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/external-content/upload', methods=['POST'])
def api_upload_external_content():
    """Upload external content file (PDF, video, etc.)."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Get metadata from form
    metadata = {
        'title': request.form.get('title', file.filename),
        'content_type': request.form.get('content_type', 'other'),
        'description': request.form.get('description', ''),
        'author': request.form.get('author', '')
    }

    try:
        user_id = session.get('user_id')
        result = ExternalContentService.upload_file(file, metadata, user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


# Helper functions for email sending
def send_verification_email(email, name, token):
    """Send email verification email."""
    try:
        # TODO: Implement actual email sending
        # For now, just log the verification link
        verification_url = f"https://maurinventuresinternal.com/verify-email?token={token}"
        print(f"VERIFICATION EMAIL for {email}: {verification_url}")
        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False


# DISABLED: Flask app execution (CLI-only mode)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
