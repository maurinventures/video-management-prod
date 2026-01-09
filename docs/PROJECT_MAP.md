# PROJECT MAP - Internal Platform

## Overview
Full-stack video management and AI-powered content creation platform with React frontend, Flask backend, and PostgreSQL database.

---

## 📁 Directory Structure (2 levels deep)

```
.
├── _archive/                     # Legacy code archives
│   ├── legacy-frontend/         # Old frontend implementations
│   └── old-frontend/           # Previous frontend versions
├── .github/                     # GitHub workflows and CI/CD
│   └── workflows/              # GitHub Actions workflows
├── archive/                     # Additional archived assets
│   ├── web_styles/             # Legacy CSS/styling
│   └── web_templates/          # Legacy HTML templates
├── config/                      # Configuration files and credentials
├── Digitalbrainplatformuidesign/ # Main React frontend application
│   ├── .github/                # Frontend-specific GitHub config
│   ├── guidelines/             # Design guidelines and documentation
│   └── src/                    # Frontend source code
├── docs/                        # Project documentation
├── migrations/                  # Database migration scripts
├── scripts/                     # Python utilities and database models
│   └── migrations/             # Database schema migrations
├── services/                    # Backend service modules
├── tests/                      # Test files and test utilities
└── web/                        # Flask backend application
    └── services/               # Backend service classes
```

---

## 🚀 Tech Stack

### Frontend (Digitalbrainplatformuidesign/)
- **Framework**: React 18.3.1 with TypeScript
- **Build Tool**: Vite 6.3.5
- **Styling**: Tailwind CSS 4.1.12
- **UI Components**: Radix UI (comprehensive component library)
- **State Management**: React Hooks (useState, useEffect)
- **Icons**: Lucide React 0.487.0
- **Notifications**: Sonner 2.0.3
- **Theming**: Next Themes 0.4.6
- **Forms**: React Hook Form 7.55.0
- **Charts**: Recharts 2.15.2
- **DnD**: React DnD 16.0.1

### Backend (web/, scripts/, services/)
- **Framework**: Flask 3.0.0 + Flask-CORS 4.0.0
- **Database**: PostgreSQL with SQLAlchemy 2.0.0 + psycopg2-binary 2.9.9
- **AI/LLM**: OpenAI 1.0.0 + Anthropic 0.18.0
- **Cloud**: AWS (boto3 1.34.0) - S3, SES, RDS
- **Authentication**: PyOTP 2.9.0 + QRCode 7.4.0 (2FA)
- **Audio Processing**: OpenAI Whisper (transcription)
- **Document Processing**: python-docx 1.1.0
- **Configuration**: PyYAML 6.0.1

### Development Tools
- **Testing**: Pytest 7.4.0 + Coverage + Flask + Mock
- **Code Quality**: Black 23.0.0 + Flake8 6.0.0 + isort 5.12.0
- **Security**: Safety 3.0.0 + Bandit 1.7.0
- **Frontend Testing**: Playwright 1.57.0

---

## 🎯 Entry Points

### Main Application Files
| Component | File Path | Description |
|-----------|-----------|-------------|
| **React App** | `Digitalbrainplatformuidesign/src/app/App.tsx` | Main React application with auth flow |
| **Flask API** | `web/app.py` | Flask backend with all API routes (4000+ lines) |
| **Database Models** | `scripts/db.py` | SQLAlchemy models and database session management |
| **Config Loader** | `scripts/config_loader.py` | Centralized configuration and credentials management |

### Frontend Entry Points
| File | Purpose |
|------|---------|
| `Digitalbrainplatformuidesign/src/main.tsx` | Vite/React entry point |
| `Digitalbrainplatformuidesign/src/app/App.tsx` | Main app component with routing |
| `Digitalbrainplatformuidesign/src/services/api.ts` | API client configuration |
| `Digitalbrainplatformuidesign/src/services/auth.ts` | Authentication service |

### Backend Entry Points
| File | Purpose |
|------|---------|
| `web/app.py` | Main Flask application (API routes, auth, chat) |
| `scripts/db.py` | Database models and session management |
| `web/services/` | Service layer (AI, transcription, video processing) |

---

## 🔑 Environment Variables & Configuration

### Configuration Files
- `config/credentials.yaml` - Main credentials file (unencrypted in development)
- `config/credentials.yaml.template` - Template showing required credentials
- `config/settings.yaml` - Application settings
- `config/aws_optimization.yaml` - AWS service configuration
- `config/deployment.yaml` - Deployment configuration
- `config/monitoring.yaml` - Monitoring and logging configuration

### Required Credentials
```yaml
apis:
  anthropic:
    api_key: sk-ant-... # Claude API key
  openai:
    api_key: sk-... # OpenAI API key

aws:
  access_key_id: AKIA... # AWS access key
  secret_access_key: ... # AWS secret key
  s3_bucket: mv-brain # S3 bucket name
  region: us-east-1 # AWS region

databases:
  peraspera_brain:
    host: mv-database.xxx.us-east-1.rds.amazonaws.com
    port: 5432
    database: video_management
    username: postgres
    password: ... # Database password
```

### Optional Configuration
- **Notion API**: For external content integration
- **GitHub Token**: For CI/CD operations
- **EC2 Keys**: For server deployment

---

## 🔐 Authentication System Files

### Frontend Auth Components
| File | Purpose |
|------|---------|
| `Digitalbrainplatformuidesign/src/app/components/auth/login.tsx` | Login form with 2FA support |
| `Digitalbrainplatformuidesign/src/app/components/auth/signup.tsx` | User registration form |
| `Digitalbrainplatformuidesign/src/app/components/auth/email-verification.tsx` | Email verification flow |
| `Digitalbrainplatformuidesign/src/app/components/auth/two-factor-setup.tsx` | 2FA setup with QR codes |
| `Digitalbrainplatformuidesign/src/app/components/auth/two-factor-verify.tsx` | 2FA code verification |
| `Digitalbrainplatformuidesign/src/app/components/auth/backup-codes.tsx` | 2FA backup codes display |
| `Digitalbrainplatformuidesign/src/app/components/auth/forgot-password.tsx` | Password reset request |
| `Digitalbrainplatformuidesign/src/app/components/auth/reset-password.tsx` | Password reset form |

### Backend Auth Endpoints
| Endpoint | File Location | Purpose |
|----------|---------------|---------|
| `/api/auth/login` | `web/app.py:3995` | User authentication |
| `/api/auth/register` | `web/app.py:4285` | User registration |
| `/api/auth/verify-email` | `web/app.py:4362` | Email verification |
| `/api/auth/setup-2fa` | `web/app.py:4076` | 2FA setup |
| `/api/auth/verify-2fa` | `web/app.py:4045` | 2FA verification |
| `/api/auth/forgot-password` | `web/app.py:4443` | Password reset request |
| `/api/auth/reset-password` | `web/app.py:4558` | Password reset |
| `/api/auth/me` | `web/app.py:3960` | Get current user |
| `/api/auth/logout` | `web/app.py:4421` | User logout |

---

## 🗄️ Database Models (scripts/db.py)

### Core Models
| Model | Purpose | Key Relationships |
|-------|---------|------------------|
| `User` | User accounts, auth, preferences | → conversations, projects, backup_codes |
| `Conversation` | Chat conversations | → messages, user, project |
| `ChatMessage` | Individual chat messages | → conversation, user |
| `Project` | Project organization | → conversations, user |
| `Video` | Video files and metadata | → transcripts, conversations |
| `Transcript` | Video transcriptions | → video, segments |
| `AudioRecording` | Audio files | → segments |

### Auth & Security Models
| Model | Purpose |
|-------|---------|
| `BackupCode` | 2FA backup codes |
| `PasswordResetToken` | Password reset tokens |
| `AILog` | AI API usage logging |

### Content Models
| Model | Purpose |
|-------|---------|
| `Document` | PDF and document files |
| `Persona` | AI personas for content generation |
| `ExternalContent` | Web articles, external videos |
| `SocialPost` | Generated social media content |

---

## 🌐 API Endpoints Overview

### Authentication (`/api/auth/`)
- Complete auth system with 2FA, email verification, password reset
- Session-based authentication with secure cookies

### Chat (`/api/chat/`)
- Real-time AI chat with Claude and OpenAI models
- Script generation with video content integration
- RAG (Retrieval Augmented Generation) support

### Conversations (`/api/conversations/`)
- Create, list, update, delete conversations
- Message history and persistence
- Project organization

### Media (`/api/video-preview/`, `/api/audio-preview/`)
- S3 presigned URLs for secure media access
- Video and audio streaming

### Content Management
- Video upload, processing, transcription
- Document processing and storage
- External content integration

---

## 🎨 Main UI Components

### Core Screens
| Component | File | Purpose |
|-----------|------|---------|
| `ChatScreen` | `Digitalbrainplatformuidesign/src/app/components/screens/chat-screen.tsx` | Main chat interface |
| `LibraryScreen` | `Digitalbrainplatformuidesign/src/app/components/screens/library-screen.tsx` | Media library management |
| `ProjectsScreen` | `Digitalbrainplatformuidesign/src/app/components/screens/projects-screen.tsx` | Project management |
| `ScriptGenerationScreen` | `Digitalbrainplatformuidesign/src/app/components/screens/script-generation-screen.tsx` | AI script generation |

### Shared Components
| Component | Purpose |
|-----------|---------|
| `Sidebar` | Navigation and chat history |
| `CommandPalette` | Quick actions and search |
| `SettingsDialog` | User preferences |

### UI Foundation
| Directory | Purpose |
|-----------|---------|
| `Digitalbrainplatformuidesign/src/app/components/ui/` | Radix UI component library |
| `Digitalbrainplatformuidesign/src/app/components/shared/` | Reusable components |
| `Digitalbrainplatformuidesign/src/styles/` | Global styles and themes |

---

## 🔧 Key Utility Files

### Frontend Utilities
| File | Purpose |
|------|---------|
| `Digitalbrainplatformuidesign/src/services/api.ts` | HTTP client for backend API |
| `Digitalbrainplatformuidesign/src/services/auth.ts` | Authentication service |
| `Digitalbrainplatformuidesign/src/app/data/` | Mock data and constants |

### Backend Services
| File | Purpose |
|------|---------|
| `web/services/ai_service.py` | AI model integration |
| `web/services/transcript_service.py` | Video transcription |
| `web/services/video_service.py` | Video processing |
| `scripts/config_loader.py` | Configuration management |

---

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.8+ (for backend)
- PostgreSQL database
- AWS account (S3, SES, RDS)
- OpenAI and Anthropic API keys

### Quick Setup
1. **Clone and install dependencies**:
   ```bash
   cd Digitalbrainplatformuidesign && npm install
   pip install -r requirements.txt
   ```

2. **Configure credentials**:
   ```bash
   cp config/credentials.yaml.template config/credentials.yaml
   # Edit config/credentials.yaml with your API keys
   ```

3. **Run development servers**:
   ```bash
   # Frontend
   cd Digitalbrainplatformuidesign && npm run dev

   # Backend
   python3 web/app.py
   ```

### Production Deployment
- Frontend: Built with `npm run build` → served from `dist/`
- Backend: Flask app deployed to EC2 with systemd service
- Database: AWS RDS PostgreSQL instance
- Storage: AWS S3 for media files
- Email: AWS SES for transactional emails

---

## 📊 Architecture Summary

**Frontend**: React SPA with TypeScript, Tailwind CSS, and comprehensive UI component library
**Backend**: Flask REST API with SQLAlchemy ORM and PostgreSQL database
**AI Integration**: OpenAI GPT and Anthropic Claude for chat and content generation
**Storage**: AWS S3 for media files, RDS for structured data
**Authentication**: Session-based auth with 2FA support and password reset
**Deployment**: Production deployment on AWS infrastructure

This is a production-ready application with modern development practices, comprehensive authentication, and scalable cloud architecture.