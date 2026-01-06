/**
 * Example hook demonstrating proper API client usage
 *
 * This shows how components should use the API client instead of direct fetch() calls.
 */

import { useState, useEffect } from 'react';
import api from '../lib/api';
import { Conversation } from '../types';

interface UseConversationsReturn {
  conversations: Conversation[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  createConversation: (title?: string, projectId?: string) => Promise<Conversation | null>;
  updateConversation: (id: string, data: { title?: string }) => Promise<boolean>;
  deleteConversation: (id: string) => Promise<boolean>;
}

export function useConversations(): UseConversationsReturn {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConversations = async () => {
    try {
      setLoading(true);
      setError(null);

      // Use API client instead of direct fetch()
      const data = await api.conversations.list();
      setConversations(data.conversations);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch conversations');
      console.error('Failed to fetch conversations:', err);
    } finally {
      setLoading(false);
    }
  };

  const createConversation = async (title?: string, projectId?: string): Promise<Conversation | null> => {
    try {
      setError(null);

      // Use API client
      const newConversation = await api.conversations.create({
        title,
        project_id: projectId
      });

      // Update local state
      setConversations(prev => [newConversation, ...prev]);

      return newConversation;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation');
      console.error('Failed to create conversation:', err);
      return null;
    }
  };

  const updateConversation = async (id: string, data: { title?: string }): Promise<boolean> => {
    try {
      setError(null);

      // Use API client
      await api.conversations.update(id, data);

      // Update local state
      setConversations(prev =>
        prev.map(conv =>
          conv.id === id
            ? { ...conv, ...data, updated_at: new Date().toISOString() }
            : conv
        )
      );

      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update conversation');
      console.error('Failed to update conversation:', err);
      return false;
    }
  };

  const deleteConversation = async (id: string): Promise<boolean> => {
    try {
      setError(null);

      // Use API client
      await api.conversations.delete(id);

      // Update local state
      setConversations(prev => prev.filter(conv => conv.id !== id));

      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete conversation');
      console.error('Failed to delete conversation:', err);
      return false;
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchConversations();
  }, []);

  return {
    conversations,
    loading,
    error,
    refetch: fetchConversations,
    createConversation,
    updateConversation,
    deleteConversation,
  };
}