/**
 * Model Selector Component
 *
 * Dropdown for selecting AI models with provider grouping and recommendations.
 */

import React, { useState } from 'react';
import { useModels } from '../../hooks/useModels';
import { AIModel } from '../../types';

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function ModelSelector({
  selectedModel,
  onModelChange,
  disabled = false,
  size = 'md',
}: ModelSelectorProps) {
  const { models, loading, error, getModelById } = useModels();
  const [isOpen, setIsOpen] = useState(false);

  if (loading) {
    return (
      <div className="flex items-center space-x-2">
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
        <span className="text-sm text-gray-600">Loading models...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-600">
        Failed to load models: {error}
      </div>
    );
  }

  const selectedModelInfo = getModelById(selectedModel);

  const groupedModels = {
    anthropic: models.filter(m => m.provider === 'anthropic'),
    openai: models.filter(m => m.provider === 'openai'),
  };

  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-2',
    lg: 'text-base px-4 py-3',
  };

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          relative w-full bg-white border border-gray-300 rounded-md shadow-sm
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          text-left cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed
          hover:bg-gray-50
          ${sizeClasses[size]}
        `}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {selectedModelInfo && (
              <>
                <div className={`flex-shrink-0 ${iconSizes[size]}`}>
                  {selectedModelInfo.provider === 'anthropic' ? (
                    <div className="bg-orange-500 rounded-full h-full w-full flex items-center justify-center">
                      <span className="text-white text-xs font-bold">A</span>
                    </div>
                  ) : (
                    <div className="bg-green-500 rounded-full h-full w-full flex items-center justify-center">
                      <span className="text-white text-xs font-bold">O</span>
                    </div>
                  )}
                </div>
                <div>
                  <span className="font-medium text-gray-900">
                    {selectedModelInfo.name}
                  </span>
                  {selectedModelInfo.is_recommended && (
                    <span className="ml-1 text-xs bg-blue-100 text-blue-800 px-1 rounded">
                      Recommended
                    </span>
                  )}
                </div>
              </>
            )}
          </div>
          <svg
            className={`${iconSizes[size]} text-gray-400 transition-transform ${
              isOpen ? 'transform rotate-180' : ''
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />

          {/* Menu */}
          <div className="absolute z-20 mt-1 w-full max-w-md bg-white rounded-md shadow-lg border border-gray-200 max-h-96 overflow-auto">
            {Object.entries(groupedModels).map(([provider, providerModels]) => (
              <div key={provider}>
                <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide bg-gray-50 border-b border-gray-200">
                  {provider === 'anthropic' ? 'Anthropic' : 'OpenAI'}
                </div>
                {providerModels.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => {
                      onModelChange(model.id);
                      setIsOpen(false);
                    }}
                    className={`
                      w-full text-left px-3 py-3 hover:bg-gray-50 focus:bg-gray-50
                      focus:outline-none border-b border-gray-100 last:border-b-0
                      ${selectedModel === model.id ? 'bg-blue-50 border-blue-200' : ''}
                    `}
                  >
                    <div className="flex items-start space-x-3">
                      <div className={`flex-shrink-0 mt-0.5 ${iconSizes[size]}`}>
                        {model.provider === 'anthropic' ? (
                          <div className="bg-orange-500 rounded-full h-full w-full flex items-center justify-center">
                            <span className="text-white text-xs font-bold">A</span>
                          </div>
                        ) : (
                          <div className="bg-green-500 rounded-full h-full w-full flex items-center justify-center">
                            <span className="text-white text-xs font-bold">O</span>
                          </div>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {model.name}
                          </p>
                          {model.is_recommended && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                              Recommended
                            </span>
                          )}
                          {selectedModel === model.id && (
                            <svg className="h-4 w-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                              <path
                                fillRule="evenodd"
                                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                clipRule="evenodd"
                              />
                            </svg>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {model.description}
                        </p>
                        <div className="flex items-center space-x-4 mt-1">
                          <span className="text-xs text-gray-400">
                            {(model.context_window / 1000).toFixed(0)}K context
                          </span>
                          <div className="flex space-x-1">
                            {model.capabilities.slice(0, 3).map((capability) => (
                              <span
                                key={capability}
                                className="inline-flex items-center px-1 py-0.5 rounded text-xs bg-gray-100 text-gray-600"
                              >
                                {capability}
                              </span>
                            ))}
                            {model.capabilities.length > 3 && (
                              <span className="text-xs text-gray-400">
                                +{model.capabilities.length - 3} more
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}