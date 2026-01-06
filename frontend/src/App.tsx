import React from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Header } from './components/layout/Header';
import { ChatInterface } from './components/chat/ChatInterface';

// Dashboard component with chat interface for testing
function Dashboard() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Internal Platform - Chat Demo" />
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Welcome banner */}
          <div className="mb-6 bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Chat with AI Models
            </h2>
            <p className="text-gray-600">
              Test the chat interface with model selection. Choose between Claude and OpenAI models.
            </p>
          </div>

          {/* Chat interface */}
          <div className="h-[600px]">
            <ChatInterface className="h-full" />
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      </div>
    </AuthProvider>
  );
}

export default App;
