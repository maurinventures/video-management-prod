import React from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Header } from './components/layout/Header';
import { ChatInterface } from './components/chat/ChatInterface';
import { UsageDisplay } from './components/usage/UsageDisplay';

// Dashboard component with chat interface and usage display for testing
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
              Test the chat interface with model selection and monitor your usage.
            </p>
          </div>

          {/* Main content grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Chat interface - takes up 2/3 on large screens */}
            <div className="lg:col-span-2">
              <div className="h-[600px] bg-white rounded-lg shadow">
                <ChatInterface className="h-full" />
              </div>
            </div>

            {/* Usage display - takes up 1/3 on large screens */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg shadow">
                <UsageDisplay />
              </div>
            </div>
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
