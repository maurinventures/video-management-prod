"""
AI Service

Handles all AI/LLM operations including script generation with Claude/OpenAI,
copy generation, conversation management, speaker identification, and metadata extraction.
"""

import os
import re
import json
import time
from uuid import UUID
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Import AI clients
from openai import OpenAI
import anthropic

# Import database models and session
try:
    from scripts.db import DatabaseSession, Video, Transcript, TranscriptSegment, AILog, Persona, SocialPost, ScriptFeedback, Conversation
    from scripts.config_loader import get_config
    from .video_service import VideoService
except ImportError:
    from ..scripts.db import DatabaseSession, Video, Transcript, TranscriptSegment, AILog, Persona, SocialPost, ScriptFeedback, Conversation
    from ..scripts.config_loader import get_config
    from .video_service import VideoService


class AIService:
    """Service for managing all AI/LLM operations."""

    # Model mapping for API calls
    MODEL_MAP = {
        # Claude models
        "claude-sonnet": "claude-sonnet-4-20250514",
        "claude-opus": "claude-opus-4-0-20250514",
        "claude-haiku": "claude-3-5-haiku-20241022",
        # OpenAI models
        "gpt-4o": "gpt-4o",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
    }

    @staticmethod
    def get_openai_client():
        """Get OpenAI client."""
        config = get_config()
        api_key = config.secrets.get("openai", {}).get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        return OpenAI(api_key=api_key)

    @staticmethod
    def get_anthropic_client():
        """Get Anthropic client."""
        config = get_config()
        api_key = config.secrets.get("anthropic", {}).get("api_key")
        if not api_key:
            raise ValueError("Anthropic API key not configured. Add your key to config/credentials.yaml")
        return anthropic.Anthropic(api_key=api_key)

    @staticmethod
    def log_ai_call(
        request_type: str,
        model: str,
        prompt: str = None,
        context_summary: str = None,
        response: str = None,
        clips_generated: int = 0,
        response_json: dict = None,
        success: bool = True,
        error_message: str = None,
        latency_ms: float = None,
        input_tokens: int = None,
        output_tokens: int = None,
        user_id: str = None,
        conversation_id: str = None
    ):
        """Log an AI API call for quality monitoring."""
        try:
            with DatabaseSession() as db_session:
                log_entry = AILog(
                    request_type=request_type,
                    model=model,
                    prompt=prompt[:10000] if prompt else None,  # Truncate very long prompts
                    context_summary=context_summary[:5000] if context_summary else None,
                    response=response[:50000] if response else None,  # Keep full response for quality review
                    clips_generated=clips_generated,
                    response_json=response_json,
                    success=1 if success else 0,
                    error_message=error_message,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    user_id=UUID(user_id) if user_id else None,
                    conversation_id=UUID(conversation_id) if conversation_id else None
                )
                db_session.add(log_entry)
                db_session.commit()
                print(f"[AI_LOG] {request_type} | model={model} | success={success} | latency={latency_ms:.0f}ms | clips={clips_generated}")
        except Exception as e:
            print(f"[AI_LOG ERROR] Failed to log AI call: {e}")

    @staticmethod
    def reconstruct_script_with_verified_clips(ai_response: str, verified_clips: list) -> str:
        """Rebuild the script using verified clip texts so script matches actual clips."""

        # Extract title from AI response
        title_match = re.search(r'\*\*\[(.*?)\]\*\*', ai_response)
        title = title_match.group(1) if title_match else "Video Script"

        # Extract all RECORD sections (narration to record)
        records = re.findall(r'\[RECORD:\s*(.*?)\]', ai_response)
        # Also try old format
        if not records:
            records = re.findall(r'\[NARRATE:\s*(.*?)\]', ai_response)

        # Build new script with verified clips
        script = f"**[{title}]**\n\n"

        record_idx = 0

        # Add opening narration if exists
        if records and record_idx < len(records):
            script += f"[RECORD: {records[record_idx]}]\n\n"
            record_idx += 1

        # Add each verified clip with narration bridges
        for i, clip in enumerate(verified_clips):
            # Use the ACTUAL verified text from the database, cleaned up
            raw_text = clip.get('text', '').strip()
            clip_text = VideoService.clean_clip_text(raw_text)

            # Store the cleaned text back for display consistency
            clip['display_text'] = clip_text

            # Get speaker info if available
            speaker = clip.get('speaker', '')
            if speaker and speaker != 'Unknown':
                script += f'[VIDEO: "{clip_text}" — {speaker}]\n\n'
            else:
                script += f'[VIDEO: "{clip_text}"]\n\n'

            # Add transition narration if available
            if record_idx < len(records):
                script += f"[RECORD: {records[record_idx]}]\n\n"
                record_idx += 1

        return script

    @staticmethod
    def generate_script_with_ai(
        user_message: str,
        transcript_context: list,
        conversation_history: list,
        model: str = "gpt-4o",
        exclude_clips: list = None,
        user_id: str = None,
        conversation_id: str = None
    ):
        """Generate a script using AI with verified transcript data."""

        # Build summary of available content
        speakers = set()
        events = set()
        years = set()
        for t in transcript_context:
            speakers.add(t.get('speaker', 'Unknown'))
            events.add(t.get('event_name', 'Unknown'))
            if t.get('year'):
                years.add(t['year'])

        summary = f"""AVAILABLE CONTENT SUMMARY:
- Speakers: {', '.join(sorted(speakers))}
- Events: {', '.join(sorted(events)[:10])}{'...' if len(events) > 10 else ''}
- Years: {min(years) if years else 'N/A'} to {max(years) if years else 'N/A'}
- Total clips available: {len(transcript_context)}
"""

        # Fetch good AND bad examples from database (few-shot learning)
        examples_text = ""
        try:
            with DatabaseSession() as db_session:
                # Good examples - learn from these
                good_scripts = db_session.query(ScriptFeedback).filter(
                    ScriptFeedback.rating == 1
                ).order_by(ScriptFeedback.created_at.desc()).limit(2).all()

                if good_scripts:
                    examples_text = "\n\nHERE ARE EXAMPLES OF GOOD SCRIPTS (learn from this style):\n"
                    for i, ex in enumerate(good_scripts, 1):
                        script_clean = ex.script.split('```json')[0].strip() if '```json' in ex.script else ex.script
                        examples_text += f"\n--- GOOD EXAMPLE {i} ---\nUser asked: \"{ex.query}\"\nGood response:\n{script_clean[:1500]}...\n"

                # Bad examples - AVOID these mistakes
                bad_scripts = db_session.query(ScriptFeedback).filter(
                    ScriptFeedback.rating == -1
                ).order_by(ScriptFeedback.created_at.desc()).limit(2).all()

                if bad_scripts:
                    examples_text += "\n\nHERE ARE EXAMPLES OF BAD SCRIPTS (DO NOT make these mistakes):\n"
                    for i, ex in enumerate(bad_scripts, 1):
                        script_clean = ex.script.split('```json')[0].strip() if '```json' in ex.script else ex.script
                        examples_text += f"\n--- BAD EXAMPLE {i} (AVOID THIS) ---\nUser asked: \"{ex.query}\"\nBad response (DO NOT DO THIS):\n{script_clean[:1000]}...\n"
        except Exception as e:
            print(f"[DEBUG] Could not fetch examples: {e}")

        # Build exclusion list from previously used clips
        exclude_text = ""
        if exclude_clips:
            exclude_text = "\n\nCLIPS TO EXCLUDE (DO NOT USE THESE - already used in previous scripts):\n"
            for clip in exclude_clips:
                exclude_text += f"- video_id: {clip.get('video_id')} | {clip.get('start_time', 0):.1f}s-{clip.get('end_time', 0):.1f}s | \"{clip.get('text', '')[:80]}...\"\n"
            exclude_text += "\nYou MUST use DIFFERENT clips than the ones listed above.\n"

        # Build context from transcripts
        # GPT-4o has 30k token limit, Claude has 200k - adjust accordingly
        is_claude = model.startswith("claude")
        max_segments = 300 if is_claude else 80  # Claude can handle more context
        max_chars = 100000 if is_claude else 20000  # Rough char limits

        context_text = ""
        seen_passages = set()
        total_chars = 0

        for t in transcript_context[:max_segments]:
            passage_key = (t['video_id'], round(t['start'], 0))
            if passage_key in seen_passages:
                continue
            seen_passages.add(passage_key)

            text = t["text"].strip()

            # Only skip truly unusable segments (very short)
            if len(text) < 15:
                continue

            # Check if we'd exceed character limit
            entry = f"[{t.get('event_date', 'Unknown')} | {t.get('speaker', 'Unknown')}]\n"
            entry += f"Video: {t['video_title']} | {t['start']:.1f}s-{t['end']:.1f}s | ID:{t['video_id']}\n"
            entry += f'"{text}"\n\n'

            if total_chars + len(entry) > max_chars:
                break

            context_text += entry
            total_chars += len(entry)

        system_prompt = f"""You are a video script creator. You have access to a database of transcript segments below.

{summary}

IMPORTANT RULES:
1. ALWAYS create a script using the transcript data provided below - NEVER say you don't have access or ask for more data
2. Copy video_id and timestamps EXACTLY from the data below
3. Look for COMPLETE THOUGHTS - prefer quotes that start with capital letters and end with periods
4. If a segment starts mid-sentence (with "and", "but", lowercase), look for a better starting point nearby
5. NEVER USE THE SAME CLIP TWICE - each video_id + timestamp combination must be unique in your script. No duplicates!
6. If user requests a SPECIFIC CLIP as the first clip (e.g., "The first clip should be..."), you MUST use that exact clip first. Search for it in the transcript data and use it verbatim.
7. Mix clips from DIFFERENT recording sessions/videos when possible - avoid using consecutive clips from the same video unless necessary

CRITICAL - [RECORD] NARRATION STYLE:
- Write ALL [RECORD] sections in FIRST PERSON as if the speaker (e.g. Dan Goldin) is narrating their own story
- Use "I", "my", "we" - NOT "he", "his", "Goldin said"
- Example BAD: "Dan Goldin developed a philosophy about caterpillars..."
- Example GOOD: "I developed a philosophy about spotting caterpillars..."
- The [RECORD] should sound like the speaker reflecting on their own experiences

CRITICAL - SMOOTH TRANSITIONS:
- Each [RECORD] must lead DIRECTLY into what the [VIDEO] clip will say
- Read the FIRST WORDS of the video clip and make the [RECORD] set them up
- Example: If video starts "The caterpillars are ugly..." then [RECORD] should end with something like "...and I learned to see their true nature:"
- NEVER write a [RECORD] that has no connection to the video clip that follows

OUTPUT FORMAT:

**[Title]**

[RECORD: First-person opening - "I..." or "When I..."]

[VIDEO: "Complete quote from transcript" | video_id | start-end]

[RECORD: First-person bridge that leads into next clip]

[VIDEO: "Complete quote from transcript" | video_id | start-end]

[RECORD: First-person closing reflection]

After script, provide JSON:
```json
{{"title": "...", "clips": [{{"video_id": "ID", "video_title": "TITLE", "start_time": 0.0, "end_time": 0.0, "text": "TEXT"}}]}}
```

FINDING GOOD CLIPS:
- Look for segments that express complete ideas
- Prefer quotes that would make sense to someone who hasn't seen the full video
- If explaining a concept (like "frogs and caterpillars"), find the segments where it's DEFINED, not just mentioned
- Combine multiple short segments if they form a complete thought
{examples_text}
{exclude_text}
---

TRANSCRIPT DATA:
""" + context_text

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 10 messages)
        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_message})

        # Log the full prompt for debugging
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'ai_prompts.log')
        with open(log_file, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"TIMESTAMP: {datetime.utcnow().isoformat()}\n")
            f.write(f"MODEL: {model}\n")
            f.write(f"USER MESSAGE: {user_message}\n")
            f.write(f"EXCLUDE CLIPS: {exclude_clips}\n")
            f.write(f"\n--- SYSTEM PROMPT (first 3000 chars) ---\n{system_prompt[:3000]}\n")
            f.write(f"\n--- FULL SYSTEM PROMPT LENGTH: {len(system_prompt)} chars ---\n")

        # Start timing for logging
        start_time = time.time()
        input_tokens = None
        output_tokens = None

        try:
            # Determine which provider to use
            actual_model = AIService.MODEL_MAP.get(model, model)
            is_claude = model.startswith("claude")

            if is_claude:
                # Use Anthropic Claude
                client = AIService.get_anthropic_client()
                # Claude uses system prompt differently
                response = client.messages.create(
                    model=actual_model,
                    max_tokens=4000,
                    system=system_prompt,
                    messages=[{"role": m["role"], "content": m["content"]} for m in messages[1:]]  # Skip system message
                )
                assistant_message = response.content[0].text
                # Extract token usage from Claude response
                if hasattr(response, 'usage'):
                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
            else:
                # Use OpenAI
                client = AIService.get_openai_client()
                response = client.chat.completions.create(
                    model=actual_model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2000,
                )
                assistant_message = response.choices[0].message.content
                # Extract token usage from OpenAI response
                if hasattr(response, 'usage'):
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens

            # Log the AI response
            with open(log_file, 'a') as f:
                f.write(f"\n--- AI RESPONSE ---\n{assistant_message}\n")

            # Try to extract JSON clips from response
            clips = []
            if "```json" in assistant_message:
                try:
                    json_str = assistant_message.split("```json")[1].split("```")[0]
                    data = json.loads(json_str)
                    clips = data.get("clips", [])
                except:
                    pass

            # Log extracted clips
            with open(log_file, 'a') as f:
                f.write(f"\n--- EXTRACTED CLIPS ({len(clips)}) ---\n")
                for i, c in enumerate(clips):
                    f.write(f"  {i+1}. video_id={c.get('video_id')} | {c.get('start_time')}-{c.get('end_time')} | {c.get('text', '')[:60]}...\n")

            # Validate clips against database
            if clips:
                validated_clips = VideoService.validate_clips_against_database(clips)
            else:
                validated_clips = []

            # DEDUPLICATE: Remove clips that overlap with each other (same video, overlapping times)
            if len(validated_clips) > 1:
                deduped_clips = []
                for clip in validated_clips:
                    is_duplicate = False
                    for existing in deduped_clips:
                        # Same video?
                        if clip.get('video_id') == existing.get('video_id'):
                            # Check for time overlap
                            clip_start = clip.get('start_time', 0)
                            clip_end = clip.get('end_time', 0)
                            exist_start = existing.get('start_time', 0)
                            exist_end = existing.get('end_time', 0)
                            # Overlap if: clip starts before existing ends AND clip ends after existing starts
                            if clip_start < exist_end + 5 and clip_end > exist_start - 5:  # 5s tolerance
                                is_duplicate = True
                                with open(log_file, 'a') as f:
                                    f.write(f"  DUPLICATE REMOVED: {clip.get('video_id')} {clip_start}-{clip_end} overlaps with {exist_start}-{exist_end}\n")
                                break
                    if not is_duplicate:
                        deduped_clips.append(clip)
                validated_clips = deduped_clips

            # Log validated clips
            with open(log_file, 'a') as f:
                f.write(f"\n--- VALIDATED CLIPS ({len(validated_clips)}) ---\n")
                for i, c in enumerate(validated_clips):
                    f.write(f"  {i+1}. video_id={c.get('video_id')} | {c.get('start_time')}-{c.get('end_time')} | {c.get('text', '')[:60]}...\n")
                f.write(f"\n{'='*80}\n")

            # RECONSTRUCT the script using verified clip texts
            # This ensures the displayed script matches the actual clips
            if validated_clips:
                reconstructed = AIService.reconstruct_script_with_verified_clips(assistant_message, validated_clips)
                # Update clip texts to match what's shown in the script
                for clip in validated_clips:
                    if 'display_text' in clip:
                        clip['text'] = clip['display_text']
            else:
                reconstructed = assistant_message

            # Log successful AI call to database
            latency_ms = (time.time() - start_time) * 1000
            AIService.log_ai_call(
                request_type="chat",
                model=actual_model,
                prompt=user_message,
                context_summary=f"Speakers: {', '.join(sorted(speakers)[:5])}; Events: {', '.join(sorted(events)[:3])}; {len(transcript_context)} segments",
                response=assistant_message,
                clips_generated=len(validated_clips),
                response_json={"clips": validated_clips} if validated_clips else None,
                success=True,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                user_id=user_id,
                conversation_id=conversation_id
            )

            return {
                "message": reconstructed,
                "clips": validated_clips,
                "has_script": len(validated_clips) > 0
            }

        except Exception as e:
            # Log failed AI call to database
            latency_ms = (time.time() - start_time) * 1000
            AIService.log_ai_call(
                request_type="chat",
                model=AIService.MODEL_MAP.get(model, model),
                prompt=user_message,
                context_summary=f"{len(transcript_context)} segments",
                success=False,
                error_message=str(e),
                latency_ms=latency_ms,
                user_id=user_id,
                conversation_id=conversation_id
            )

            return {
                "message": f"Error generating response: {str(e)}",
                "clips": [],
                "has_script": False,
                "error": True
            }

    @staticmethod
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

    @staticmethod
    def generate_general_response(
        user_message: str,
        conversation_history: list,
        model: str = "claude-sonnet",
        user_id: str = None,
        conversation_id: str = None
    ):
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
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

            # Log the AI call
            latency_ms = (time.time() - start_time) * 1000
            AIService.log_ai_call(
                request_type="general_chat",
                model=api_model,
                prompt=user_message,
                context_summary=f"{len(messages)} messages",
                response=response_text,
                success=True,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                user_id=user_id,
                conversation_id=conversation_id
            )

            return {
                'message': response_text,
                'model': model
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            AIService.log_ai_call(
                request_type="general_chat",
                model=model,
                prompt=user_message,
                context_summary=f"{len(messages)} messages",
                success=False,
                error_message=str(e),
                latency_ms=latency_ms,
                user_id=user_id,
                conversation_id=conversation_id
            )

            return {
                'message': f'Sorry, I encountered an error: {str(e)}',
                'model': model,
                'error': True
            }

    @staticmethod
    def generate_conversation_title(conversation_id: str, first_message: str) -> Tuple[bool, str]:
        """Generate a title for a conversation using AI based on first message."""
        try:
            # Generate title using Claude (fast, cheap)
            client = anthropic.Anthropic()
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
            return True, title
        except Exception as e:
            # Fallback to truncated message
            title = first_message[:50] + ('...' if len(first_message) > 50 else '')
            return False, title

    @staticmethod
    def regenerate_record_text(
        original_text: str,
        feedback: str,
        conversation_history: list = None,
        model: str = 'claude-sonnet'
    ) -> Dict[str, Any]:
        """Regenerate a narration/record section based on feedback."""

        if not original_text:
            return {'success': False, 'error': 'Original text required'}

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
                output_tokens=response.usage.output_tokens if hasattr(response, 'usage') else None
            )

            return {
                'success': True,
                'new_text': new_text
            }

        except Exception as e:
            # Log failed AI call
            latency_ms = (time.time() - start_time) * 1000
            AIService.log_ai_call(
                request_type="regenerate_record",
                model=actual_model,
                prompt=regenerate_prompt,
                success=False,
                error_message=str(e),
                latency_ms=latency_ms
            )

            return {
                'success': False,
                'error': f"Error regenerating text: {str(e)}"
            }

    @staticmethod
    def identify_speakers_in_transcript(
        transcript_id: str,
        known_speakers: List[str] = None
    ) -> Dict[str, Any]:
        """Use AI to identify and label speakers in a transcript."""

        if known_speakers is None:
            known_speakers = []

        try:
            with DatabaseSession() as db_session:
                transcript = db_session.query(Transcript).filter(
                    Transcript.id == UUID(transcript_id)
                ).first()

                if not transcript:
                    return {'success': False, 'error': 'Transcript not found'}

                # Get video info
                video = db_session.query(Video).filter(Video.id == transcript.video_id).first()
                video_speaker = video.speaker if video else None

                # Get segments
                segments = db_session.query(TranscriptSegment).filter(
                    TranscriptSegment.transcript_id == transcript.id
                ).order_by(TranscriptSegment.start_time).limit(100).all()

                if not segments:
                    return {'success': False, 'error': 'No segments found'}

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
    {{
      "timestamp": "2:15",
      "from_speaker": "Speaker 1",
      "to_speaker": "Speaker 2",
      "confidence": "high"
    }}
  ]
}}"""

                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )

                try:
                    ai_result = json.loads(response.content[0].text)
                    return {
                        'success': True,
                        'speakers': ai_result.get('speakers', []),
                        'speaker_changes': ai_result.get('speaker_changes', []),
                        'raw_response': response.content[0].text
                    }
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'error': 'Could not parse AI response',
                        'raw_response': response.content[0].text
                    }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def autofill_video_metadata(video_id: str) -> Dict[str, Any]:
        """Use AI to auto-fill video metadata from transcript."""
        try:
            with DatabaseSession() as db_session:
                video = db_session.query(Video).filter(Video.id == UUID(video_id)).first()
                if not video:
                    return {'success': False, 'error': 'Video not found'}

                # Get transcript
                transcript = db_session.query(Transcript).filter(
                    Transcript.video_id == video.id,
                    Transcript.status == 'completed'
                ).first()

                if not transcript:
                    return {'success': False, 'error': 'No transcript available for this video'}

                # Get transcript segments
                segments = db_session.query(TranscriptSegment).filter(
                    TranscriptSegment.transcript_id == transcript.id
                ).order_by(TranscriptSegment.start_time).all()

                if not segments:
                    return {'success': False, 'error': 'Transcript has no segments'}

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

                try:
                    metadata = json.loads(response.content[0].text)
                    return {
                        'success': True,
                        'metadata': metadata,
                        'raw_response': response.content[0].text
                    }
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'error': 'Could not parse AI response',
                        'raw_response': response.content[0].text
                    }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def detect_copy_intent(message: str) -> dict:
        """Detect if user wants copy generation vs video scripts.

        Returns dict with is_copy, persona_name, platform, and topic.
        """
        message_lower = message.lower()
        is_copy = False
        persona_name = None
        detected_platform = None

        # Platform detection
        platforms = {
            'linkedin': ['linkedin', 'professional network'],
            'x': ['twitter', 'x.com', 'tweet'],
            'email': ['email', 'message', 'send to'],
            'blog': ['blog', 'article', 'post']
        }

        for platform, keywords in platforms.items():
            if any(kw in message_lower for kw in keywords):
                detected_platform = platform
                is_copy = True
                break

        # Copy action indicators
        copy_actions = ['write', 'create', 'draft', 'compose', 'generate']
        copy_types = ['post', 'tweet', 'email', 'message', 'copy', 'content', 'caption']

        # Check for copy action + type combinations
        for action in copy_actions:
            for ctype in copy_types:
                if action in message_lower and ctype in message_lower:
                    is_copy = True
                    break

        # Persona detection (check if any persona name is mentioned)
        with DatabaseSession() as db_session:
            personas = db_session.query(Persona).filter(Persona.is_active == 1).all()

            for p in personas:
                # Check full name first
                if p.name.lower() in message_lower:
                    persona_name = p.name
                    break
                # Check first name only if it's longer than 2 chars
                first_name = p.name.split()[0].lower()
                if len(first_name) > 2 and first_name in message_lower:
                    persona_name = p.name
                    break

        # If persona mentioned with "voice", "style", "as", it's likely copy
        if persona_name:
            voice_indicators = ["voice", "style", "as", "for", "like"]
            for ind in voice_indicators:
                if ind in message_lower:
                    is_copy = True
                    break

        return {
            'is_copy': is_copy,
            'persona_name': persona_name,
            'platform': detected_platform,
            'topic': message  # Will be refined by the AI
        }

    @staticmethod
    def detect_script_intent(message: str) -> bool:
        """Detect if user wants video script generation.

        Returns True if message indicates they want to create a video script.
        """
        message_lower = message.lower()

        # Script action indicators
        script_actions = ['create', 'make', 'generate', 'write', 'draft', 'build', 'compile']
        script_types = ['script', 'video', 'compilation', 'edit', 'clip', 'footage']

        # Check for script action + type combinations
        for action in script_actions:
            for stype in script_types:
                if action in message_lower and stype in message_lower:
                    return True

        # Check for explicit script requests
        script_phrases = [
            'video script', 'create a script', 'make a video',
            'compile clips', 'video compilation', 'script about',
            'using clips', 'from the transcripts', 'from the videos'
        ]

        for phrase in script_phrases:
            if phrase in message_lower:
                return True

        return False