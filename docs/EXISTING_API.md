# Existing API Documentation

**Project:** Internal Platform Flask Backend
**Source:** `web/app.py`
**Last Updated:** 2026-01-06

This document maps all existing Flask routes with their authentication requirements, request/response formats, and usage patterns.

---

## Authentication Patterns

The API uses **session-based authentication** with the following patterns:

- **Session Required**: Routes check `if 'user_id' not in session`
- **2FA Pending**: Some auth routes use `pending_2fa_user_id` in session
- **Admin Required**: Some routes check user permissions
- **Public**: No authentication required

**Error Responses:**
- `401`: `{'error': 'Not logged in'}` - Session expired/missing
- `400`: `{'error': 'Validation message'}` - Request validation failed
- `500`: `{'error': 'Server error message'}` - Server error

---

## Web Interface Routes

### Home & Navigation

#### `GET /`
- **Auth:** Session Required
- **Description:** Redirect to chat (requires login)
- **Response:** Redirect to `/login` or `/chat`

#### `GET /chat`
- **Auth:** Session Required
- **Description:** New chat welcome screen
- **Query Params:** `?project=<id>` (optional)
- **Response:** HTML template

#### `GET /chat/recents`
- **Auth:** Session Required
- **Description:** Chat list page showing recent conversations
- **Response:** HTML template

#### `GET /chat/<conversation_id>` (Commented out)
- **Auth:** Session Required
- **Description:** Specific conversation view
- **Response:** HTML template

#### `GET /projects`
- **Auth:** Session Required
- **Description:** Projects list page
- **Response:** HTML template

#### `GET /project/<project_id>`
- **Auth:** Session Required
- **Description:** Project detail page
- **Response:** HTML template or redirect to login

### Authentication Pages

#### `GET/POST /login`
- **Auth:** Public
- **Description:** User login page
- **Request Body (POST):**
  ```
  Content-Type: application/x-www-form-urlencoded
  email=user@example.com&password=secret123
  ```
- **Response (POST):**
  - Success: Redirect to 2FA or chat
  - Error: HTML template with error message

#### `GET/POST /verify-2fa` (Commented out)
- **Auth:** 2FA Pending (`pending_2fa_user_id` in session)
- **Description:** 2FA verification page
- **Request Body (POST):**
  ```
  Content-Type: application/x-www-form-urlencoded
  token=123456
  ```
- **Response:** HTML template or redirect

#### `GET/POST /setup-2fa` (Commented out)
- **Auth:** Session Required
- **Description:** 2FA setup page (mandatory for all users)
- **Response:** HTML template with QR code

#### `GET /logout`
- **Auth:** Session Required
- **Description:** User logout
- **Response:** Redirect to login, clears session

#### `GET/POST /register` (Commented out)
- **Auth:** Public
- **Description:** User registration with email verification
- **Request Body (POST):**
  ```
  Content-Type: application/x-www-form-urlencoded
  name=John Doe&email=user@example.com&password=secret123
  ```
- **Response:** HTML template or redirect

#### `GET /verify-email` (Commented out)
- **Auth:** Public
- **Description:** Email verification endpoint
- **Query Params:** `?token=<verification_token>`
- **Response:** Redirect to 2FA setup

#### `GET/POST /setup-2fa-required` (Commented out)
- **Auth:** 2FA Setup Required
- **Description:** Mandatory 2FA setup after email verification
- **Response:** HTML template

### Media Library Pages (Commented out)

#### `GET /videos`
- **Auth:** Session Required
- **Description:** List all videos page
- **Response:** HTML template

#### `GET /audio`
- **Auth:** Session Required
- **Description:** List all audio recordings page
- **Response:** HTML template

#### `GET /transcripts`
- **Auth:** Session Required
- **Description:** List all transcripts page
- **Response:** HTML template

#### `GET /transcripts/<transcript_id>`
- **Auth:** No Session Check (uses DatabaseSession)
- **Description:** View single transcript with segments
- **Response:** HTML template

#### `GET /transcripts/search`
- **Auth:** No Session Check
- **Description:** Search across transcripts
- **Query Params:** `?q=<search_term>`
- **Response:** HTML template

#### `GET /personas`
- **Auth:** Session Required
- **Description:** List all personas (voice profiles)
- **Response:** HTML template

#### `GET /personas/<persona_id>`
- **Auth:** No Session Check (uses DatabaseSession)
- **Description:** View and edit single persona
- **Response:** HTML template

### Admin & Monitoring

#### `GET /ai-logs`
- **Auth:** Session Required
- **Description:** View AI call logs for quality monitoring
- **Response:** HTML template

#### `GET/POST /admin/invite`
- **Auth:** Session Required + Admin Check
- **Description:** Admin page to invite new users
- **Request Body (POST):**
  ```
  Content-Type: application/x-www-form-urlencoded
  email=newuser@example.com&name=New User
  ```
- **Response:** HTML template

---

## API Routes

### AI Logs & Monitoring

#### `GET /api/ai-logs`
- **Auth:** Session Required
- **Description:** Fetch AI logs with filtering
- **Query Params:** `?start=<date>&end=<date>&model=<model_name>&user=<user_id>`
- **Response:**
  ```json
  {
    "logs": [
      {
        "id": "log_123",
        "timestamp": "2026-01-06T10:00:00Z",
        "model": "claude-sonnet",
        "tokens_used": 1500,
        "cost": 0.045,
        "user_id": "user_456",
        "endpoint": "/api/chat",
        "success": true,
        "error": null
      }
    ],
    "total": 25,
    "has_more": false
  }
  ```

#### `GET /api/ai-logs/<log_id>`
- **Auth:** Session Required
- **Description:** Get full details of specific AI log entry
- **Response:**
  ```json
  {
    "id": "log_123",
    "timestamp": "2026-01-06T10:00:00Z",
    "model": "claude-sonnet",
    "tokens_input": 800,
    "tokens_output": 700,
    "cost": 0.045,
    "user_id": "user_456",
    "conversation_id": "conv_789",
    "endpoint": "/api/chat",
    "request_data": {...},
    "response_data": {...},
    "success": true,
    "error": null
  }
  ```

### Personas Management

#### `GET /api/personas`
- **Auth:** No Session Check (uses DatabaseSession)
- **Description:** List all personas
- **Response:**
  ```json
  [
    {
      "id": "persona_123",
      "name": "Professional Writer",
      "description": "Formal business writing style",
      "tone": "professional",
      "style_notes": "Clear, concise, authoritative",
      "topics": ["business", "marketing"],
      "vocabulary": ["utilize", "optimize", "leverage"],
      "speaker_name_in_videos": "Sarah Johnson",
      "avatar_url": "https://...",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
  ```

#### `POST /api/personas`
- **Auth:** Session Required
- **Description:** Create new persona
- **Request Body:**
  ```json
  {
    "name": "Creative Writer",
    "description": "Casual, engaging style",
    "tone": "friendly",
    "style_notes": "Use storytelling elements",
    "topics": ["lifestyle", "entertainment"],
    "vocabulary": ["awesome", "amazing", "incredible"],
    "speaker_name_in_videos": "Mike Chen",
    "avatar_url": "https://example.com/avatar.jpg"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "id": "persona_456",
    "name": "Creative Writer"
  }
  ```
- **Errors:**
  - `400`: `{'error': 'Name is required'}`
  - `400`: `{'error': 'A persona with this name already exists'}`

#### `PUT /api/personas/<persona_id>`
- **Auth:** Session Required
- **Description:** Update existing persona
- **Request Body:** Same as POST (all fields optional)
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Persona not found'}`

#### `DELETE /api/personas/<persona_id>`
- **Auth:** Session Required
- **Description:** Soft delete a persona
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Persona not found'}`

### Projects Management

#### `GET /api/projects`
- **Auth:** Session Required
- **Description:** List all projects for current user
- **Query Params:** `?include_archived=true` (optional)
- **Response:**
  ```json
  {
    "projects": [
      {
        "id": "proj_123",
        "name": "Marketing Campaign",
        "description": "Q1 2026 product launch",
        "color": "#3B82F6",
        "is_archived": false,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-06T10:00:00Z",
        "conversation_count": 12
      }
    ]
  }
  ```

#### `POST /api/projects`
- **Auth:** Session Required
- **Description:** Create new project
- **Request Body:**
  ```json
  {
    "name": "New Project",
    "description": "Project description",
    "color": "#10B981"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "project": {
      "id": "proj_456",
      "name": "New Project",
      "description": "Project description",
      "color": "#10B981",
      "is_archived": false,
      "created_at": "2026-01-06T10:00:00Z"
    }
  }
  ```
- **Errors:**
  - `400`: `{'error': 'Project name is required'}`

#### `GET /api/projects/<project_id>`
- **Auth:** Session Required
- **Description:** Get project details with conversations
- **Response:**
  ```json
  {
    "project": {
      "id": "proj_123",
      "name": "Marketing Campaign",
      "description": "Q1 2026 product launch",
      "color": "#3B82F6",
      "is_archived": false,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-06T10:00:00Z"
    },
    "conversations": [
      {
        "id": "conv_789",
        "title": "Campaign Strategy",
        "created_at": "2026-01-06T09:00:00Z",
        "updated_at": "2026-01-06T10:00:00Z",
        "message_count": 8
      }
    ]
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Project not found'}`

#### `PUT /api/projects/<project_id>`
- **Auth:** Session Required
- **Description:** Update project
- **Request Body:**
  ```json
  {
    "name": "Updated Project Name",
    "description": "Updated description",
    "color": "#EF4444"
  }
  ```
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Project not found'}`

#### `DELETE /api/projects/<project_id>`
- **Auth:** Session Required
- **Description:** Delete project (soft delete by default)
- **Query Params:** `?permanent=true` (optional, for permanent deletion)
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Project not found'}`

### Conversations Management

#### `GET /api/conversations`
- **Auth:** Session Required
- **Description:** List all conversations for current user
- **Response:**
  ```json
  {
    "conversations": [
      {
        "id": "conv_123",
        "title": "Product Strategy Discussion",
        "video_id": "video_456",
        "project_id": "proj_789",
        "project": {
          "id": "proj_789",
          "name": "Marketing Campaign",
          "color": "#3B82F6"
        },
        "created_at": "2026-01-06T09:00:00Z",
        "updated_at": "2026-01-06T10:00:00Z",
        "message_count": 15
      }
    ]
  }
  ```

#### `POST /api/conversations`
- **Auth:** Session Required
- **Description:** Create new conversation
- **Request Body:**
  ```json
  {
    "title": "New Discussion",
    "project_id": "proj_123"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "conversation": {
      "id": "conv_456",
      "title": "New Discussion",
      "project_id": "proj_123",
      "created_at": "2026-01-06T10:00:00Z",
      "updated_at": "2026-01-06T10:00:00Z"
    }
  }
  ```

#### `GET /api/conversations/<conversation_id>`
- **Auth:** Session Required
- **Description:** Get conversation with all messages
- **Response:**
  ```json
  {
    "conversation": {
      "id": "conv_123",
      "title": "Product Strategy",
      "project_id": "proj_789",
      "created_at": "2026-01-06T09:00:00Z",
      "updated_at": "2026-01-06T10:00:00Z"
    },
    "messages": [
      {
        "id": "msg_456",
        "role": "user",
        "content": "What's our strategy for Q1?",
        "created_at": "2026-01-06T09:00:00Z"
      },
      {
        "id": "msg_789",
        "role": "assistant",
        "content": "Based on market analysis...",
        "model": "claude-sonnet",
        "tokens_used": 1200,
        "created_at": "2026-01-06T09:01:00Z"
      }
    ]
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Conversation not found'}`

#### `PUT /api/conversations/<conversation_id>`
- **Auth:** Session Required
- **Description:** Update conversation title
- **Request Body:**
  ```json
  {
    "title": "Updated Conversation Title"
  }
  ```
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Conversation not found'}`

#### `PUT /api/conversations/<conversation_id>/star`
- **Auth:** Session Required
- **Description:** Star or unstar conversation
- **Request Body:**
  ```json
  {
    "starred": true
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "starred": true
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Conversation not found'}`

#### `POST /api/conversations/<conversation_id>/generate-title`
- **Auth:** Session Required
- **Description:** Generate AI title based on first message
- **Response:**
  ```json
  {
    "success": true,
    "title": "AI-Generated Title Based on Content"
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Conversation not found'}`
  - `400`: `{'error': 'No messages found in conversation'}`

#### `DELETE /api/conversations/<conversation_id>`
- **Auth:** Session Required
- **Description:** Delete conversation
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Conversation not found'}`

#### `PUT /api/conversations/<conversation_id>/project`
- **Auth:** Session Required
- **Description:** Assign conversation to project
- **Request Body:**
  ```json
  {
    "project_id": "proj_123"
  }
  ```
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Conversation not found'}`
  - `404`: `{'error': 'Project not found'}`

### User Management

#### `GET /api/users/search`
- **Auth:** Session Required
- **Description:** Search users by name/email for collaboration
- **Query Params:** `?q=<search_term>`
- **Response:**
  ```json
  {
    "users": [
      {
        "id": "user_123",
        "name": "John Doe",
        "email": "john@example.com",
        "avatar_url": "https://..."
      }
    ]
  }
  ```

### Collaboration

#### `GET /api/conversations/<conversation_id>/participants`
- **Auth:** Session Required + Access Check
- **Description:** Get conversation participants
- **Response:**
  ```json
  {
    "owner": {
      "id": "user_123",
      "name": "Jane Doe",
      "email": "jane@example.com"
    },
    "participants": [
      {
        "user": {
          "id": "user_456",
          "name": "Bob Smith",
          "email": "bob@example.com"
        },
        "role": "editor",
        "invited_at": "2026-01-06T09:00:00Z",
        "accepted_at": "2026-01-06T09:30:00Z"
      }
    ]
  }
  ```
- **Errors:**
  - `403`: `{'error': 'Access denied'}`
  - `404`: `{'error': 'Conversation not found'}`

#### `POST /api/conversations/<conversation_id>/invite`
- **Auth:** Session Required (Owner Only)
- **Description:** Invite users to collaborate
- **Request Body:**
  ```json
  {
    "user_ids": ["user_456", "user_789"],
    "role": "editor"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "invited_count": 2
  }
  ```
- **Errors:**
  - `403`: `{'error': 'Only conversation owner can invite participants'}`

#### `POST /api/conversations/<conversation_id>/leave`
- **Auth:** Session Required (Participants Only)
- **Description:** Leave conversation (not for owners)
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:**
  - `403`: `{'error': 'Conversation owner cannot leave'}`

### File Attachments

#### `POST /api/conversations/<conversation_id>/attachments`
- **Auth:** Session Required
- **Description:** Upload file attachment
- **Request Body:** `multipart/form-data` with `file` field
- **Response:**
  ```json
  {
    "success": true,
    "attachment": {
      "id": "att_123",
      "filename": "document.pdf",
      "original_filename": "My Document.pdf",
      "file_size": 1024000,
      "mime_type": "application/pdf",
      "url": "https://s3.amazonaws.com/...",
      "uploaded_at": "2026-01-06T10:00:00Z"
    }
  }
  ```
- **Errors:**
  - `400`: `{'error': 'No file provided'}`
  - `400`: `{'error': 'File too large'}`
  - `413`: `{'error': 'File size exceeds limit'}`

### Chat & AI

#### `POST /api/chat`
- **Auth:** No explicit session check (handles internally)
- **Description:** Send chat message for script/copy generation
- **Request Body:**
  ```json
  {
    "message": "Create a marketing script about our new product",
    "conversation_id": "conv_123",
    "model": "claude-sonnet",
    "history": [
      {"role": "user", "content": "Previous message"},
      {"role": "assistant", "content": "Previous response"}
    ],
    "previous_clips": ["clip_id_1", "clip_id_2"]
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "conversation_id": "conv_123",
    "response": "Generated script content...",
    "clips": [
      {
        "title": "Product Introduction",
        "description": "Opening segment introducing the product",
        "video_id": "video_456",
        "start_time": 10.5,
        "end_time": 45.2,
        "transcript_text": "Welcome to our amazing product..."
      }
    ],
    "model_used": "claude-sonnet",
    "tokens_used": 1500,
    "cost": 0.045
  }
  ```
- **Errors:**
  - `400`: `{'error': 'No message provided'}`
  - `500`: `{'error': 'AI service error'}`

#### `POST /api/chat/create-video`
- **Auth:** No explicit session check
- **Description:** Create video clips from chat-generated script
- **Request Body:**
  ```json
  {
    "conversation_id": "conv_123",
    "script": "Full script content...",
    "clips": [
      {
        "title": "Intro Segment",
        "start_time": 0,
        "end_time": 30,
        "video_id": "video_456"
      }
    ]
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "video_url": "https://s3.amazonaws.com/generated-video.mp4",
    "clips_created": 3,
    "total_duration": 180
  }
  ```

#### `POST /api/chat/export-script`
- **Auth:** No explicit session check
- **Description:** Generate downloadable script file
- **Request Body:**
  ```json
  {
    "conversation_id": "conv_123",
    "format": "pdf"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "download_url": "https://s3.amazonaws.com/exports/script-123.pdf",
    "expires_at": "2026-01-07T10:00:00Z"
  }
  ```

### Script Feedback

#### `POST /api/script-feedback`
- **Auth:** No explicit session check
- **Description:** Save user feedback on generated script
- **Request Body:**
  ```json
  {
    "conversation_id": "conv_123",
    "script_content": "The script content being rated...",
    "feedback": "Great structure but needs more energy",
    "rating": 4
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "feedback_id": "fb_456"
  }
  ```

#### `GET /api/script-examples`
- **Auth:** No explicit session check
- **Description:** Get good script examples for few-shot learning
- **Response:**
  ```json
  {
    "examples": [
      {
        "title": "Product Launch Script",
        "content": "Script content...",
        "style": "professional",
        "rating": 4.8,
        "category": "marketing"
      }
    ]
  }
  ```

### Media Handling

#### `GET /api/video-preview/<video_id>`
- **Auth:** No explicit session check
- **Description:** Get presigned S3 URL for video preview
- **Response:**
  ```json
  {
    "success": true,
    "url": "https://s3.amazonaws.com/videos/preview-123.mp4?X-Amz-Signature=...",
    "expires_in": 3600,
    "content_type": "video/mp4"
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Video not found'}`

#### `GET /api/video-thumbnail/<video_id>`
- **Auth:** No explicit session check
- **Description:** Get pre-generated thumbnail or redirect to placeholder
- **Response:** Either JSON with URL or HTTP redirect
  ```json
  {
    "success": true,
    "url": "https://s3.amazonaws.com/thumbnails/thumb-123.jpg"
  }
  ```

#### `GET /api/clip-preview/<video_id>`
- **Auth:** No explicit session check
- **Description:** Get presigned URL for streaming preview
- **Query Params:** `?start=<seconds>&end=<seconds>`
- **Response:**
  ```json
  {
    "success": true,
    "url": "https://s3.amazonaws.com/clips/preview-123.mp4?start=10&end=60&X-Amz-Signature=...",
    "start_time": 10.0,
    "end_time": 60.0,
    "duration": 50.0
  }
  ```

#### `GET /api/clip-download/<video_id>`
- **Auth:** No explicit session check
- **Description:** Download clip at original quality
- **Query Params:** `?start=<seconds>&end=<seconds>&format=<mp4|mov>`
- **Response:**
  ```json
  {
    "success": true,
    "download_url": "https://s3.amazonaws.com/downloads/clip-123.mp4",
    "file_size": 15728640,
    "format": "mp4",
    "expires_in": 3600
  }
  ```

#### `GET /api/video-download/<video_id>`
- **Auth:** No explicit session check
- **Description:** Download full video
- **Response:**
  ```json
  {
    "success": true,
    "download_url": "https://s3.amazonaws.com/videos/full-123.mp4",
    "file_size": 104857600,
    "format": "mp4",
    "duration": 300.5
  }
  ```

#### `GET /api/audio-preview/<audio_id>`
- **Auth:** No explicit session check
- **Description:** Get presigned S3 URL for audio preview
- **Response:**
  ```json
  {
    "success": true,
    "url": "https://s3.amazonaws.com/audio/preview-123.mp3?X-Amz-Signature=...",
    "duration": 180.5,
    "format": "mp3"
  }
  ```

#### `GET /api/audio-clip/<audio_id>`
- **Auth:** No explicit session check
- **Description:** Get audio clip with presigned URL and time range
- **Response:**
  ```json
  {
    "success": true,
    "url": "https://s3.amazonaws.com/audio/clip-123.mp3",
    "start_time": 30.0,
    "end_time": 90.0,
    "duration": 60.0,
    "format": "mp3"
  }
  ```

### Transcript Management

#### `POST /api/transcript-segment/update`
- **Auth:** No explicit session check
- **Description:** Update transcript text for specific time range
- **Request Body:**
  ```json
  {
    "transcript_id": "trans_123",
    "start_time": 30.5,
    "end_time": 45.2,
    "new_text": "Updated transcript text for this segment"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "updated_segments": 2
  }
  ```
- **Errors:**
  - `400`: `{'error': 'Invalid time range'}`
  - `404`: `{'error': 'Transcript not found'}`

#### `POST /api/transcripts/<transcript_id>/identify-speakers`
- **Auth:** No explicit session check
- **Description:** Use AI to identify and label speakers
- **Response:**
  ```json
  {
    "success": true,
    "speakers_identified": 3,
    "speakers": [
      {"id": "speaker_1", "name": "John", "segments": 15},
      {"id": "speaker_2", "name": "Jane", "segments": 12},
      {"id": "speaker_3", "name": "Bob", "segments": 8}
    ],
    "processing_time": 45.2
  }
  ```

#### `PUT /api/segments/<segment_id>/speaker`
- **Auth:** No explicit session check
- **Description:** Update speaker label for segment
- **Request Body:**
  ```json
  {
    "speaker": "John Doe"
  }
  ```
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Segment not found'}`

### Video Management

#### `GET /api/videos/<video_id>`
- **Auth:** No explicit session check
- **Description:** Get single video details
- **Response:**
  ```json
  {
    "success": true,
    "video": {
      "id": "video_123",
      "title": "Marketing Video",
      "description": "Product launch video",
      "duration": 300.5,
      "file_size": 104857600,
      "resolution": "1920x1080",
      "fps": 30,
      "format": "mp4",
      "s3_key": "videos/video-123.mp4",
      "thumbnail_url": "https://...",
      "created_at": "2026-01-06T09:00:00Z",
      "tags": ["marketing", "product"]
    }
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Video not found'}`

#### `PUT /api/videos/<video_id>`
- **Auth:** No explicit session check
- **Description:** Update video metadata
- **Request Body:**
  ```json
  {
    "title": "Updated Video Title",
    "description": "Updated description",
    "tags": ["marketing", "product", "launch"]
  }
  ```
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:**
  - `404`: `{'error': 'Video not found'}`

#### `POST /api/videos/<video_id>/autofill`
- **Auth:** No explicit session check
- **Description:** Use AI to auto-fill video metadata from transcript
- **Response:**
  ```json
  {
    "success": true,
    "updated_fields": ["title", "description", "tags"],
    "suggestions": {
      "title": "AI-suggested title",
      "description": "AI-generated description",
      "tags": ["ai-tag-1", "ai-tag-2"]
    }
  }
  ```

### Comments & Feedback

#### `GET /api/clips/<conversation_id>/<clip_index>/comments`
- **Auth:** Session Required
- **Description:** Get comments on specific clip
- **Response:**
  ```json
  {
    "comments": [
      {
        "id": "comment_123",
        "content": "Great clip! Could use more energy.",
        "user": {
          "id": "user_456",
          "name": "John Doe",
          "avatar_url": "https://..."
        },
        "created_at": "2026-01-06T10:00:00Z"
      }
    ]
  }
  ```

#### `POST /api/clips/<conversation_id>/<clip_index>/comments`
- **Auth:** Session Required
- **Description:** Add comment on clip (use @mv-video for regeneration)
- **Request Body:**
  ```json
  {
    "content": "This needs more energy! @mv-video please regenerate"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "comment_id": "comment_456",
    "regeneration_requested": true
  }
  ```

#### `POST /api/clips/<conversation_id>/<clip_index>/regenerate`
- **Auth:** No explicit session check
- **Description:** Regenerate specific clip based on feedback
- **Request Body:**
  ```json
  {
    "feedback": "Make it more energetic and engaging"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "new_clip": {
      "title": "Updated Clip Title",
      "video_id": "video_789",
      "start_time": 15.0,
      "end_time": 55.0
    },
    "processing_time": 30.5
  }
  ```

#### `POST /api/records/<conversation_id>/<record_index>/comments`
- **Auth:** Session Required
- **Description:** Add comment on narration section
- **Request Body:**
  ```json
  {
    "content": "The pacing is too fast here @mv-video"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "comment_id": "comment_789"
  }
  ```

#### `POST /api/records/<conversation_id>/<record_index>/regenerate`
- **Auth:** Session Required
- **Description:** Regenerate narration section based on feedback
- **Request Body:**
  ```json
  {
    "feedback": "Slow down the pace and add more pauses"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "updated_record": {
      "content": "Updated narration content...",
      "duration": 45.0
    }
  }
  ```

### Commented Out Routes (Audio API)

#### `GET /api/audio` (Commented out)
- **Auth:** No Session Check
- **Description:** API endpoint to list all audio recordings
- **Response:** Would return array of audio objects

---

## Implementation Notes

### Session Management
- Uses Flask's built-in session with cookies
- `session['user_id']` stores authenticated user ID
- `session['user_name']` and `session['user_email']` store user info
- 2FA uses temporary session keys like `pending_2fa_user_id`

### Database Patterns
- Uses `DatabaseSession()` context manager for all DB operations
- UUID primary keys throughout the system
- Soft deletes with `is_active` flags
- Timestamps in ISO format with timezone info

### Error Handling
- Consistent JSON error responses: `{'error': 'Message'}`
- HTTP status codes: 401 (auth), 400 (validation), 404 (not found), 500 (server error)
- Most routes handle exceptions with try/catch blocks

### S3 Integration
- Presigned URLs for secure media access with expiration
- Separate buckets/paths for videos, audio, thumbnails, clips
- File processing with ffmpeg for clip extraction

### AI Integration
- Multiple model support: Claude (Sonnet), OpenAI (GPT-4o)
- Token counting and cost tracking in AI logs
- Context search across transcripts for better responses
- Intent detection for copy vs script generation

### Authentication Flow
1. POST `/login` with credentials
2. If 2FA enabled → redirect to `/verify-2fa`
3. If 2FA not set up → mandatory `/setup-2fa-required`
4. Success → session established with `user_id`
5. All protected routes check `session['user_id']`

This documentation covers all existing routes as of the current `web/app.py` implementation. Many routes are commented out but documented for completeness.