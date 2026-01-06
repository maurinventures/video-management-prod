/**
 * Authentication Router Component
 *
 * Manages routing between different authentication states and forms.
 */

import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { LoginForm } from './LoginForm';
import { TwoFactorForm } from './TwoFactorForm';
import { TwoFactorSetup } from './TwoFactorSetup';
import { RegisterForm } from './RegisterForm';
import { EmailVerificationPending } from './EmailVerificationPending';

interface AuthRouterProps {
  onAuthSuccess?: () => void;
  initialView?: 'login' | 'register';
}

export function AuthRouter({ onAuthSuccess, initialView = 'login' }: AuthRouterProps) {
  const { pendingVerification, isAuthenticated } = useAuth();
  const [currentView, setCurrentView] = React.useState<'login' | 'register' | '2fa' | '2fa-setup' | 'email-verification'>(initialView);

  // If user is authenticated, call success callback
  React.useEffect(() => {
    if (isAuthenticated) {
      onAuthSuccess?.();
    }
  }, [isAuthenticated, onAuthSuccess]);

  // Handle pending verification states
  React.useEffect(() => {
    if (pendingVerification.type) {
      switch (pendingVerification.type) {
        case '2fa':
          setCurrentView('2fa');
          break;
        case '2fa-setup':
          setCurrentView('2fa-setup');
          break;
        case 'email':
          setCurrentView('email-verification');
          break;
      }
    }
  }, [pendingVerification]);

  const handleLoginSuccess = () => {
    onAuthSuccess?.();
  };

  const handleLoginRequire2FA = () => {
    setCurrentView('2fa');
  };

  const handleLoginRequire2FASetup = () => {
    setCurrentView('2fa-setup');
  };

  const handleRegisterSuccess = () => {
    onAuthSuccess?.();
  };

  const handleRegisterRequireEmailVerification = () => {
    setCurrentView('email-verification');
  };

  const handle2FASuccess = () => {
    onAuthSuccess?.();
  };

  const handle2FASetupSuccess = () => {
    onAuthSuccess?.();
  };

  const handleBackToLogin = () => {
    setCurrentView('login');
  };

  const handleSwitchToRegister = () => {
    setCurrentView('register');
  };

  const handleSwitchToLogin = () => {
    setCurrentView('login');
  };

  // Don't render anything if user is already authenticated
  if (isAuthenticated) {
    return null;
  }

  switch (currentView) {
    case 'login':
      return (
        <LoginForm
          onSuccess={handleLoginSuccess}
          onRequire2FA={handleLoginRequire2FA}
          onRequire2FASetup={handleLoginRequire2FASetup}
        />
      );

    case 'register':
      return (
        <RegisterForm
          onSuccess={handleRegisterSuccess}
          onRequireEmailVerification={handleRegisterRequireEmailVerification}
        />
      );

    case '2fa':
      return (
        <TwoFactorForm
          onSuccess={handle2FASuccess}
          onBackToLogin={handleBackToLogin}
        />
      );

    case '2fa-setup':
      return (
        <TwoFactorSetup
          onSuccess={handle2FASetupSuccess}
          onCancel={handleBackToLogin}
        />
      );

    case 'email-verification':
      return (
        <EmailVerificationPending
          onBackToLogin={handleBackToLogin}
        />
      );

    default:
      return (
        <LoginForm
          onSuccess={handleLoginSuccess}
          onRequire2FA={handleLoginRequire2FA}
          onRequire2FASetup={handleLoginRequire2FASetup}
        />
      );
  }
}