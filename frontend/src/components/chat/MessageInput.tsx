/**
 * Message Input Component
 *
 * Input field for typing and sending chat messages with keyboard shortcuts and state management.
 */

import React, { useState, useRef, KeyboardEvent } from 'react';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function MessageInput({
  onSendMessage,
  disabled = false,
  placeholder = "Type your message..."
}: MessageInputProps) {
  const [message, setMessage] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();

    if (!message.trim() || disabled) return;

    onSendMessage(message.trim());
    setMessage('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Handle Enter key (send message)
    if (e.key === 'Enter') {
      if (e.shiftKey || e.metaKey || e.ctrlKey || isComposing) {
        // Allow line break with Shift+Enter or during IME composition
        return;
      } else {
        // Send message with Enter
        e.preventDefault();
        handleSubmit();
      }
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setMessage(value);

    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    const scrollHeight = textarea.scrollHeight;
    const maxHeight = 120; // Roughly 5 lines
    textarea.style.height = Math.min(scrollHeight, maxHeight) + 'px';
  };

  const handleCompositionStart = () => {
    setIsComposing(true);
  };

  const handleCompositionEnd = () => {
    setIsComposing(false);
  };

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <form onSubmit={handleSubmit} className="flex items-end space-x-3">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            onCompositionStart={handleCompositionStart}
            onCompositionEnd={handleCompositionEnd}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                     disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed
                     resize-none text-sm"
            style={{
              minHeight: '40px',
              maxHeight: '120px'
            }}
          />

          {/* Character count indicator (optional) */}
          {message.length > 500 && (
            <div className="absolute bottom-1 right-2 text-xs text-gray-400">
              {message.length}/1000
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={!message.trim() || disabled}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent
                   text-sm font-medium rounded-md shadow-sm text-white bg-blue-600
                   hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2
                   focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed
                   transition-colors duration-200"
        >
          {disabled ? (
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>Sending...</span>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
              <span>Send</span>
            </div>
          )}
        </button>
      </form>

      {/* Help text */}
      <div className="mt-2 text-xs text-gray-500">
        Press Enter to send, Shift+Enter for a new line
      </div>
    </div>
  );
}