import React, { useState, useEffect } from 'react';
import api from '../../lib/api';
import { UsageStatus, UsageLimits, UsageStats } from '../../types';
import { Card } from '../ui/card';
import { Progress } from '../ui/progress';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';

interface UsageDisplayProps {
  className?: string;
}

export function UsageDisplay({ className }: UsageDisplayProps) {
  const [status, setStatus] = useState<UsageStatus | null>(null);
  const [limits, setLimits] = useState<UsageLimits | null>(null);
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUsageData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [statusData, limitsData, statsData] = await Promise.all([
          api.usage.getStatus(),
          api.usage.getLimits(),
          api.usage.getStats(30)
        ]);

        setStatus(statusData);
        setLimits(limitsData);
        setStats(statsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load usage data');
        console.error('Error fetching usage data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchUsageData();
  }, []);

  if (loading) {
    return (
      <div className={`p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert className={`${className}`}>
        <AlertDescription>
          Error loading usage data: {error}
        </AlertDescription>
      </Alert>
    );
  }

  if (!status || !limits || !stats) {
    return (
      <Alert className={`${className}`}>
        <AlertDescription>
          No usage data available
        </AlertDescription>
      </Alert>
    );
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= limits.limits.warning_threshold_percent) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getUsageBadgeVariant = (percentage: number) => {
    if (percentage >= 90) return 'destructive';
    if (percentage >= limits.limits.warning_threshold_percent) return 'secondary';
    return 'default';
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-1">Usage & Limits</h3>
        <p className="text-sm text-gray-600">Monitor your AI API usage and costs</p>
      </div>

      {/* Current Usage Status */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="font-medium text-gray-900">Daily Token Usage</h4>
          <Badge variant={getUsageBadgeVariant(status.daily_percentage_used * 100)}>
            {(status.daily_percentage_used * 100).toFixed(1)}% used
          </Badge>
        </div>

        <div className="space-y-2">
          <Progress
            value={status.daily_percentage_used * 100}
            className="h-3"
            style={{ '--progress-background': getUsageColor(status.daily_percentage_used * 100) } as React.CSSProperties}
          />
          <div className="flex justify-between text-sm text-gray-600">
            <span>{formatNumber(status.daily_tokens_used)} used</span>
            <span>{formatNumber(status.daily_tokens_remaining)} remaining</span>
          </div>
          <div className="text-xs text-gray-500">
            Daily limit: {formatNumber(status.max_daily_tokens)} tokens
          </div>
        </div>

        {status.warning_active && (
          <Alert className="mt-3">
            <AlertDescription className="text-sm">
              ⚠️ You're approaching your daily limit. Consider optimizing your usage.
            </AlertDescription>
          </Alert>
        )}

        {status.limit_reached && (
          <Alert className="mt-3">
            <AlertDescription className="text-sm">
              🚫 Daily limit reached. Usage will be restricted until tomorrow.
            </AlertDescription>
          </Alert>
        )}
      </Card>

      {/* Usage Statistics (30 days) */}
      <Card className="p-4">
        <h4 className="font-medium text-gray-900 mb-3">30-Day Usage Statistics</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{stats.period_stats.total_calls}</div>
            <div className="text-xs text-gray-500">API Calls</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {formatNumber(stats.period_stats.total_tokens)}
            </div>
            <div className="text-xs text-gray-500">Total Tokens</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              ${stats.period_stats.total_cost.toFixed(2)}
            </div>
            <div className="text-xs text-gray-500">Total Cost</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              ${stats.period_stats.avg_cost_per_call.toFixed(3)}
            </div>
            <div className="text-xs text-gray-500">Avg/Call</div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span>Models used:</span>
            <div className="flex gap-1">
              {stats.period_stats.models_used.map((model) => (
                <Badge key={model} variant="outline" className="text-xs">
                  {model}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* Limits and Pricing */}
      <Card className="p-4">
        <h4 className="font-medium text-gray-900 mb-3">Limits & Pricing</h4>

        <div className="space-y-4">
          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">Usage Limits</h5>
            <div className="space-y-1 text-sm text-gray-600">
              <div>Daily limit: {formatNumber(limits.limits.max_daily_tokens_per_user)} tokens</div>
              <div>Context limit: {formatNumber(limits.limits.max_context_tokens_per_request)} tokens per request</div>
              <div>Warning threshold: {limits.limits.warning_threshold_percent}%</div>
            </div>
          </div>

          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">Model Pricing (per 1K tokens)</h5>
            <div className="space-y-1 text-xs">
              {Object.entries(limits.model_pricing).map(([model, pricing]) => (
                <div key={model} className="flex justify-between">
                  <span className="font-mono">{model}</span>
                  <span>
                    ${pricing.input_cost_per_1k_tokens.toFixed(4)} / ${pricing.output_cost_per_1k_tokens.toFixed(4)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}