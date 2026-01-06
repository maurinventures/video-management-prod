/**
 * Hook for managing chat functionality
 *
 * Handles sending messages, managing conversation state, and integrating
 * with the model selector for AI chat functionality.
 */

import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';
import { Conversation, Message } from '../types';

interface UseChatReturn {
  // Current conversation
  conversation: Conversation | null;
  messages: Message[];

  // UI state
  loading: boolean;
  error: string | null;
  isGenerating: boolean;

  // Actions
  sendMessage: (message: string, modelId?: string) => Promise<void>;
  createNewConversation: (title?: string, modelId?: string) => Promise<void>;
  loadConversation: (conversationId: string) => Promise<void>;
  updateConversationModel: (modelId: string) => Promise<void>;
  clearError: () => void;
}

export function useChat(): UseChatReturn {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const createNewConversation = useCallback(async (title?: string, modelId?: string) => {
    try {
      setLoading(true);
      setError(null);

      const newConversation = await api.conversations.create({
        title,
        preferred_model: modelId,
      });

      setConversation(newConversation);
      setMessages([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation');
      console.error('Failed to create conversation:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadConversation = useCallback(async (conversationId: string) => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.conversations.get(conversationId);

      setConversation({
        id: response.id,
        title: response.title,
        user_id: '', // Will be populated by the API response in real usage
        project_id: response.project_id,
        is_starred: false, // Will be populated by the API response in real usage
        preferred_model: response.preferred_model,
        created_at: response.created_at,
        updated_at: response.updated_at,
      } as Conversation);

      setMessages(response.messages || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation');
      console.error('Failed to load conversation:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const updateConversationModel = useCallback(async (modelId: string) => {
    if (!conversation) return;

    try {
      setError(null);

      await api.conversations.update(conversation.id, {
        preferred_model: modelId,
      });

      setConversation(prev =>
        prev ? { ...prev, preferred_model: modelId } : null
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update model preference');
      console.error('Failed to update model preference:', err);
    }
  }, [conversation]);

  const sendMessage = useCallback(async (message: string, modelId?: string) => {
    if (!message.trim()) return;

    try {
      setIsGenerating(true);
      setError(null);

      // Create user message
      const userMessage: Message = {
        id: Date.now().toString(), // Temporary ID
        conversation_id: conversation?.id || '',
        role: 'user',
        content: message.trim(),
        created_at: new Date().toISOString(),
      };

      // Add user message to UI immediately
      setMessages(prev => [...prev, userMessage]);

      // Send to API
      const response = await api.chat.sendMessage({
        conversation_id: conversation?.id,
        message: message.trim(),
        model: modelId || conversation?.preferred_model,
        history: messages,
      });

      // Create assistant message from response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(), // Temporary ID
        conversation_id: response.conversation_id || conversation?.id || '',
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString(),
        metadata: {
          model: response.model,
          tokens_used: 0, // Could be populated from response if available
        },
      };

      // Add assistant message to UI
      setMessages(prev => [...prev, assistantMessage]);

      // Update conversation ID if this was a new conversation
      if (!conversation && response.conversation_id) {
        // Load the full conversation data
        await loadConversation(response.conversation_id);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      console.error('Failed to send message:', err);

      // Remove the user message from UI if sending failed
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsGenerating(false);
    }
  }, [conversation, messages, loadConversation]);

  return {
    conversation,
    messages,
    loading,
    error,
    isGenerating,
    sendMessage,
    createNewConversation,
    loadConversation,
    updateConversationModel,
    clearError,
  };
}