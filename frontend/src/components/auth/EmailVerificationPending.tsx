/**
 * Email Verification Pending Component
 *
 * Shows after registration when email verification is required.
 */

import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';

interface EmailVerificationPendingProps {
  onBackToLogin?: () => void;
}

export function EmailVerificationPending({ onBackToLogin }: EmailVerificationPendingProps) {
  const { resendVerificationEmail, pendingVerification, error, clearError } = useAuth();
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);

  const handleResendEmail = async () => {
    setResendLoading(true);
    setResendSuccess(false);
    clearError();

    const result = await resendVerificationEmail();

    if (result.success) {
      setResendSuccess(true);
    }

    setResendLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100">
            <svg
              className="h-6 w-6 text-blue-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Check your email
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            We've sent a verification link to
            {pendingVerification.email && (
              <>
                <br />
                <span className="font-medium">{pendingVerification.email}</span>
              </>
            )}
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="space-y-4">
            {error && (
              <div className="rounded-md bg-red-50 p-4">
                <div className="text-sm text-red-800">{error}</div>
              </div>
            )}

            {resendSuccess && (
              <div className="rounded-md bg-green-50 p-4">
                <div className="text-sm text-green-800">
                  Verification email sent successfully! Check your inbox.
                </div>
              </div>
            )}

            <div className="text-center space-y-4">
              <div className="text-sm text-gray-600">
                <p className="mb-2">
                  Click the link in the email to verify your account and complete registration.
                </p>
                <p className="mb-4">
                  After verification, you'll need to set up two-factor authentication.
                </p>
              </div>

              <div className="space-y-2">
                <button
                  onClick={handleResendEmail}
                  disabled={resendLoading}
                  className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {resendLoading ? (
                    <span className="flex items-center">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Sending...
                    </span>
                  ) : (
                    'Resend verification email'
                  )}
                </button>

                <button
                  onClick={onBackToLogin}
                  className="w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-blue-600 bg-blue-50 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Back to login
                </button>
              </div>
            </div>

            <div className="mt-6">
              <div className="text-xs text-gray-500">
                <p className="mb-2">
                  <strong>Didn't receive the email?</strong>
                </p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Check your spam/junk folder</li>
                  <li>Make sure you entered the correct email address</li>
                  <li>Try resending the verification email</li>
                  <li>Contact support if you continue to have issues</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}