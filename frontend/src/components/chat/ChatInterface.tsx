/**
 * Chat Interface Component
 *
 * Main chat interface that integrates model selection, message display, and message input.
 * Implements prompt 9 requirements for React chat with model selector.
 */

import React, { useEffect, useState } from 'react';
import { useChat } from '../../hooks/useChat';
import { useModels } from '../../hooks/useModels';
import { ModelSelector } from './ModelSelector';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';

interface ChatInterfaceProps {
  conversationId?: string;
  className?: string;
}

export function ChatInterface({ conversationId, className = '' }: ChatInterfaceProps) {
  const {
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
  } = useChat();

  const { models, defaultModel, loading: modelsLoading, getModelById } = useModels();

  const [selectedModel, setSelectedModel] = useState<string>('');

  // Initialize conversation and selected model
  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    } else {
      // Set default model for new conversations
      setSelectedModel(defaultModel);
    }
  }, [conversationId, defaultModel, loadConversation]);

  // Update selected model when conversation loads
  useEffect(() => {
    if (conversation?.preferred_model) {
      setSelectedModel(conversation.preferred_model);
    }
  }, [conversation?.preferred_model]);

  const handleModelChange = async (modelId: string) => {
    setSelectedModel(modelId);

    if (conversation) {
      // Update existing conversation's model preference
      await updateConversationModel(modelId);
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!conversation && !conversationId) {
      // Create a new conversation if one doesn't exist
      await createNewConversation(undefined, selectedModel);
    }

    await sendMessage(message, selectedModel);
  };

  const selectedModelInfo = getModelById(selectedModel);

  return (
    <div className={`flex flex-col h-full bg-white rounded-lg shadow ${className}`}>
      {/* Header with model selector and conversation info */}
      <div className="flex-shrink-0 border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900">
              {conversation?.title || 'New Conversation'}
            </h2>
            {conversation && (
              <p className="text-sm text-gray-500 mt-1">
                Created {new Date(conversation.created_at).toLocaleDateString()}
              </p>
            )}
          </div>

          {/* Model Selector */}
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                AI Model
              </label>
              <ModelSelector
                selectedModel={selectedModel}
                onModelChange={handleModelChange}
                disabled={modelsLoading || isGenerating}
                size="sm"
              />
            </div>
          </div>
        </div>

        {/* Model info display */}
        {selectedModelInfo && (
          <div className="mt-3 p-3 bg-gray-50 rounded-md">
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                  selectedModelInfo.provider === 'anthropic' ? 'bg-orange-500' : 'bg-green-500'
                }`}>
                  <span className="text-white text-xs font-bold">
                    {selectedModelInfo.provider === 'anthropic' ? 'A' : 'O'}
                  </span>
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900">
                  {selectedModelInfo.name}
                </p>
                <p className="text-xs text-gray-500">
                  {selectedModelInfo.description}
                </p>
              </div>
              <div className="flex-shrink-0">
                <span className="text-xs text-gray-400">
                  {(selectedModelInfo.context_window / 1000).toFixed(0)}K context
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Error display */}
        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <div className="mt-1 text-sm text-red-700">{error}</div>
                <button
                  onClick={clearError}
                  className="mt-2 text-sm font-medium text-red-800 hover:text-red-600"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center space-x-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="text-gray-600">Loading conversation...</span>
            </div>
          </div>
        ) : (
          <MessageList messages={messages} isGenerating={isGenerating} />
        )}
      </div>

      {/* Message input */}
      <div className="flex-shrink-0">
        <MessageInput
          onSendMessage={handleSendMessage}
          disabled={isGenerating || loading || modelsLoading || !selectedModel}
          placeholder={
            !selectedModel
              ? 'Please select a model first...'
              : isGenerating
              ? 'AI is responding...'
              : 'Type your message...'
          }
        />
      </div>
    </div>
  );
}

/**
 * Chat Page Component
 *
 * Full-page layout for the chat interface with proper layout structure.
 */
export function ChatPage() {
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header could be imported from layout components */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-xl font-bold text-gray-900">Internal Platform Chat</h1>
          </div>
        </div>
      </div>

      {/* Main chat area */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-[calc(100vh-12rem)]">
          <ChatInterface className="h-full" />
        </div>
      </div>
    </div>
  );
}