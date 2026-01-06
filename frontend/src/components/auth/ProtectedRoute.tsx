/**
 * Protected Route Component
 *
 * Wrapper component that ensures user is authenticated before showing protected content.
 */

import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { AuthRouter } from './AuthRouter';

interface ProtectedRouteProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function ProtectedRoute({ children, fallback }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-sm text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Show auth flow if not authenticated
  if (!isAuthenticated || !user) {
    if (fallback) {
      return <>{fallback}</>;
    }

    return (
      <AuthRouter
        onAuthSuccess={() => {
          // Auth success is handled by the AuthContext
          // The component will re-render when isAuthenticated becomes true
        }}
      />
    );
  }

  // User is authenticated, show protected content
  return <>{children}</>;
}

/**
 * Higher-order component version of ProtectedRoute
 */
export function withAuthRequired<P extends object>(
  Component: React.ComponentType<P>
) {
  return function AuthRequiredComponent(props: P) {
    return (
      <ProtectedRoute>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
}