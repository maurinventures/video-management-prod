-- Migration: Add starred column to conversations table
-- Run this to add the starred functionality to existing conversations

-- Add starred column to conversations table
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS starred BOOLEAN DEFAULT FALSE;

-- Update existing conversations to have starred = FALSE (already default, but explicit)
UPDATE conversations SET starred = FALSE WHERE starred IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN conversations.starred IS 'Whether this conversation is starred by the user';