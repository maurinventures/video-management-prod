#!/usr/bin/env python3
"""
Test script for AI API integration
Tests both Claude and OpenAI models with the chat interface.
"""

import requests
import json

API_BASE = "http://localhost:5001"

def test_models_endpoint():
    """Test the models endpoint."""
    print("🔍 Testing models endpoint...")
    response = requests.get(f"{API_BASE}/api/models")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Models loaded: {len(data['models'])} total")
        print(f"✅ Default model: {data['default']}")
        print(f"✅ Providers: {', '.join(set(m['provider'] for m in data['models']))}")
        return True
    else:
        print(f"❌ Models endpoint failed: {response.status_code}")
        return False

def test_chat_endpoint(message, model):
    """Test chat with specific model."""
    print(f"\n💬 Testing {model}:")
    print(f"   Message: {message}")

    payload = {
        "message": message,
        "model": model
    }

    response = requests.post(
        f"{API_BASE}/api/chat/test",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        data = response.json()
        response_text = data.get('response', 'No response')
        used_model = data.get('model', 'Unknown')

        print(f"   ✅ Status: Success")
        print(f"   ✅ Model: {used_model}")
        print(f"   ✅ Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
        return True
    else:
        print(f"   ❌ Failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"   ❌ Error: {error_data.get('error', 'Unknown error')}")
        except:
            print(f"   ❌ Raw error: {response.text[:200]}")
        return False

def main():
    """Main test function."""
    print("🧪 AI Integration Test Suite")
    print("=" * 50)

    # Test models endpoint
    if not test_models_endpoint():
        print("❌ Models endpoint failed - stopping tests")
        return

    # Test different models
    test_cases = [
        ("Hello! Can you help me test the Claude integration?", "claude-sonnet"),
        ("Hi there! Testing GPT-4o integration.", "gpt-4o"),
        ("Quick test of Claude Opus capabilities", "claude-opus"),
        ("Testing GPT-3.5 Turbo", "gpt-3.5-turbo"),
    ]

    results = []
    for message, model in test_cases:
        success = test_chat_endpoint(message, model)
        results.append((model, success))

    # Summary
    print("\n🎯 Test Results Summary:")
    print("=" * 30)
    successful = sum(1 for _, success in results if success)
    total = len(results)

    for model, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {model:15} {status}")

    print(f"\n📊 Overall: {successful}/{total} models working correctly")

    if successful == total:
        print("🎉 All AI integrations are working!")
    else:
        print("⚠️  Some integrations need configuration")

if __name__ == "__main__":
    main()