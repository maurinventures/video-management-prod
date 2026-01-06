/**
 * Two-Factor Authentication Setup Component
 *
 * Handles mandatory 2FA setup for new users or when 2FA is not configured.
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';

interface TwoFactorSetupProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function TwoFactorSetup({ onSuccess, onCancel }: TwoFactorSetupProps) {
  const { setup2FA, generateBackupCodes, isLoading, error, clearError, pendingVerification } = useAuth();
  const [step, setStep] = useState<'generate' | 'verify' | 'backup-codes'>('generate');
  const [qrCode, setQrCode] = useState<string>('');
  const [secret, setSecret] = useState<string>('');
  const [verificationCode, setVerificationCode] = useState<string>('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);

  useEffect(() => {
    // Generate QR code when component mounts
    generateQRCode();
  }, []);

  const generateQRCode = async () => {
    try {
      const result = await setup2FA();
      if (result.success && result.qrCode && result.secret) {
        setQrCode(result.qrCode);
        setSecret(result.secret);
      }
    } catch (error) {
      console.error('Failed to generate 2FA setup:', error);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (!verificationCode.trim()) {
      return;
    }

    const result = await setup2FA(verificationCode.replace(/\s/g, ''));

    if (result.success) {
      // 2FA setup successful, now generate backup codes
      const backupResult = await generateBackupCodes();
      if (backupResult.success && backupResult.codes) {
        setBackupCodes(backupResult.codes);
        setStep('backup-codes');
      } else {
        // Even if backup codes fail, 2FA is set up
        onSuccess?.();
      }
    }
  };

  const handleCodeChange = (value: string) => {
    const cleanValue = value.replace(/\D/g, '');
    if (cleanValue.length <= 6) {
      setVerificationCode(cleanValue);
    }
    clearError();
  };

  const handleFinishSetup = () => {
    onSuccess?.();
  };

  const formatSecret = (secret: string) => {
    return secret.match(/.{1,4}/g)?.join(' ') || secret;
  };

  if (step === 'generate') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <div>
            <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
              Set up Two-Factor Authentication
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              Two-factor authentication is required for all accounts
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
              <div className="text-center">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Step 1: Scan QR Code
                </h3>
                {qrCode ? (
                  <div className="flex justify-center mb-4">
                    <img
                      src={`data:image/png;base64,${qrCode}`}
                      alt="2FA QR Code"
                      className="border border-gray-200 rounded"
                    />
                  </div>
                ) : (
                  <div className="flex justify-center items-center h-48 bg-gray-100 rounded">
                    <div className="text-gray-500">Generating QR code...</div>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <p className="text-sm text-gray-600">
                  1. Install an authenticator app like Google Authenticator, Authy, or 1Password
                </p>
                <p className="text-sm text-gray-600">
                  2. Scan the QR code above with your authenticator app
                </p>
                <p className="text-sm text-gray-600">
                  3. Enter the 6-digit code from your app to verify
                </p>
              </div>

              {secret && (
                <div className="mt-4 p-3 bg-gray-50 rounded">
                  <p className="text-xs text-gray-600 mb-1">
                    Can't scan? Enter this code manually:
                  </p>
                  <code className="text-sm font-mono text-gray-900 select-all">
                    {formatSecret(secret)}
                  </code>
                </div>
              )}

              <button
                onClick={() => setStep('verify')}
                disabled={!qrCode}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue to Verification
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (step === 'verify') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <div>
            <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
              Verify Two-Factor Authentication
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              Enter the 6-digit code from your authenticator app
            </p>
          </div>

          <form className="mt-8 space-y-6" onSubmit={handleVerifyCode}>
            {error && (
              <div className="rounded-md bg-red-50 p-4">
                <div className="text-sm text-red-800">{error}</div>
              </div>
            )}

            <div>
              <label htmlFor="verification-code" className="block text-sm font-medium text-gray-700">
                Authentication Code
              </label>
              <input
                id="verification-code"
                name="verification-code"
                type="text"
                autoComplete="one-time-code"
                required
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm text-center font-mono text-lg"
                placeholder="123456"
                value={verificationCode}
                onChange={(e) => handleCodeChange(e.target.value)}
                disabled={isLoading}
                maxLength={6}
                autoFocus
              />
            </div>

            <div className="flex space-x-4">
              <button
                type="button"
                onClick={() => setStep('generate')}
                disabled={isLoading}
                className="flex-1 flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Back
              </button>

              <button
                type="submit"
                disabled={isLoading || !verificationCode.trim() || verificationCode.length !== 6}
                className="flex-1 flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
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
                  'Verify & Complete Setup'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  if (step === 'backup-codes') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <div>
            <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
              Save Your Backup Codes
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              Store these backup codes in a safe place. You can use them to access your account if you lose your authenticator device.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-2">
                {backupCodes.map((code, index) => (
                  <div key={index} className="p-2 bg-gray-50 rounded font-mono text-sm text-center">
                    {code}
                  </div>
                ))}
              </div>

              <div className="rounded-md bg-yellow-50 p-4">
                <div className="text-sm text-yellow-800">
                  <p className="font-medium mb-1">Important:</p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>Each backup code can only be used once</li>
                    <li>Store them securely (password manager, safe, etc.)</li>
                    <li>Don't share them with anyone</li>
                    <li>You can generate new codes anytime from your settings</li>
                  </ul>
                </div>
              </div>

              <div className="flex space-x-4">
                <button
                  onClick={() => {
                    const codesText = backupCodes.join('\n');
                    navigator.clipboard.writeText(codesText).then(() => {
                      alert('Backup codes copied to clipboard');
                    }).catch(() => {
                      // Fallback for browsers that don't support clipboard API
                      const textArea = document.createElement('textarea');
                      textArea.value = codesText;
                      document.body.appendChild(textArea);
                      textArea.select();
                      document.execCommand('copy');
                      document.body.removeChild(textArea);
                      alert('Backup codes copied to clipboard');
                    });
                  }}
                  className="flex-1 flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Copy Codes
                </button>

                <button
                  onClick={() => window.print()}
                  className="flex-1 flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Print Codes
                </button>
              </div>

              <button
                onClick={handleFinishSetup}
                className="w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
              >
                I've Saved My Backup Codes - Continue
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}