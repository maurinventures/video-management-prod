-- Video Management System Database Schema
-- Run this script to set up the database tables

-- Create database (run separately if needed)
-- CREATE DATABASE video_management;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Videos table: original uploaded videos
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    s3_key VARCHAR(1000) NOT NULL UNIQUE,
    s3_bucket VARCHAR(255) NOT NULL DEFAULT 'per-aspera-brain',
    file_size_bytes BIGINT,
    duration_seconds DECIMAL(10, 2),
    resolution VARCHAR(50),
    format VARCHAR(20),
    status VARCHAR(50) DEFAULT 'uploaded',  -- uploaded, processing, transcribed, error
    uploaded_by VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Transcripts table: transcriptions of videos
CREATE TABLE IF NOT EXISTS transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    s3_key VARCHAR(1000) NOT NULL UNIQUE,
    provider VARCHAR(50) DEFAULT 'aws',  -- aws, whisper
    language VARCHAR(20) DEFAULT 'en-US',
    full_text TEXT,
    word_count INTEGER,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, error
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Transcript segments: individual timestamped segments
CREATE TABLE IF NOT EXISTS transcript_segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcript_id UUID NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    segment_index INTEGER NOT NULL,
    start_time DECIMAL(10, 3) NOT NULL,  -- seconds with milliseconds
    end_time DECIMAL(10, 3) NOT NULL,
    text TEXT NOT NULL,
    confidence DECIMAL(5, 4),
    speaker VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Clips table: segments cut from source videos
CREATE TABLE IF NOT EXISTS clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    clip_name VARCHAR(500) NOT NULL,
    s3_key VARCHAR(1000) UNIQUE,
    start_time DECIMAL(10, 3) NOT NULL,  -- seconds with milliseconds
    end_time DECIMAL(10, 3) NOT NULL,
    duration_seconds DECIMAL(10, 2) GENERATED ALWAYS AS (end_time - start_time) STORED,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, error
    file_size_bytes BIGINT,
    notes TEXT,
    created_by VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Compiled videos table: final videos assembled from clips
CREATE TABLE IF NOT EXISTS compiled_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    s3_key VARCHAR(1000) UNIQUE,
    total_duration_seconds DECIMAL(10, 2),
    file_size_bytes BIGINT,
    resolution VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, error
    created_by VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Junction table: clips in compiled videos (with ordering)
CREATE TABLE IF NOT EXISTS compiled_video_clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    compiled_video_id UUID NOT NULL REFERENCES compiled_videos(id) ON DELETE CASCADE,
    clip_id UUID NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    sequence_order INTEGER NOT NULL,
    transition_type VARCHAR(50) DEFAULT 'cut',  -- cut (no transition)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(compiled_video_id, sequence_order)
);

-- Processing jobs table: track async operations
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL,  -- transcribe, clip, compile
    reference_id UUID NOT NULL,  -- ID of video, clip, or compiled_video
    reference_type VARCHAR(50) NOT NULL,  -- video, clip, compiled_video
    aws_job_id VARCHAR(500),  -- AWS Transcribe job ID if applicable
    status VARCHAR(50) DEFAULT 'queued',  -- queued, running, completed, failed
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at);
CREATE INDEX IF NOT EXISTS idx_transcripts_video_id ON transcripts(video_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_status ON transcripts(status);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_transcript_id ON transcript_segments(transcript_id);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_times ON transcript_segments(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_clips_source_video_id ON clips(source_video_id);
CREATE INDEX IF NOT EXISTS idx_clips_status ON clips(status);
CREATE INDEX IF NOT EXISTS idx_compiled_video_clips_compiled_id ON compiled_video_clips(compiled_video_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_reference ON processing_jobs(reference_id, reference_type);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_videos_updated_at ON videos;
CREATE TRIGGER update_videos_updated_at
    BEFORE UPDATE ON videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_transcripts_updated_at ON transcripts;
CREATE TRIGGER update_transcripts_updated_at
    BEFORE UPDATE ON transcripts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_clips_updated_at ON clips;
CREATE TRIGGER update_clips_updated_at
    BEFORE UPDATE ON clips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_compiled_videos_updated_at ON compiled_videos;
CREATE TRIGGER update_compiled_videos_updated_at
    BEFORE UPDATE ON compiled_videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_processing_jobs_updated_at ON processing_jobs;
CREATE TRIGGER update_processing_jobs_updated_at
    BEFORE UPDATE ON processing_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View: Video inventory with transcript status
CREATE OR REPLACE VIEW video_inventory AS
SELECT
    v.id,
    v.filename,
    v.original_filename,
    v.s3_key,
    v.duration_seconds,
    v.status as video_status,
    t.id as transcript_id,
    t.status as transcript_status,
    COUNT(DISTINCT c.id) as clip_count,
    v.created_at,
    v.updated_at
FROM videos v
LEFT JOIN transcripts t ON v.id = t.video_id
LEFT JOIN clips c ON v.id = c.source_video_id
GROUP BY v.id, t.id;

-- View: Compiled video details with clips
CREATE OR REPLACE VIEW compiled_video_details AS
SELECT
    cv.id,
    cv.title,
    cv.description,
    cv.s3_key,
    cv.total_duration_seconds,
    cv.status,
    COUNT(cvc.id) as clip_count,
    ARRAY_AGG(c.clip_name ORDER BY cvc.sequence_order) as clip_names,
    cv.created_at
FROM compiled_videos cv
LEFT JOIN compiled_video_clips cvc ON cv.id = cvc.compiled_video_id
LEFT JOIN clips c ON cvc.clip_id = c.id
GROUP BY cv.id;
