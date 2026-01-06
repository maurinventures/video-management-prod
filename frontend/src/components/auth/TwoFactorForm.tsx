/**
 * Two-Factor Authentication Form
 *
 * Handles 2FA code verification and backup code entry.
 */

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';

interface TwoFactorFormProps {
  onSuccess?: () => void;
  onBackToLogin?: () => void;
}

export function TwoFactorForm({ onSuccess, onBackToLogin }: TwoFactorFormProps) {
  const { verify2FA, verifyBackupCode, isLoading, error, clearError, pendingVerification } = useAuth();
  const [code, setCode] = useState('');
  const [useBackupCode, setUseBackupCode] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus the input when component mounts
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [useBackupCode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (!code.trim()) {
      return;
    }

    const result = useBackupCode
      ? await verifyBackupCode(code.replace(/\s/g, '').toUpperCase())
      : await verify2FA(code.replace(/\s/g, ''));

    if (result.success) {
      onSuccess?.();
    }
  };

  const handleCodeChange = (value: string) => {
    // For regular 2FA codes, only allow 6 digits
    if (!useBackupCode) {
      const cleanValue = value.replace(/\D/g, '');
      if (cleanValue.length <= 6) {
        setCode(cleanValue);
      }
    } else {
      // For backup codes, allow alphanumeric
      const cleanValue = value.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
      if (cleanValue.length <= 8) {
        setCode(cleanValue);
      }
    }
    clearError();
  };

  const toggleBackupCode = () => {
    setCode('');
    setUseBackupCode(!useBackupCode);
    clearError();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            {useBackupCode ? 'Enter Backup Code' : 'Two-Factor Authentication'}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            {useBackupCode ? (
              <>Enter one of your backup codes to sign in</>
            ) : (
              <>
                Enter the 6-digit code from your authenticator app
                {pendingVerification.email && (
                  <>
                    <br />
                    <span className="font-medium">{pendingVerification.email}</span>
                  </>
                )}
              </>
            )}
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{error}</div>
            </div>
          )}

          <div>
            <label htmlFor="code" className="block text-sm font-medium text-gray-700">
              {useBackupCode ? 'Backup Code' : 'Authentication Code'}
            </label>
            <input
              ref={inputRef}
              id="code"
              name="code"
              type="text"
              autoComplete="one-time-code"
              required
              className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm text-center font-mono text-lg"
              placeholder={useBackupCode ? 'ABC12345' : '123456'}
              value={code}
              onChange={(e) => handleCodeChange(e.target.value)}
              disabled={isLoading}
              maxLength={useBackupCode ? 8 : 6}
            />
            <div className="mt-2 text-xs text-gray-500 text-center">
              {useBackupCode ? (
                'Backup codes are 8 characters long'
              ) : (
                'Enter the 6-digit code from your authenticator app'
              )}
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading || !code.trim()}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <span className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Verifying...
                </span>
              ) : (
                'Verify & Sign In'
              )}
            </button>
          </div>

          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={toggleBackupCode}
              className="text-sm text-blue-600 hover:text-blue-500 font-medium"
              disabled={isLoading}
            >
              {useBackupCode ? 'Use authenticator app' : 'Use backup code instead'}
            </button>

            <button
              type="button"
              onClick={onBackToLogin}
              className="text-sm text-gray-600 hover:text-gray-500"
              disabled={isLoading}
            >
              Back to login
            </button>
          </div>

          <div className="rounded-md bg-blue-50 p-4">
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">Can't access your codes?</p>
              <p>
                If you've lost access to your authenticator app and backup codes,
                contact your administrator for account recovery.
              </p>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}