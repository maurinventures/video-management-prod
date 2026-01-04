# Contributing to MV Internal

Welcome to the MV Internal video management platform! This guide will help you get set up for local development.

## Prerequisites

- Python 3.8+
- PostgreSQL client (for database access)
- AWS CLI (optional, for S3 operations)
- Git
- OpenSSL (for decrypting credentials)

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/maurinventures/video-management-prod.git
cd video-management-prod
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Secrets

Credentials are stored encrypted. To decrypt:

```bash
openssl aes-256-cbc -d -pbkdf2 -in config/credentials.yaml.enc -out config/credentials.yaml
# Password: Ask team lead or check 1Password
```

The decrypted `credentials.yaml` contains:

```yaml
aws:
  access_key_id: YOUR_AWS_ACCESS_KEY_ID
  secret_access_key: YOUR_AWS_SECRET_ACCESS_KEY

rds:
  host: YOUR_RDS_ENDPOINT.us-east-1.rds.amazonaws.com
  username: YOUR_DB_USERNAME
  password: YOUR_DB_PASSWORD

ec2:
  key_path: ~/Documents/keys/per_aspera/per-aspera-key.pem
  instance_id: YOUR_EC2_INSTANCE_ID
  public_ip: YOUR_EC2_PUBLIC_IP

# API Keys (OpenAI, Anthropic, Notion)
```

**Important:** Never commit decrypted `credentials.yaml` to git (it's in `.gitignore`).

To re-encrypt after making changes:
```bash
openssl aes-256-cbc -salt -pbkdf2 -in config/credentials.yaml -out config/credentials.yaml.enc
```

Contact the project owner to get the encryption password.

### 4. Run Locally

```bash
# Start the Flask development server
cd web
python app.py

# Or use gunicorn (production-like)
gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 120 web.app:app
```

The app will be available at: http://localhost:5000

## Project Structure

```
video-management-prod/
├── web/
│   ├── app.py              # Main Flask application (140KB)
│   └── templates/          # HTML templates (Jinja2)
├── scripts/
│   ├── db.py               # Database models (SQLAlchemy)
│   ├── config_loader.py    # Configuration loading
│   ├── import_otter_ai.py  # Otter AI transcript importer
│   ├── transcribe.py       # AWS Transcribe integration
│   ├── upload_video.py     # S3 video upload
│   ├── batch_upload.py     # Batch video processing
│   ├── run_batch_upload.py # Batch upload runner script
│   ├── run_batch_transcribe.py # Batch transcription runner
│   ├── clip_video.py       # Video clipping functionality
│   ├── compile_video.py    # Video compilation
│   ├── generate_thumbnails.py  # Thumbnail generation
│   ├── storylines.py       # Storyline management
│   ├── main.py             # CLI entry point
│   ├── aws_commands.sh     # AWS CLI helper commands
│   └── setup_database.sql  # Database schema setup
├── config/
│   ├── settings.yaml       # App settings (committed)
│   ├── credentials.yaml.enc    # Encrypted credentials
│   └── credentials.yaml.template  # Credential template
├── migrations/             # SQL migration files (004-009)
├── requirements.txt        # Python dependencies
├── INFRASTRUCTURE.md       # Server/deployment docs
└── GIT_CHEATSHEET.md       # Git workflow reference
```

## Key Features

- **Video Management**: Upload, transcode, clip, and compile video content
- **Transcription**: AWS Transcribe and local Whisper integration
- **AI Chat**: Generate video scripts using Claude/GPT with transcript context
- **Audio Clips**: Otter AI transcript imports with audio playback
- **Personas**: AI personas for copy generation (LinkedIn, X, etc.)
- **Documents & Social Posts**: Content generation with persona integration
- **AI Logs**: Track and review AI-generated content
- **2FA Authentication**: TOTP-based two-factor authentication with email verification
- **Collaboration**: Multi-user conversations with clip comments

## Development Workflow

### Making Changes

1. Pull latest changes:
   ```bash
   git pull origin main
   ```

2. Make your changes

3. Test locally

4. Commit and push:
   ```bash
   git add -A
   git commit -m "Description of changes"
   git push origin main
   ```

### Deploying to Production

The production server is on EC2 (54.198.253.138). The server has two directories:
- `~/video-management` - Git repo (source of truth)
- `~/mv-internal` - Production directory (served by nginx)

To deploy:

```bash
# SSH to EC2
ssh -i ~/Documents/keys/per_aspera/per-aspera-key.pem ec2-user@54.198.253.138

# Pull latest code
cd ~/video-management && git pull

# Sync to production directory
rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'

# Restart service
sudo systemctl restart mv-internal.service
```

Note: You need the SSH key and access to the EC2 server. Contact the project owner for access.
See `INFRASTRUCTURE.md` for detailed server documentation.

## Database

The app uses PostgreSQL (AWS RDS). Key tables:

**Core Content:**
- `videos` - Video metadata and S3 locations
- `transcripts` - Transcription jobs and status
- `transcript_segments` - Timestamped transcript text
- `clips` - Video clips extracted from source videos
- `compiled_videos` - Compiled video projects
- `compiled_video_clips` - Clips in compiled videos

**Audio:**
- `audio_recordings` - Otter AI audio imports
- `audio_segments` - Audio transcript segments

**AI & Content:**
- `personas` - AI personas for content generation
- `documents` - Generated documents
- `social_posts` - Social media content
- `ai_logs` - AI generation history

**Users & Collaboration:**
- `users` - User accounts with 2FA and email verification
- `conversations` - Chat sessions
- `chat_messages` - Messages in conversations
- `chat_participants` - Conversation members
- `clip_comments` - Comments on clips

**System:**
- `processing_jobs` - Background job tracking
- `script_feedback` - User feedback on scripts
- `voice_avatars` - Voice profiles

### Running Migrations

Migrations are numbered (004-009). Run in order:

```bash
# Connect to database and run SQL
psql -h <host> -U <user> -d <database> -f scripts/setup_database.sql
psql -h <host> -U <user> -d <database> -f migrations/004_collaboration.sql
# ... continue with remaining migrations
```

## API Endpoints

**Videos:**
- `GET /api/videos/<video_id>` - Get video details
- `PUT /api/videos/<video_id>` - Update video metadata
- `GET /api/video-preview/<video_id>` - Stream video
- `GET /api/video-download/<video_id>` - Download video
- `GET /api/video-thumbnail/<video_id>` - Get thumbnail
- `POST /api/videos/<video_id>/autofill` - AI autofill metadata

**Clips:**
- `GET /api/clip-preview/<video_id>` - Preview clip
- `GET /api/clip-download/<video_id>` - Download clip
- `GET/POST /api/clips/<conv_id>/<clip_index>/comments` - Clip comments
- `POST /api/clips/<conv_id>/<clip_index>/regenerate` - Regenerate clip

**Audio:**
- `GET /api/audio-preview/<audio_id>` - Stream audio
- `GET /api/audio-clip/<audio_id>` - Get audio clip

**Transcripts:**
- `POST /api/transcript-segment/update` - Update segment
- `POST /api/transcripts/<id>/identify-speakers` - Speaker identification
- `PUT /api/segments/<segment_id>/speaker` - Update speaker

**AI Chat:**
- `POST /api/chat` - AI chat for script generation
- `POST /api/chat/create-video` - Create video from chat
- `POST /api/chat/export-script` - Export script

**Personas:**
- `GET/POST /api/personas` - List/create personas
- `PUT/DELETE /api/personas/<persona_id>` - Update/delete persona

**Conversations:**
- `GET/POST /api/conversations` - List/create conversations
- `GET/PUT/DELETE /api/conversations/<id>` - Manage conversation
- `GET/POST /api/conversations/<id>/participants` - Manage participants

**AI Logs:**
- `GET /api/ai-logs` - List AI logs
- `GET /api/ai-logs/<log_id>` - Get log details

## Environment Variables

Optional environment variables:

- `FLASK_SECRET_KEY` - Session encryption key
- `FLASK_ENV` - Set to `development` for debug mode

## Getting Help

- Check existing code for patterns and conventions
- Ask in the team chat for guidance
- Review recent commits for context

## Code Style

- Use clear, descriptive variable names
- Add docstrings to functions
- Keep functions focused and small
- Test changes locally before pushing
