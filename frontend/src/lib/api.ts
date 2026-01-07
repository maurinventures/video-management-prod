/**
 * API Client for Internal Platform
 *
 * All API calls must go through this file - no fetch() scattered in components.
 * Follows patterns from Flask routes in web/app.py.
 */

import {
  ApiResponse,
  User,
  Conversation,
  Message,
  Project,
  Persona,
  Video,
  Audio,
  Transcript,
  TranscriptSegment,
  ChatRequest,
  ChatResponse,
  Comment,
  Attachment,
  AIModel,
  ExternalContent,
  ExternalContentSegment,
  ExternalContentCreateRequest,
  ExternalContentUpdateRequest,
  ExternalContentSearchOptions,
  VideoDownloadOptionsResponse,
  ClipDownloadResponse,
  VideoDownloadResponse,
  ClipDownloadOptions,
  VideoDownloadOptions,
  UsageStatus,
  UsageLimits,
  UsageStats,
} from '../types';

// Base configuration - use relative URLs in production, localhost in development
const API_BASE_URL = process.env.REACT_APP_API_URL ||
  (process.env.NODE_ENV === 'production' ? '' : 'http://localhost:5001');

// Generic API client class
class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;

    const config: RequestInit = {
      credentials: 'include', // Include cookies for session-based auth
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        if (response.status === 401) {
          // Redirect to login on unauthorized
          window.location.href = '/login';
          throw new Error('Authentication required');
        }

        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return response.json();
      }

      return response.text() as unknown as T;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  private get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  private post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  private put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  private delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // Authentication endpoints
  auth = {
    // Check current authentication status
    me: () =>
      this.get<{ user: User }>('/api/auth/me'),

    // Primary login endpoint - handles 2FA flow
    login: (email: string, password: string) =>
      this.post<{
        success: boolean;
        user?: User;
        user_id?: string;
        requires_2fa?: boolean;
        requires_2fa_setup?: boolean;
        error?: string;
      }>('/api/auth/login', { email, password }),

    // Logout
    logout: () =>
      this.post<ApiResponse>('/api/auth/logout'),

    // User registration
    register: (name: string, email: string, password: string) =>
      this.post<{
        success: boolean;
        user?: User;
        requires_email_verification?: boolean;
        error?: string;
      }>('/api/auth/register', { name, email, password }),

    // 2FA verification
    verify2FA: (token: string) =>
      this.post<{
        success: boolean;
        user?: User;
        error?: string;
      }>('/api/auth/verify-2fa', { token }),

    // 2FA setup - returns QR code on first call, verifies on second
    setup2FA: (token?: string) =>
      this.post<{
        success: boolean;
        user?: User;
        qr_code?: string;
        secret?: string;
        error?: string;
      }>('/api/auth/setup-2fa', token ? { token } : {}),

    // Email verification
    verifyEmail: (token: string) =>
      this.get<{
        success: boolean;
        error?: string;
      }>(`/api/auth/verify-email?token=${token}`),

    // Resend verification email
    resendVerificationEmail: () =>
      this.post<{
        success: boolean;
        error?: string;
      }>('/api/auth/resend-verification'),

    // Generate backup codes for 2FA
    generateBackupCodes: () =>
      this.post<{
        success: boolean;
        codes?: string[];
        error?: string;
      }>('/api/auth/backup-codes'),

    // Verify backup code
    verifyBackupCode: (code: string) =>
      this.post<{
        success: boolean;
        user?: User;
        error?: string;
      }>('/api/auth/verify-backup-code', { code }),

    // Reset password request
    requestPasswordReset: (email: string) =>
      this.post<{
        success: boolean;
        error?: string;
      }>('/api/auth/reset-password', { email }),

    // Reset password with token
    resetPassword: (token: string, newPassword: string) =>
      this.post<{
        success: boolean;
        error?: string;
      }>('/api/auth/reset-password-confirm', { token, password: newPassword }),
  };

  // Conversation endpoints
  conversations = {
    list: () =>
      this.get<{ conversations: Conversation[] }>('/api/conversations'),

    create: (data: { title?: string; project_id?: string; preferred_model?: string }) =>
      this.post<Conversation>('/api/conversations', data),

    get: (id: string) =>
      this.get<{
        id: string;
        title: string;
        project_id?: string;
        preferred_model: string;
        created_at: string;
        updated_at: string;
        messages: Message[];
      }>(`/api/conversations/${id}`),

    update: (id: string, data: { title?: string; preferred_model?: string }) =>
      this.put<ApiResponse>(`/api/conversations/${id}`, data),

    delete: (id: string) =>
      this.delete<ApiResponse>(`/api/conversations/${id}`),

    star: (id: string, starred: boolean) =>
      this.put<ApiResponse>(`/api/conversations/${id}/star`, { starred }),

    generateTitle: (id: string) =>
      this.post<{ title: string }>(`/api/conversations/${id}/generate-title`),

    setProject: (id: string, project_id: string | null) =>
      this.put<ApiResponse>(`/api/conversations/${id}/project`, { project_id }),
  };

  // AI Models endpoints
  models = {
    list: () =>
      this.get<{
        models: AIModel[];
        default: string;
      }>('/api/models'),
  };

  // Chat endpoints
  chat = {
    sendMessage: (data: {
      conversation_id?: string;
      message: string;
      model?: string;
      history?: any[];
      previous_clips?: any[];
    }) =>
      this.post<{
        response: string;
        clips?: any[];
        has_script?: boolean;
        is_copy?: boolean;
        persona?: string;
        platform?: string;
        context_segments?: number;
        model: string;
        conversation_id?: string;
      }>('/api/chat', data),

    createVideo: (data: {
      conversation_id: string;
      script: string;
      clips: any[];
    }) =>
      this.post<ApiResponse>('/api/chat/create-video', data),

    exportScript: (data: {
      conversation_id: string;
      format: string;
    }) =>
      this.post<{ download_url: string }>('/api/chat/export-script', data),
  };

  // Project endpoints
  projects = {
    list: (includeArchived = false) =>
      this.get<Project[]>(`/api/projects?include_archived=${includeArchived}`),

    create: (name: string, description?: string) =>
      this.post<Project>('/api/projects', { name, description }),

    get: (id: string) =>
      this.get<{
        project: Project;
        conversations: Conversation[];
      }>(`/api/projects/${id}`),

    update: (id: string, data: { name?: string; description?: string }) =>
      this.put<ApiResponse>(`/api/projects/${id}`, data),

    delete: (id: string, permanent = false) =>
      this.delete<ApiResponse>(`/api/projects/${id}?permanent=${permanent}`),
  };

  // Persona endpoints
  personas = {
    list: () =>
      this.get<Persona[]>('/api/personas'),

    create: (data: {
      name: string;
      description?: string;
      voice_settings?: any;
      avatar_url?: string;
    }) =>
      this.post<Persona>('/api/personas', data),

    update: (id: string, data: {
      name?: string;
      description?: string;
      voice_settings?: any;
      avatar_url?: string;
    }) =>
      this.put<ApiResponse>(`/api/personas/${id}`, data),

    delete: (id: string) =>
      this.delete<ApiResponse>(`/api/personas/${id}`),
  };

  // Video endpoints
  videos = {
    get: (id: string) =>
      this.get<Video>(`/api/videos/${id}`),

    update: (id: string, data: {
      title?: string;
      description?: string;
      tags?: string[];
    }) =>
      this.put<ApiResponse>(`/api/videos/${id}`, data),

    getPreviewUrl: (id: string) =>
      this.get<{ url: string }>(`/api/video-preview/${id}`),

    getThumbnail: (id: string) =>
      this.get<{ url: string }>(`/api/video-thumbnail/${id}`),

    getClipPreview: (id: string) =>
      this.get<{ url: string }>(`/api/clip-preview/${id}`),

    // Enhanced download methods for Prompt 11
    getDownloadOptions: (id: string) =>
      this.get<VideoDownloadOptionsResponse>(`/api/video/${id}/download-options`),

    downloadClipSegment: (id: string, options: ClipDownloadOptions) => {
      const params = new URLSearchParams();
      params.set('start', options.start.toString());
      params.set('end', options.end.toString());
      if (options.metadata !== undefined) {
        params.set('metadata', options.metadata.toString());
      }
      if (options.timeout !== undefined) {
        params.set('timeout', Math.min(options.timeout, 900).toString());
      }
      return this.get<ClipDownloadResponse>(`/api/clip-download/${id}?${params}`);
    },

    downloadFullVideo: (id: string, options: VideoDownloadOptions = {}) => {
      const params = new URLSearchParams();
      if (options.metadata !== undefined) {
        params.set('metadata', options.metadata.toString());
      }
      const queryString = params.toString();
      return this.get<VideoDownloadResponse>(`/api/video-download/${id}${queryString ? '?' + queryString : ''}`);
    },

    // Legacy methods (kept for backward compatibility)
    downloadClip: (id: string) =>
      this.get<{ download_url: string }>(`/api/clip-download/${id}?metadata=false`),

    downloadFull: (id: string) =>
      this.get<{ download_url: string }>(`/api/video-download/${id}?metadata=false`),

    autofill: (id: string) =>
      this.post<ApiResponse>(`/api/videos/${id}/autofill`),
  };

  // Audio endpoints
  audio = {
    getPreviewUrl: (id: string) =>
      this.get<{ url: string }>(`/api/audio-preview/${id}`),

    getClip: (id: string) =>
      this.get<{
        url: string;
        start_time: number;
        end_time: number;
      }>(`/api/audio-clip/${id}`),
  };

  // Transcript endpoints
  transcripts = {
    updateSegment: (data: {
      transcript_id: string;
      start_time: number;
      end_time: number;
      new_text: string;
    }) =>
      this.post<ApiResponse>('/api/transcript-segment/update', data),

    identifySpeakers: (id: string) =>
      this.post<ApiResponse>(`/api/transcripts/${id}/identify-speakers`),

    updateSegmentSpeaker: (segmentId: string, speaker: string) =>
      this.put<ApiResponse>(`/api/segments/${segmentId}/speaker`, { speaker }),
  };

  // User management
  users = {
    search: (query: string) =>
      this.get<User[]>(`/api/users/search?q=${encodeURIComponent(query)}`),
  };

  // Conversation collaboration
  collaboration = {
    getParticipants: (conversationId: string) =>
      this.get<{
        owner: User;
        participants: Array<{
          user: User;
          role: string;
          invited_at: string;
        }>;
      }>(`/api/conversations/${conversationId}/participants`),

    invite: (conversationId: string, userIds: string[]) =>
      this.post<ApiResponse>(`/api/conversations/${conversationId}/invite`, {
        user_ids: userIds,
      }),

    leave: (conversationId: string) =>
      this.post<ApiResponse>(`/api/conversations/${conversationId}/leave`),
  };

  // File attachments
  attachments = {
    upload: (conversationId: string, file: File) => {
      const formData = new FormData();
      formData.append('file', file);

      return this.request<{
        attachment_id: string;
        filename: string;
        url: string;
      }>(`/api/conversations/${conversationId}/attachments`, {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      });
    },
  };

  // Comments and feedback
  comments = {
    getClipComments: (conversationId: string, clipIndex: number) =>
      this.get<Array<{
        id: string;
        content: string;
        user: User;
        created_at: string;
      }>>(`/api/clips/${conversationId}/${clipIndex}/comments`),

    addClipComment: (conversationId: string, clipIndex: number, content: string) =>
      this.post<ApiResponse>(`/api/clips/${conversationId}/${clipIndex}/comments`, {
        content,
      }),

    regenerateClip: (conversationId: string, clipIndex: number, feedback?: string) =>
      this.post<ApiResponse>(`/api/clips/${conversationId}/${clipIndex}/regenerate`, {
        feedback,
      }),

    addRecordComment: (conversationId: string, recordIndex: number, content: string) =>
      this.post<ApiResponse>(`/api/records/${conversationId}/${recordIndex}/comments`, {
        content,
      }),

    regenerateRecord: (conversationId: string, recordIndex: number, feedback?: string) =>
      this.post<ApiResponse>(`/api/records/${conversationId}/${recordIndex}/regenerate`, {
        feedback,
      }),
  };

  // Script feedback
  scripts = {
    submitFeedback: (data: {
      conversation_id: string;
      script_content: string;
      feedback: string;
      rating: number;
    }) =>
      this.post<ApiResponse>('/api/script-feedback', data),

    getExamples: () =>
      this.get<Array<{
        title: string;
        content: string;
        style: string;
      }>>('/api/script-examples'),
  };

  // External Content Library endpoints
  externalContent = {
    // List external content with search and filters
    list: (options: ExternalContentSearchOptions = {}) => {
      const searchParams = new URLSearchParams();
      if (options.q) searchParams.set('q', options.q);
      if (options.type) searchParams.set('type', options.type);
      if (options.author) searchParams.set('author', options.author);
      if (options.status) searchParams.set('status', options.status);
      if (options.limit) searchParams.set('limit', options.limit.toString());

      const queryString = searchParams.toString();
      return this.get<ExternalContent[]>(
        `/api/external-content${queryString ? '?' + queryString : ''}`
      );
    },

    // Get single external content item
    get: (id: string) =>
      this.get<ExternalContent>(`/api/external-content/${id}`),

    // Create new external content
    create: (data: ExternalContentCreateRequest) =>
      this.post<{
        success: boolean;
        id: string;
        message: string;
        error?: string;
      }>('/api/external-content', data),

    // Update external content
    update: (id: string, data: ExternalContentUpdateRequest) =>
      this.put<{
        success: boolean;
        message: string;
        error?: string;
      }>(`/api/external-content/${id}`, data),

    // Delete external content
    delete: (id: string) =>
      this.delete<{
        success: boolean;
        message: string;
        error?: string;
      }>(`/api/external-content/${id}`),

    // Get segments for external content
    getSegments: (id: string) =>
      this.get<ExternalContentSegment[]>(`/api/external-content/${id}/segments`),

    // Upload external content file
    upload: (file: File, metadata: {
      title?: string;
      content_type: 'article' | 'web_clip' | 'pdf' | 'external_video' | 'other';
      description?: string;
      author?: string;
    }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', metadata.title || file.name);
      formData.append('content_type', metadata.content_type);
      if (metadata.description) formData.append('description', metadata.description);
      if (metadata.author) formData.append('author', metadata.author);

      return this.request<{
        success: boolean;
        id: string;
        title: string;
        content_type: string;
        file_size: number;
        preview_url: string;
        message: string;
        error?: string;
      }>('/api/external-content/upload', {
        method: 'POST',
        body: formData,
        headers: {} // Remove Content-Type header to let browser set it for FormData
      });
    },

    // Search external content (same as list but with search emphasis)
    search: (query: string, options: Omit<ExternalContentSearchOptions, 'q'> = {}) =>
      this.externalContent.list({ ...options, q: query }),
  };

  // Usage tracking endpoints
  usage = {
    // Get current usage status
    getStatus: () => this.get<UsageStatus>('/api/usage/status'),

    // Get usage limits and pricing
    getLimits: () => this.get<UsageLimits>('/api/usage/limits'),

    // Get comprehensive usage stats
    getStats: (days?: number) => {
      const params = days ? `?days=${days}` : '';
      return this.get<UsageStats>(`/api/usage/stats${params}`);
    },

    // Clean old cached prompts (admin only)
    cleanCache: (days?: number) =>
      this.post<{ success: boolean; deleted_entries: number; cutoff_days: number }>(
        '/api/usage/clean-cache',
        { days }
      ),
  };

  // Admin endpoints (if needed)
  admin = {
    invite: (email: string, name?: string) =>
      this.post<ApiResponse>('/admin/invite', { email, name }),
  };
}

// Create and export singleton instance
const api = new ApiClient();
export default api;

// Also export the class for testing
export { ApiClient };