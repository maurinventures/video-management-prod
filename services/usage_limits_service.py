"""
Usage Limits and Statistics Service

Provides usage tracking, limits enforcement, and statistics for the Internal Platform.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import UUID
from sqlalchemy import func, desc
from scripts.db import get_session, AILog


class UsageLimitsService:
    """Service for managing user usage limits and statistics."""

    # Usage limits configuration
    MAX_DAILY_TOKENS_PER_USER = 100_000  # 100K tokens per day per user
    MAX_CONTEXT_TOKENS = 32_000  # Maximum tokens per single request
    WARNING_THRESHOLD = 0.8  # Warning at 80% of daily limit

    # Model pricing (per 1K tokens) - Updated for 2026 pricing
    MODEL_COSTS = {
        'gpt-4o': {
            'input_cost_per_1k': 0.005,   # $5 per 1M input tokens
            'output_cost_per_1k': 0.015,  # $15 per 1M output tokens
            'description': 'GPT-4 Omni - Most capable model'
        },
        'gpt-3.5-turbo': {
            'input_cost_per_1k': 0.0015,  # $1.5 per 1M input tokens
            'output_cost_per_1k': 0.002,  # $2 per 1M output tokens
            'description': 'GPT-3.5 Turbo - Fast and efficient'
        },
        'claude-sonnet': {
            'input_cost_per_1k': 0.003,   # $3 per 1M input tokens
            'output_cost_per_1k': 0.015,  # $15 per 1M output tokens
            'description': 'Claude Sonnet - Balanced performance'
        },
        'claude-opus': {
            'input_cost_per_1k': 0.015,   # $15 per 1M input tokens
            'output_cost_per_1k': 0.075,  # $75 per 1M output tokens
            'description': 'Claude Opus - Most powerful model'
        }
    }

    @classmethod
    def get_user_usage_stats(cls, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive usage statistics for a user over the specified period."""
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        except (ValueError, TypeError):
            raise ValueError(f"Invalid user_id format: {user_id}")

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        with get_session() as session:
            # Query all successful AI logs for the user in the time period
            logs_query = session.query(AILog).filter(
                AILog.user_id == user_uuid,
                AILog.created_at >= start_date,
                AILog.created_at <= end_date,
                AILog.success == 1  # Only successful calls
            )

            # Get basic stats
            total_calls = logs_query.count()

            # If no usage, return zero stats
            if total_calls == 0:
                return {
                    'period_days': days,
                    'total_calls': 0,
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'total_tokens': 0,
                    'total_cost': 0.0,
                    'models_used': []
                }

            # Aggregate data
            aggregates = session.query(
                func.sum(AILog.input_tokens).label('total_input'),
                func.sum(AILog.output_tokens).label('total_output'),
                func.sum(AILog.total_cost).label('total_cost')
            ).filter(
                AILog.user_id == user_uuid,
                AILog.created_at >= start_date,
                AILog.created_at <= end_date,
                AILog.success == 1
            ).first()

            # Get models used with their usage stats
            model_stats = session.query(
                AILog.model,
                func.count(AILog.id).label('call_count'),
                func.sum(AILog.input_tokens).label('input_tokens'),
                func.sum(AILog.output_tokens).label('output_tokens'),
                func.sum(AILog.total_cost).label('total_cost')
            ).filter(
                AILog.user_id == user_uuid,
                AILog.created_at >= start_date,
                AILog.created_at <= end_date,
                AILog.success == 1
            ).group_by(AILog.model).all()

            # Format model usage data
            models_used = []
            for stat in model_stats:
                models_used.append({
                    'model': stat.model,
                    'call_count': stat.call_count or 0,
                    'input_tokens': stat.input_tokens or 0,
                    'output_tokens': stat.output_tokens or 0,
                    'total_tokens': (stat.input_tokens or 0) + (stat.output_tokens or 0),
                    'total_cost': float(stat.total_cost or 0.0)
                })

            # Calculate totals
            total_input_tokens = aggregates.total_input or 0
            total_output_tokens = aggregates.total_output or 0
            total_tokens = total_input_tokens + total_output_tokens
            total_cost = float(aggregates.total_cost or 0.0)

            return {
                'period_days': days,
                'total_calls': total_calls,
                'total_input_tokens': total_input_tokens,
                'total_output_tokens': total_output_tokens,
                'total_tokens': total_tokens,
                'total_cost': total_cost,
                'models_used': sorted(models_used, key=lambda x: x['total_cost'], reverse=True)
            }

    @classmethod
    def check_daily_user_limit(cls, user_id: str) -> Dict[str, Any]:
        """Check current daily token usage against limits for a user."""
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        except (ValueError, TypeError):
            raise ValueError(f"Invalid user_id format: {user_id}")

        # Get today's usage (midnight to now)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.utcnow()

        with get_session() as session:
            # Sum today's token usage
            today_usage = session.query(
                func.sum(AILog.input_tokens + AILog.output_tokens).label('total_tokens')
            ).filter(
                AILog.user_id == user_uuid,
                AILog.created_at >= today_start,
                AILog.created_at <= today_end,
                AILog.success == 1
            ).scalar()

            total_tokens_today = today_usage or 0

            # Calculate percentages and limits
            daily_limit = cls.MAX_DAILY_TOKENS_PER_USER
            usage_percentage = (total_tokens_today / daily_limit) * 100 if daily_limit > 0 else 0

            # Check if warning or limit reached
            warning_active = usage_percentage >= (cls.WARNING_THRESHOLD * 100)
            limit_reached = total_tokens_today >= daily_limit

            return {
                'usage': total_tokens_today,
                'limit': daily_limit,
                'percentage': round(usage_percentage, 2),
                'warning': warning_active,
                'allowed': not limit_reached,
                'remaining': max(0, daily_limit - total_tokens_today)
            }

    @classmethod
    def can_make_request(cls, user_id: str, estimated_tokens: int = 0) -> Dict[str, Any]:
        """Check if user can make a request with estimated token usage."""
        daily_check = cls.check_daily_user_limit(user_id)

        # Check if current request would exceed limit
        would_exceed = (daily_check['usage'] + estimated_tokens) > daily_check['limit']

        return {
            'allowed': daily_check['allowed'] and not would_exceed,
            'current_usage': daily_check['usage'],
            'estimated_total': daily_check['usage'] + estimated_tokens,
            'daily_limit': daily_check['limit'],
            'would_exceed_limit': would_exceed,
            'reason': 'Daily token limit exceeded' if would_exceed or not daily_check['allowed'] else None
        }

    @classmethod
    def get_user_recent_activity(cls, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """Get recent AI API activity for a user."""
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        except (ValueError, TypeError):
            raise ValueError(f"Invalid user_id format: {user_id}")

        with get_session() as session:
            recent_logs = session.query(AILog).filter(
                AILog.user_id == user_uuid
            ).order_by(desc(AILog.created_at)).limit(limit).all()

            activity = []
            for log in recent_logs:
                activity.append({
                    'id': str(log.id),
                    'request_type': log.request_type,
                    'model': log.model,
                    'input_tokens': log.input_tokens or 0,
                    'output_tokens': log.output_tokens or 0,
                    'total_tokens': (log.input_tokens or 0) + (log.output_tokens or 0),
                    'cost': float(log.total_cost or 0.0),
                    'success': bool(log.success),
                    'created_at': log.created_at.isoformat(),
                    'latency_ms': log.latency_ms
                })

            return {
                'recent_activity': activity,
                'total_entries': len(activity)
            }

    @classmethod
    def estimate_request_cost(cls, model: str, input_tokens: int, output_tokens: int) -> Dict[str, Any]:
        """Estimate the cost of a request based on model and token counts."""
        if model not in cls.MODEL_COSTS:
            # Default to GPT-4o pricing for unknown models
            model_pricing = cls.MODEL_COSTS['gpt-4o']
        else:
            model_pricing = cls.MODEL_COSTS[model]

        # Calculate costs (pricing is per 1K tokens)
        input_cost = (input_tokens / 1000) * model_pricing['input_cost_per_1k']
        output_cost = (output_tokens / 1000) * model_pricing['output_cost_per_1k']
        total_cost = input_cost + output_cost

        return {
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(total_cost, 6),
            'currency': 'USD'
        }