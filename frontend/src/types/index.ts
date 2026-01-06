/**
 * TypeScript type definitions for Internal Platform
 */

// API Response wrapper
export interface ApiResponse<T = any> {
  success?: boolean;
  error?: string;
  message?: string;
  data?: T;
}

// User types
export interface User {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

// Conversation types
export interface Conversation {
  id: string;
  title: string;
  user_id: string;
  project_id?: string;
  is_starred: boolean;
  is_archived?: boolean;
  preferred_model: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  updated_at?: string;
  metadata?: {
    model?: string;
    persona_id?: string;
    tokens_used?: number;
    cost?: number;
    [key: string]: any;
  };
}

// Project types
export interface Project {
  id: string;
  name: string;
  description?: string;
  user_id: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  conversation_count?: number;
}

// Persona types
export interface Persona {
  id: string;
  name: string;
  description?: string;
  voice_settings?: {
    voice_id?: string;
    stability?: number;
    similarity_boost?: number;
    style?: number;
  };
  avatar_url?: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

// Media types
export interface Video {
  id: string;
  title: string;
  description?: string;
  s3_key: string;
  duration?: number;
  file_size?: number;
  width?: number;
  height?: number;
  fps?: number;
  user_id: string;
  created_at: string;
  updated_at?: string;
  tags?: string[];
  thumbnail_url?: string;
}

export interface Audio {
  id: string;
  title: string;
  description?: string;
  s3_key: string;
  duration?: number;
  file_size?: number;
  sample_rate?: number;
  channels?: number;
  user_id: string;
  created_at: string;
  updated_at?: string;
  tags?: string[];
}

// External Content Library types
export interface ExternalContent {
  id: string;
  title: string;
  content_type: 'article' | 'web_clip' | 'pdf' | 'external_video' | 'other';
  description?: string;
  source_url?: string;
  original_filename?: string;
  s3_key?: string;
  s3_bucket?: string;
  file_size_bytes?: number;
  file_format?: string;
  content_text?: string;
  content_summary?: string;
  word_count?: number;
  duration_seconds?: number;
  thumbnail_s3_key?: string;
  content_date?: string;
  author?: string;
  tags: string[];
  keywords: string[];
  extra_data: any;
  status: string;
  processing_notes?: string;
  segments_count?: number;
  preview_url?: string;
  download_url?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface ExternalContentSegment {
  id: string;
  content_id: string;
  segment_index: number;
  section_title?: string;
  start_time?: number;
  end_time?: number;
  start_position?: number;
  end_position?: number;
  text: string;
  speaker?: string;
  confidence?: number;
  created_at: string;
}

export interface ExternalContentCreateRequest {
  title: string;
  content_type: 'article' | 'web_clip' | 'pdf' | 'external_video' | 'other';
  description?: string;
  source_url?: string;
  author?: string;
  content_date?: string;
  tags?: string[];
  extra_data?: any;
}

export interface ExternalContentUpdateRequest {
  title?: string;
  description?: string;
  author?: string;
  content_date?: string;
  tags?: string[];
  status?: string;
  processing_notes?: string;
  extra_data?: any;
}

export interface ExternalContentSearchOptions {
  q?: string;
  type?: 'article' | 'web_clip' | 'pdf' | 'external_video' | 'other';
  author?: string;
  tags?: string[];
  status?: string;
  limit?: number;
}

// Transcript types
export interface Transcript {
  id: string;
  video_id?: string;
  audio_id?: string;
  content: string;
  language?: string;
  confidence?: number;
  user_id: string;
  created_at: string;
  updated_at?: string;
  segments?: TranscriptSegment[];
}

export interface TranscriptSegment {
  id: string;
  transcript_id: string;
  start_time: number;
  end_time: number;
  text: string;
  speaker?: string;
  confidence?: number;
  sequence_number: number;
}

// Chat and AI types
export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  model?: string;
  persona_id?: string;
  tokens_used?: number;
  cost?: number;
  created_at: string;
  metadata?: any;
}

export interface ChatRequest {
  conversation_id?: string;
  message: string;
  model?: string;
  persona_id?: string;
  context?: any;
}

export interface ChatResponse {
  conversation_id: string;
  message: Message;
  response: Message;
}

// Collaboration types
export interface ChatParticipant {
  id: string;
  conversation_id: string;
  user_id: string;
  role: 'owner' | 'editor' | 'viewer';
  invited_by: string;
  invited_at: string;
  accepted_at?: string;
  user?: User;
}

export interface ConversationWithParticipants {
  conversation: Conversation;
  owner: User;
  participants: Array<{
    user: User;
    role: string;
    invited_at: string;
    accepted_at?: string;
  }>;
}

// Comment and feedback types
export interface Comment {
  id: string;
  content: string;
  user_id: string;
  conversation_id: string;
  message_id?: string;
  clip_index?: number;
  created_at: string;
  user?: User;
}

export interface ScriptFeedback {
  id: string;
  conversation_id: string;
  script_content: string;
  feedback: string;
  rating: number;
  user_id: string;
  created_at: string;
}

// File attachment types
export interface Attachment {
  id: string;
  conversation_id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  s3_key: string;
  uploaded_by: string;
  created_at: string;
  url?: string;
}

// Generation and export types
export interface VideoClip {
  id: string;
  title: string;
  description: string;
  start_time?: number;
  end_time?: number;
  video_id?: string;
  audio_id?: string;
  generated_content?: string;
}

export interface ScriptExport {
  conversation_id: string;
  format: 'pdf' | 'docx' | 'txt' | 'markdown';
  content: string;
  download_url?: string;
}

// AI and model types
export interface AIModel {
  id: string;
  name: string;
  description: string;
  provider: 'openai' | 'anthropic';
  capabilities: string[];
  context_window: number;
  is_recommended: boolean;
}

export interface AIUsageLog {
  id: string;
  user_id: string;
  conversation_id?: string;
  model: string;
  tokens_input: number;
  tokens_output: number;
  cost: number;
  created_at: string;
  endpoint: string;
  success: boolean;
  error?: string;
}

// Search and filter types
export interface SearchResult {
  type: 'conversation' | 'message' | 'video' | 'audio' | 'transcript';
  id: string;
  title: string;
  excerpt?: string;
  match_score?: number;
  created_at: string;
  metadata?: any;
}

export interface FilterOptions {
  project_id?: string;
  user_id?: string;
  start_date?: string;
  end_date?: string;
  is_starred?: boolean;
  is_archived?: boolean;
  search_query?: string;
}

// Form and validation types
export interface LoginForm {
  email: string;
  password: string;
}

export interface RegisterForm {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface TwoFactorForm {
  token: string;
}

// UI State types
export interface UIState {
  isLoading: boolean;
  error?: string;
  success?: string;
}

export interface ConversationUIState extends UIState {
  selectedConversation?: Conversation;
  messages: Message[];
  isGenerating: boolean;
  currentModel?: string;
  currentPersona?: Persona;
}

export interface ProjectUIState extends UIState {
  projects: Project[];
  selectedProject?: Project;
  showArchived: boolean;
}

// Event types for real-time updates (if implemented later)
export interface WebSocketMessage {
  type: 'message' | 'typing' | 'conversation_update' | 'participant_joined';
  conversation_id: string;
  user_id: string;
  data: any;
  timestamp: string;
}

// Utility types
export type SortDirection = 'asc' | 'desc';
export type SortField = 'created_at' | 'updated_at' | 'title' | 'name';

export interface SortOptions {
  field: SortField;
  direction: SortDirection;
}

export interface PaginationOptions {
  page: number;
  limit: number;
  total?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  limit: number;
  total: number;
  has_more: boolean;
}