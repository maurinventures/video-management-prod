#!/usr/bin/env python3
"""
Verification script for real API integration
Checks if the system is using real APIs vs demo mode
"""

import requests
import json
import time

def check_server_status():
    """Check if servers are running."""
    print("🔍 Checking Server Status")
    print("-" * 30)

    try:
        # Check React
        react_response = requests.get("http://localhost:3000", timeout=5)
        react_status = "✅ Running" if react_response.status_code == 200 else "❌ Issues"
    except:
        react_status = "❌ Not running"

    try:
        # Check Flask
        flask_response = requests.get("http://localhost:5001/api/models", timeout=5)
        flask_status = "✅ Running" if flask_response.status_code == 200 else "❌ Issues"
    except:
        flask_status = "❌ Not running"

    print(f"React Frontend (3000): {react_status}")
    print(f"Flask Backend (5001):  {flask_status}")

    return "✅" in react_status and "✅" in flask_status

def test_real_api_integration():
    """Test if we're getting real AI responses vs demo responses."""
    print("\n🤖 Testing Real AI Integration")
    print("-" * 30)

    # Test cases with different models
    test_cases = [
        ("claude-haiku", "Hello Claude Haiku!"),
        ("gpt-3.5-turbo", "Hello GPT-3.5!"),
        ("claude-sonnet", "Test Claude Sonnet"),
        ("gpt-4o", "Test GPT-4o")
    ]

    real_apis_working = 0
    demo_mode = 0
    failed = 0

    for model, message in test_cases:
        print(f"Testing {model:12}... ", end="", flush=True)

        try:
            response = requests.post(
                "http://localhost:5001/api/chat/test",
                json={"message": message, "model": model},
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')

                if "Demo Response" in response_text:
                    print("📋 Demo Mode")
                    demo_mode += 1
                elif len(response_text) > 10 and not response_text.startswith("Sorry"):
                    print("✅ Real API")
                    real_apis_working += 1
                else:
                    print("❌ Error")
                    failed += 1
            else:
                print("❌ Failed")
                failed += 1

        except Exception as e:
            print(f"❌ Error: {str(e)[:30]}")
            failed += 1

    return real_apis_working, demo_mode, failed

def check_credentials_file():
    """Check if credentials file exists and has API keys."""
    print("\n🔑 Checking Credentials")
    print("-" * 30)

    import os
    import yaml
    from pathlib import Path

    creds_file = Path("config/credentials.yaml")

    if not creds_file.exists():
        print("❌ credentials.yaml not found")
        return False, False

    try:
        with open(creds_file, 'r') as f:
            config = yaml.safe_load(f)

        # Check for API keys
        anthropic_configured = bool(
            config.get('anthropic', {}).get('api_key', '').startswith('sk-ant-')
        )
        openai_configured = bool(
            config.get('openai', {}).get('api_key', '').startswith('sk-')
        )

        print(f"Anthropic API key: {'✅ Configured' if anthropic_configured else '❌ Missing/Invalid'}")
        print(f"OpenAI API key:    {'✅ Configured' if openai_configured else '❌ Missing/Invalid'}")

        return anthropic_configured, openai_configured

    except Exception as e:
        print(f"❌ Error reading credentials: {str(e)}")
        return False, False

def main():
    print("🔍 REAL API INTEGRATION VERIFICATION")
    print("=" * 40)
    print()

    # Check servers
    servers_ok = check_server_status()

    if not servers_ok:
        print("\n❌ Servers not running properly!")
        print("Please start both servers:")
        print("1. React: npm start (in frontend/)")
        print("2. Flask: python3 web/app.py")
        return

    # Check credentials
    anthropic_ok, openai_ok = check_credentials_file()

    # Test API integration
    real_apis, demo_responses, failures = test_real_api_integration()

    # Summary
    print(f"\n📊 VERIFICATION RESULTS")
    print("=" * 25)
    print(f"Real API Responses:  {real_apis}/4")
    print(f"Demo Mode Responses: {demo_responses}/4")
    print(f"Failed Requests:     {failures}/4")
    print()

    # Overall status
    if real_apis == 4:
        print("🎉 SUCCESS! All models using real APIs")
        print("✅ Your chat interface is fully connected to Anthropic and OpenAI")
        print("🚀 Ready for production use!")

    elif real_apis > 0:
        print("⚠️  PARTIAL SUCCESS! Some models using real APIs")
        if not anthropic_ok:
            print("🔑 Add Anthropic API key for Claude models")
        if not openai_ok:
            print("🔑 Add OpenAI API key for GPT models")

    elif demo_responses == 4:
        print("📋 DEMO MODE ACTIVE")
        print("🔑 Add API keys to connect to real AI services")
        print()
        print("To set up real APIs:")
        print("1. Run: python3 setup_api_keys.py")
        print("2. Or manually edit config/credentials.yaml")
        print("3. Restart Flask server")

    else:
        print("❌ INTEGRATION ISSUES")
        print("Check server logs for detailed error messages")

    print(f"\n🌐 Access URLs:")
    print(f"Frontend: http://localhost:3000")
    print(f"Backend:  http://localhost:5001")

if __name__ == "__main__":
    main()