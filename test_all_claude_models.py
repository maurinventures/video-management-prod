#!/usr/bin/env python3

import requests
import json
import time

def test_all_claude_models():
    """Test all three Claude models to ensure they work properly."""

    # Read session cookie
    try:
        with open('/tmp/test_fixed_cookies.txt', 'r') as f:
            cookie_content = f.read()
    except FileNotFoundError:
        print("❌ No session cookie file found. Please authenticate first.")
        return

    # Extract session cookie value
    session_cookie = None
    for line in cookie_content.split('\n'):
        if line.startswith('#HttpOnly_maurinventuresinternal.com') and 'session' in line:
            parts = line.split('\t')
            if len(parts) > 6:
                session_cookie = parts[6]
                break

    if not session_cookie:
        print("❌ Could not extract session cookie")
        return

    print("=== Testing All Claude Models ===\n")

    # Test configuration for each model
    claude_models = [
        {
            "name": "claude-sonnet",
            "display": "Claude Sonnet 4",
            "expected_backend": "claude-sonnet-4-20250514",
            "description": "Balanced performance and capability"
        },
        {
            "name": "claude-opus",
            "display": "Claude Opus 4.5",
            "expected_backend": "claude-opus-4-5-20251101",
            "description": "Most capable model"
        },
        {
            "name": "claude-haiku",
            "display": "Claude Haiku 3.5",
            "expected_backend": "claude-3-5-haiku-20241022",
            "description": "Fastest responses"
        }
    ]

    results = {}

    for model_info in claude_models:
        model = model_info["name"]
        print(f"🧪 Testing {model_info['display']} ({model})")
        print(f"   Expected backend model: {model_info['expected_backend']}")
        print(f"   Description: {model_info['description']}")

        try:
            # Test with a simple message first
            response = requests.post(
                'https://maurinventuresinternal.com/api/chat',
                json={
                    'message': f'Hello! Please respond with exactly "I am {model_info["display"]}" to confirm you are working.',
                    'model': model,
                    'use_rag': False,
                    'context_mode': 'auto'
                },
                cookies={'session': session_cookie},
                headers={'Content-Type': 'application/json'},
                timeout=45  # Longer timeout for potentially slower models
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')
                model_used = result.get('model', 'Unknown')

                print(f"   ✅ SUCCESS")
                print(f"   📝 Response: {response_text[:150]}{'...' if len(response_text) > 150 else ''}")
                print(f"   🔧 Backend model: {model_used}")
                print(f"   📊 Response length: {len(response_text)} chars")
                print(f"   ⏱️  Status: Model responding properly")

                results[model] = {
                    "status": "success",
                    "response_length": len(response_text),
                    "backend_model": model_used,
                    "response_preview": response_text[:100]
                }

            elif response.status_code == 502:
                print(f"   ❌ 502 Bad Gateway - Backend worker error")
                print(f"   🔍 This suggests the backend model call failed")
                print(f"   💡 Possible causes: API key issue, model unavailable, timeout")

                results[model] = {
                    "status": "502_error",
                    "error": "Bad Gateway - Backend worker error"
                }

            elif response.status_code == 500:
                print(f"   ❌ 500 Internal Server Error")
                try:
                    error_response = response.json()
                    error_msg = error_response.get('error', response.text[:100])
                    print(f"   📝 Error: {error_msg}")
                except:
                    print(f"   📝 Error: {response.text[:100]}")

                results[model] = {
                    "status": "500_error",
                    "error": response.text[:200]
                }

            else:
                print(f"   ❌ HTTP {response.status_code}")
                print(f"   📝 Response: {response.text[:100]}")

                results[model] = {
                    "status": f"http_{response.status_code}",
                    "error": response.text[:200]
                }

        except requests.exceptions.Timeout:
            print(f"   ❌ Request timeout (>45s)")
            print(f"   💡 Model may be very slow or unavailable")
            results[model] = {"status": "timeout"}

        except Exception as e:
            print(f"   ❌ Request failed: {e}")
            results[model] = {"status": "exception", "error": str(e)}

        print()
        time.sleep(2)  # Small delay between requests

    # Summary
    print("=" * 60)
    print("📊 CLAUDE MODELS TEST SUMMARY")
    print("=" * 60)

    working_models = []
    failing_models = []

    for model, result in results.items():
        status_emoji = "✅" if result["status"] == "success" else "❌"
        print(f"{status_emoji} {model}: {result['status'].upper()}")

        if result["status"] == "success":
            working_models.append(model)
            print(f"    Backend: {result.get('backend_model', 'Unknown')}")
            print(f"    Response: {result.get('response_length', 0)} chars")
        else:
            failing_models.append(model)
            if "error" in result:
                print(f"    Error: {result['error'][:100]}")

        print()

    # Final assessment
    print("🎯 FINAL ASSESSMENT:")
    print(f"   Working models: {len(working_models)}/3")
    print(f"   ✅ Functional: {', '.join(working_models) if working_models else 'None'}")
    print(f"   ❌ Issues: {', '.join(failing_models) if failing_models else 'None'}")

    if len(working_models) == 3:
        print("   🎉 ALL CLAUDE MODELS WORKING PERFECTLY!")
    elif len(working_models) >= 1:
        print("   ⚠️  Some models working, others need investigation")
        print("   💡 Check backend logs and API key configuration")
    else:
        print("   🚨 NO CLAUDE MODELS WORKING - Critical issue")
        print("   💡 Check API keys, model mappings, and backend logs")

    # Test @video command with working model
    if working_models:
        print(f"\n🎬 Testing @video command with {working_models[0]}...")

        try:
            response = requests.post(
                'https://maurinventuresinternal.com/api/chat',
                json={
                    'message': '@video Create a short test script',
                    'model': working_models[0],
                    'use_rag': False
                },
                cookies={'session': session_cookie},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                has_script = result.get('has_script', False)
                clips_count = len(result.get('clips', []))

                print(f"   ✅ @video command working")
                print(f"   🎬 Script generated: {has_script}")
                print(f"   📹 Clips: {clips_count}")

            else:
                print(f"   ❌ @video failed: HTTP {response.status_code}")

        except Exception as e:
            print(f"   ❌ @video test failed: {e}")

if __name__ == "__main__":
    test_all_claude_models()