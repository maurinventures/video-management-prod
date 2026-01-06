/**
 * Hook for managing AI models
 */

import { useState, useEffect } from 'react';
import api from '../lib/api';
import { AIModel } from '../types';

interface UseModelsReturn {
  models: AIModel[];
  defaultModel: string;
  loading: boolean;
  error: string | null;
  getModelById: (id: string) => AIModel | undefined;
  getRecommendedModels: () => AIModel[];
  getModelsByProvider: (provider: 'openai' | 'anthropic') => AIModel[];
}

export function useModels(): UseModelsReturn {
  const [models, setModels] = useState<AIModel[]>([]);
  const [defaultModel, setDefaultModel] = useState<string>('gpt-4o');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.models.list();
      setModels(response.models);
      setDefaultModel(response.default);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch models');
      console.error('Failed to fetch models:', err);
    } finally {
      setLoading(false);
    }
  };

  const getModelById = (id: string): AIModel | undefined => {
    return models.find(model => model.id === id);
  };

  const getRecommendedModels = (): AIModel[] => {
    return models.filter(model => model.is_recommended);
  };

  const getModelsByProvider = (provider: 'openai' | 'anthropic'): AIModel[] => {
    return models.filter(model => model.provider === provider);
  };

  return {
    models,
    defaultModel,
    loading,
    error,
    getModelById,
    getRecommendedModels,
    getModelsByProvider,
  };
}