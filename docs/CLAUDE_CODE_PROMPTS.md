# Internal Platform — Claude Code Instructions

## Project Context

**What exists:** Flask backend (web/app.py, 140KB) with PostgreSQL, S3, Claude/OpenAI integration, 2FA auth. Production at maurinventuresinternal.com on EC2.

**What we're adding:** React frontend to replace Flask templates. The API stays.

**Architecture:** React (port 3000) → Flask API (port 5000) → Services → Database/S3

**UI Components (source of truth):** GitHub repo `maurinventures/Digitalbrainplatformuidesign` — Figma Make exports go in `/frontend/src/components/`

---

## Priority Order

1. **Setup (1-7):** Repo cleanup, React scaffold
2. **Core Features (8-12):** Auth, chat, library connections
3. **RAG System (13-18):** Cost control — do before heavy AI usage
4. **Long-Form (19-22):** Generation pipeline for scripts/essays
5. **Testing (23-26):** Verification
6. **AWS (27-30):** Optimization

---

## Phase 1: Setup

### Prompt 1: Rename Repo
```
Rename this repo from "video-management-prod" to "internal-platform" using GitHub CLI. Update the local git remote.
```

### Prompt 2: Archive Legacy Frontend
```
Move web/templates/ and web/static/ to _archive/legacy-frontend/. Keep web/app.py — that's the API. Add a README in _archive explaining these are preserved legacy files.
```

### Prompt 3: Update CLAUDE.md
```
Update CLAUDE.md: Project is now "Internal Platform" with React frontend + Flask API. Remove protection of web/templates and web/static (now archived). Add /frontend/src/components/ as protected (Figma exports go there). Link to specs: https://www.notion.so/2df71d8cc1fa815aa51cfc1bd4ce7852
```

### Prompt 4: Update .gitignore
```
Add node_modules/, frontend/build/, .env.local, .env.production to .gitignore. Keep existing entries.
```

### Prompt 5: Create Frontend Scaffold
```
Create /frontend with React + TypeScript (create-react-app or Next.js). Set up proxy to Flask on port 5000. Create folders: components/, pages/, hooks/, lib/, types/. Don't build any UI yet.
```

### Prompt 6: Create API Client
```
Create /frontend/src/lib/api.ts. ALL API calls must go through this file — no fetch() scattered in components. Include auth, chat, videos, audio, transcripts, personas endpoints. Follow patterns from the existing Flask routes in app.py.
```

### Prompt 7: Document Existing API
```
Create /docs/EXISTING_API.md. Scan web/app.py for all @app.route decorators and document each: path, method, request body, response format, auth required. Don't change any code.
```

---

## Phase 2: Core Features

### Prompt 8: Connect Auth Flow
```
Wire React auth to existing Flask auth endpoints. For 2FA, reuse existing logic. Add new endpoints for email verification and backup codes — create the necessary tables. Follow existing patterns in app.py.
```

### Prompt 9: Connect Chat with Model Selector
```
Wire React chat to POST /api/chat. Add GET /api/models endpoint returning available Claude and OpenAI models. Store selected model per conversation. Add model dropdown in frontend.
```

### Prompt 10: Connect Library
```
Wire React library to existing video/audio/transcript endpoints. Add tables and CRUD endpoints for external content: articles, external videos, web clips, PDFs. Follow existing patterns. Migration file needed.
```

### Prompt 11: Dual Download for Clips
```
Add endpoints for clip download: one for trimmed segment (use ffmpeg), one for full source. Return metadata with both options. Cache extracted segments to avoid re-processing.
```

### Prompt 12: Extract Services from app.py
```
The 140KB app.py mixes routes with business logic. Extract into services: ai_service.py (all LLM calls), video_service.py, audio_service.py, transcript_service.py. Routes should become thin — just validation and calling services. Do incrementally, test after each.
```

---

## Phase 3: RAG System (Cost Control)

> ⚠️ Without RAG, queries with your terabytes of transcripts cost $1.50+ each. With RAG, $0.01 each.

### Prompt 13: Audit Current AI Usage
```
Before changing anything, report: How are transcripts currently sent to Claude/OpenAI? What's the average token count per request? Any caching? Estimate monthly cost at current patterns. Create /docs/AI_USAGE_AUDIT.md.
```

### Prompt 14: Set Up pgvector
```
Enable pgvector extension in RDS. Test with a simple table to confirm vector similarity search works. If RDS doesn't support it, report back.
```

### Prompt 15: Create Knowledge Hierarchy Tables
```
Create tables for hierarchical RAG: corpus_summary (one row, overall KB description), rag_documents (summaries per video/article), rag_sections (summaries per segment), rag_chunks (searchable text ~400 tokens each with embeddings). Add vector indexes and full-text search index. Migration file needed.
```

### Prompt 16: Create Embedding Service
```
Create scripts/embedding_service.py. Use OpenAI text-embedding-3-small ($0.02/1M tokens). Handle single text and batch embedding. Format output for pgvector. Reuse existing OpenAI client from config.
```

### Prompt 17: Create Content Processor
```
Create scripts/content_processor.py. Process transcripts into the knowledge hierarchy: generate document summary, split into sections with summaries, chunk into ~400 token pieces preserving speaker turns. Use Claude Haiku for summaries (cheap). Store embeddings. This is a batch job for existing content + runs on new uploads.
```

### Prompt 18: Implement RAG in Chat
```
Modify ai_service to use RAG: embed the query, search chunks (hybrid: semantic + keyword), assemble top results with context, send to Claude with citations format. Should reduce tokens from 500K+ to ~5K per query. Add token usage logging table to track costs.
```

---

## Phase 4: Long-Form Generation

### Prompt 19: Token Limits and Tracking
```
Add ai_usage_log table tracking every AI call: tokens, cost, model, user. Add endpoint to view usage stats. Implement limits: max 50K context tokens, daily user limit of 500K tokens, warn at 80%. Cache identical prompts to avoid duplicate costs.
```

### Prompt 20: Generation Pipeline Service
```
Create scripts/generation_service.py for long-form content. Pipeline: brief → outline → consistency docs → sectional generation → assembly. Store job state in generation_jobs table. Each section generated separately with full outline context.
```

### Prompt 21: Outline and Consistency Docs
```
Before generating long content, create: outline (sections with word targets), style guide (tone, voice), fact sheet (established facts that can't contradict), character bible (for scripts). Store as JSON in generation job. Include in every section generation.
```

### Prompt 22: Sectional Generation
```
Generate long content section by section (~1000-1500 words each). Each call includes: full outline, consistency docs, previous section ending, current section requirements. Post-process to extract new facts. Run continuity check after all sections complete.
```

---

## Phase 5: Testing

### Prompt 23: Frontend Tests
```
Add Jest + React Testing Library. Test: login form submits, chat sends messages, library displays items, download buttons work. Mock the API client. Tests should pass without Flask running.
```

### Prompt 24: API Tests
```
Add pytest for Flask. Test: auth endpoints return correct responses, chat returns AI response, CRUD operations work. Mock service layer. Tests should pass without real AI calls.
```

### Prompt 25: CI Pipeline
```
Set up GitHub Actions: run frontend tests, run API tests, run linting. Block merge if tests fail.
```

### Prompt 26: Smoke Tests
```
Create scripts/smoke_test.py. After deploy, verify: homepage loads, API health endpoint responds, can fetch data. Run automatically after each deploy.
```

---

## Phase 6: AWS Optimization

### Prompt 27: Audit AWS Usage
```
Report current setup: EC2 instance type and utilization, RDS instance type and storage, S3 bucket sizes, data transfer costs. Flag obvious waste. Don't change anything.
```

### Prompt 28: S3 Lifecycle Policies
```
Set up S3 lifecycle policies: move old files to cheaper storage tiers, check for orphaned uploads, enable intelligent tiering if sensible. Show proposed policies before applying.
```

### Prompt 29: RDS and EC2 Right-Sizing
```
Analyze RDS and EC2 utilization. Recommend right-sizing if oversized. Check for missing indexes causing slow queries. Evaluate Reserved Instances for cost savings. Report recommendations with estimated savings.
```

### Prompt 30: Deploy React + Flask
```
Update nginx config: serve React build as static files, proxy /api/* to Flask. Create deploy script that builds React, copies to nginx, restarts services. Document the process.
```

---

## Key Rules

**Don't:**
- Rewrite Flask backend in Node/Next.js
- Create new tables without checking existing ones
- Change auth logic that works
- Pass full transcripts to AI (use RAG)
- Over-engineer — this is an internal tool
- Manually edit files in /frontend/src/components/ — those come from Figma Make

**Do:**
- Read existing code before writing new code
- Follow existing patterns in app.py and scripts/
- Pull UI components from Figma Make repo: `maurinventures/Digitalbrainplatformuidesign`
- Test locally before deploying
- Ask clarifying questions if unclear
