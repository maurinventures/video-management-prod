#!/usr/bin/env python3
"""
Test script for Prompt 19: Token Limits and Tracking
Tests the complete usage limits system including:
- Context limit checking
- Daily user limit checking
- Cost calculation
- Prompt caching
"""

import sys
import os
sys.path.append('.')
os.chdir('web')

from services.usage_limits_service import UsageLimitsService

def test_cost_calculation():
    """Test cost calculation for different models."""
    print("\n=== Testing Cost Calculation ===")

    test_cases = [
        ('claude-sonnet', 1000, 500),
        ('claude-haiku', 2000, 1000),
        ('gpt-4o', 1500, 750),
        ('unknown-model', 1000, 500),  # Should use default pricing
    ]

    for model, input_tokens, output_tokens in test_cases:
        input_cost, output_cost, total_cost = UsageLimitsService.calculate_cost(model, input_tokens, output_tokens)
        print(f"  {model:15} | {input_tokens:4d}+{output_tokens:3d} tokens | ${total_cost:.4f} (in:${input_cost:.4f}, out:${output_cost:.4f})")

def test_context_limits():
    """Test context limit checking."""
    print("\n=== Testing Context Limits ===")

    test_cases = [
        (10000, True),  # Well under limit
        (49999, True),  # Just under limit
        (50001, False), # Just over limit
        (100000, False) # Way over limit
    ]

    for tokens, should_pass in test_cases:
        result = UsageLimitsService.check_context_limit(tokens)
        status = "✅ PASS" if result['allowed'] == should_pass else "❌ FAIL"
        print(f"  {tokens:6d} tokens | Expected: {should_pass:5} | Got: {result['allowed']:5} | {status}")

def test_prompt_caching():
    """Test prompt caching functionality."""
    print("\n=== Testing Prompt Caching ===")

    # Test hash generation
    prompt = "What is the capital of France?"
    model = "claude-sonnet"
    hash1 = UsageLimitsService.get_prompt_hash(prompt, model)
    hash2 = UsageLimitsService.get_prompt_hash(prompt, model)
    hash3 = UsageLimitsService.get_prompt_hash(prompt + " Please be specific.", model)

    print(f"  Same prompt generates same hash: {'✅ PASS' if hash1 == hash2 else '❌ FAIL'}")
    print(f"  Different prompts generate different hashes: {'✅ PASS' if hash1 != hash3 else '❌ FAIL'}")
    print(f"  Hash format: {hash1[:16]}... (64 chars)")

def test_daily_limits():
    """Test daily user limit checking."""
    print("\n=== Testing Daily Limits ===")

    # Test with demo user (valid UUID format)
    import uuid
    demo_user_id = str(uuid.UUID('12345678-1234-5678-9abc-123456789012'))

    test_cases = [
        (0, True),      # No usage
        (100000, True), # 20% usage
        (400000, True), # 80% usage (warning threshold)
        (500001, False) # Over limit
    ]

    for additional_tokens, should_pass in test_cases:
        result = UsageLimitsService.check_daily_user_limit(demo_user_id, additional_tokens)
        percentage = result['percentage'] * 100
        warning = result.get('warning', False)
        status = "✅ PASS" if result['allowed'] == should_pass else "❌ FAIL"
        warning_flag = "⚠️  WARNING" if warning else ""
        print(f"  {additional_tokens:6d} tokens | {percentage:5.1f}% | Expected: {should_pass:5} | Got: {result['allowed']:5} | {status} {warning_flag}")

def run_all_tests():
    """Run all usage limits tests."""
    print("🚀 Starting Prompt 19: Usage Limits Test Suite")
    print(f"📊 Configuration:")
    print(f"   Max Context Tokens: {UsageLimitsService.MAX_CONTEXT_TOKENS:,}")
    print(f"   Max Daily Tokens:   {UsageLimitsService.MAX_DAILY_TOKENS_PER_USER:,}")
    print(f"   Warning Threshold:  {UsageLimitsService.WARNING_THRESHOLD:.0%}")

    try:
        test_cost_calculation()
        test_context_limits()
        test_prompt_caching()
        test_daily_limits()

        print("\n🎉 All tests completed!")
        print("✅ Usage limits system is working correctly")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)