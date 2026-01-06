/**
 * Authentication Context for Internal Platform
 *
 * Manages user authentication state and provides auth methods
 * throughout the React application.
 */

import React, { createContext, useContext, useEffect, useReducer, ReactNode } from 'react';
import api from '../lib/api';
import { User } from '../types';

// Auth state interface
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  pendingVerification: {
    type: 'email' | '2fa' | '2fa-setup' | null;
    email?: string;
    userId?: string;
  };
}

// Auth actions
type AuthAction =
  | { type: 'AUTH_START' }
  | { type: 'AUTH_SUCCESS'; payload: { user: User } }
  | { type: 'AUTH_ERROR'; payload: { error: string } }
  | { type: 'AUTH_LOGOUT' }
  | { type: 'SET_PENDING_VERIFICATION'; payload: { type: 'email' | '2fa' | '2fa-setup'; email?: string; userId?: string } }
  | { type: 'CLEAR_PENDING_VERIFICATION' }
  | { type: 'CLEAR_ERROR' };

// Initial state
const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: true, // Start with loading true to check existing session
  error: null,
  pendingVerification: { type: null },
};

// Auth reducer
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'AUTH_START':
      return {
        ...state,
        isLoading: true,
        error: null,
      };

    case 'AUTH_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        pendingVerification: { type: null },
      };

    case 'AUTH_ERROR':
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: action.payload.error,
      };

    case 'AUTH_LOGOUT':
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        pendingVerification: { type: null },
      };

    case 'SET_PENDING_VERIFICATION':
      return {
        ...state,
        isLoading: false,
        pendingVerification: action.payload,
      };

    case 'CLEAR_PENDING_VERIFICATION':
      return {
        ...state,
        pendingVerification: { type: null },
      };

    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };

    default:
      return state;
  }
}

// Context interface
interface AuthContextType {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  pendingVerification: AuthState['pendingVerification'];

  // Actions
  login: (email: string, password: string) => Promise<{ success: boolean; requiresVerification?: '2fa' | '2fa-setup' }>;
  logout: () => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<{ success: boolean; requiresEmailVerification?: boolean }>;
  verify2FA: (token: string) => Promise<{ success: boolean }>;
  setup2FA: (token?: string) => Promise<{ success: boolean; qrCode?: string; secret?: string }>;
  verifyEmail: (token: string) => Promise<{ success: boolean }>;
  resendVerificationEmail: () => Promise<{ success: boolean }>;
  generateBackupCodes: () => Promise<{ success: boolean; codes?: string[] }>;
  verifyBackupCode: (code: string) => Promise<{ success: boolean }>;
  clearError: () => void;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Auth provider component
interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Check for existing session on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      dispatch({ type: 'AUTH_START' });

      // Try to get current user info - this will fail if not authenticated
      const response = await api.auth.me();

      dispatch({
        type: 'AUTH_SUCCESS',
        payload: { user: response.user },
      });
    } catch (error) {
      // No valid session - this is expected for logged-out users
      dispatch({ type: 'AUTH_LOGOUT' });
    }
  };

  const login = async (email: string, password: string): Promise<{ success: boolean; requiresVerification?: '2fa' | '2fa-setup' }> => {
    try {
      dispatch({ type: 'AUTH_START' });

      const response = await api.auth.login(email, password);

      if (response.success) {
        if (response.requires_2fa) {
          dispatch({
            type: 'SET_PENDING_VERIFICATION',
            payload: { type: '2fa', email, userId: response.user_id },
          });
          return { success: true, requiresVerification: '2fa' };
        } else if (response.requires_2fa_setup) {
          dispatch({
            type: 'SET_PENDING_VERIFICATION',
            payload: { type: '2fa-setup', email, userId: response.user_id },
          });
          return { success: true, requiresVerification: '2fa-setup' };
        } else if (response.user) {
          // Direct login success
          dispatch({
            type: 'AUTH_SUCCESS',
            payload: { user: response.user },
          });
          return { success: true };
        } else {
          // Unexpected response format
          dispatch({
            type: 'AUTH_ERROR',
            payload: { error: 'Invalid login response' },
          });
          return { success: false };
        }
      } else {
        dispatch({
          type: 'AUTH_ERROR',
          payload: { error: response.error || 'Login failed' },
        });
        return { success: false };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Login failed';
      dispatch({
        type: 'AUTH_ERROR',
        payload: { error: errorMessage },
      });
      return { success: false };
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await api.auth.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      dispatch({ type: 'AUTH_LOGOUT' });
    }
  };

  const register = async (name: string, email: string, password: string): Promise<{ success: boolean; requiresEmailVerification?: boolean }> => {
    try {
      dispatch({ type: 'AUTH_START' });

      const response = await api.auth.register(name, email, password);

      if (response.success) {
        if (response.requires_email_verification) {
          dispatch({
            type: 'SET_PENDING_VERIFICATION',
            payload: { type: 'email', email },
          });
          return { success: true, requiresEmailVerification: true };
        } else if (response.user) {
          // Auto-login after registration
          dispatch({
            type: 'AUTH_SUCCESS',
            payload: { user: response.user },
          });
          return { success: true };
        } else {
          // Registration successful but no immediate login
          dispatch({ type: 'CLEAR_PENDING_VERIFICATION' });
          return { success: true };
        }
      } else {
        dispatch({
          type: 'AUTH_ERROR',
          payload: { error: response.error || 'Registration failed' },
        });
        return { success: false };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Registration failed';
      dispatch({
        type: 'AUTH_ERROR',
        payload: { error: errorMessage },
      });
      return { success: false };
    }
  };

  const verify2FA = async (token: string): Promise<{ success: boolean }> => {
    try {
      const response = await api.auth.verify2FA(token);

      if (response.success && response.user) {
        dispatch({
          type: 'AUTH_SUCCESS',
          payload: { user: response.user },
        });
        return { success: true };
      } else {
        dispatch({
          type: 'AUTH_ERROR',
          payload: { error: response.error || '2FA verification failed' },
        });
        return { success: false };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '2FA verification failed';
      dispatch({
        type: 'AUTH_ERROR',
        payload: { error: errorMessage },
      });
      return { success: false };
    }
  };

  const setup2FA = async (token?: string): Promise<{ success: boolean; qrCode?: string; secret?: string }> => {
    try {
      const response = await api.auth.setup2FA(token);

      if (response.success) {
        if (token && response.user) {
          // 2FA setup completed
          dispatch({
            type: 'AUTH_SUCCESS',
            payload: { user: response.user },
          });
          return { success: true };
        } else if (!token) {
          // Initial setup - return QR code and secret
          return {
            success: true,
            qrCode: response.qr_code,
            secret: response.secret,
          };
        } else {
          // Token provided but no user returned - error
          dispatch({
            type: 'AUTH_ERROR',
            payload: { error: 'Invalid 2FA setup response' },
          });
          return { success: false };
        }
      } else {
        dispatch({
          type: 'AUTH_ERROR',
          payload: { error: response.error || '2FA setup failed' },
        });
        return { success: false };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '2FA setup failed';
      dispatch({
        type: 'AUTH_ERROR',
        payload: { error: errorMessage },
      });
      return { success: false };
    }
  };

  const verifyEmail = async (token: string): Promise<{ success: boolean }> => {
    try {
      const response = await api.auth.verifyEmail(token);

      if (response.success) {
        dispatch({ type: 'CLEAR_PENDING_VERIFICATION' });
        return { success: true };
      } else {
        dispatch({
          type: 'AUTH_ERROR',
          payload: { error: response.error || 'Email verification failed' },
        });
        return { success: false };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Email verification failed';
      dispatch({
        type: 'AUTH_ERROR',
        payload: { error: errorMessage },
      });
      return { success: false };
    }
  };

  const resendVerificationEmail = async (): Promise<{ success: boolean }> => {
    try {
      const response = await api.auth.resendVerificationEmail();

      if (!response.success) {
        dispatch({
          type: 'AUTH_ERROR',
          payload: { error: response.error || 'Failed to resend verification email' },
        });
      }

      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to resend verification email';
      dispatch({
        type: 'AUTH_ERROR',
        payload: { error: errorMessage },
      });
      return { success: false };
    }
  };

  const generateBackupCodes = async (): Promise<{ success: boolean; codes?: string[] }> => {
    try {
      const response = await api.auth.generateBackupCodes();

      if (!response.success) {
        dispatch({
          type: 'AUTH_ERROR',
          payload: { error: response.error || 'Failed to generate backup codes' },
        });
      }

      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate backup codes';
      dispatch({
        type: 'AUTH_ERROR',
        payload: { error: errorMessage },
      });
      return { success: false };
    }
  };

  const verifyBackupCode = async (code: string): Promise<{ success: boolean }> => {
    try {
      const response = await api.auth.verifyBackupCode(code);

      if (response.success && response.user) {
        dispatch({
          type: 'AUTH_SUCCESS',
          payload: { user: response.user },
        });
        return { success: true };
      } else {
        dispatch({
          type: 'AUTH_ERROR',
          payload: { error: response.error || 'Invalid backup code' },
        });
        return { success: false };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Backup code verification failed';
      dispatch({
        type: 'AUTH_ERROR',
        payload: { error: errorMessage },
      });
      return { success: false };
    }
  };

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  const contextValue: AuthContextType = {
    // State
    user: state.user,
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    error: state.error,
    pendingVerification: state.pendingVerification,

    // Actions
    login,
    logout,
    register,
    verify2FA,
    setup2FA,
    verifyEmail,
    resendVerificationEmail,
    generateBackupCodes,
    verifyBackupCode,
    clearError,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook to use auth context
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}