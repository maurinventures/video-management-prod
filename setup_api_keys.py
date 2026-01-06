#!/usr/bin/env python3
"""
Interactive API Key Setup Script
Guides you through setting up real Anthropic and OpenAI API keys.
"""

import os
import yaml
import requests
from pathlib import Path

def print_header():
    print("🔑 REAL API KEYS SETUP WIZARD")
    print("=" * 40)
    print("This script will help you set up real API keys for:")
    print("• Anthropic Claude (claude-sonnet, claude-opus, claude-haiku)")
    print("• OpenAI GPT (gpt-4o, gpt-4-turbo, gpt-3.5-turbo)")
    print()

def get_api_keys_info():
    print("📋 STEP 1: Get Your API Keys")
    print("-" * 30)
    print()
    print("🎯 ANTHROPIC API KEY:")
    print("1. Visit: https://console.anthropic.com/")
    print("2. Sign up or log into your account")
    print("3. Go to 'API Keys' section")
    print("4. Click 'Create Key'")
    print("5. Copy the key (starts with 'sk-ant-')")
    print()
    print("💡 OPENAI API KEY:")
    print("1. Visit: https://platform.openai.com/api-keys")
    print("2. Sign up or log into your account")
    print("3. Click 'Create new secret key'")
    print("4. Copy the key (starts with 'sk-')")
    print()
    input("Press Enter when you have both API keys ready...")

def collect_api_keys():
    print("\n📝 STEP 2: Enter Your API Keys")
    print("-" * 30)

    # Get Anthropic key
    while True:
        anthropic_key = input("🔑 Enter your Anthropic API key (sk-ant-...): ").strip()
        if anthropic_key.startswith('sk-ant-') and len(anthropic_key) > 20:
            break
        print("❌ Invalid Anthropic key format. Should start with 'sk-ant-' and be longer than 20 characters.")

    # Get OpenAI key
    while True:
        openai_key = input("🔑 Enter your OpenAI API key (sk-...): ").strip()
        if openai_key.startswith('sk-') and len(openai_key) > 20:
            break
        print("❌ Invalid OpenAI key format. Should start with 'sk-' and be longer than 20 characters.")

    return anthropic_key, openai_key

def test_api_key(api_name, key, test_func):
    """Test if an API key is working."""
    print(f"🧪 Testing {api_name} API key...", end=" ")
    try:
        if test_func(key):
            print("✅ Working!")
            return True
        else:
            print("❌ Failed!")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_anthropic_key(key):
    """Test Anthropic API key by making a simple request."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model="claude-haiku-3-5-20241120",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        return len(response.content) > 0
    except Exception:
        return False

def test_openai_key(key):
    """Test OpenAI API key by making a simple request."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        return len(response.choices) > 0
    except Exception:
        return False

def create_credentials_file(anthropic_key, openai_key):
    """Create the credentials.yaml file."""
    print("\n💾 STEP 3: Creating Credentials File")
    print("-" * 30)

    config_dir = Path("/Users/josephs./internal-platform/config")
    credentials_file = config_dir / "credentials.yaml"

    # Read existing template or create new structure
    template_file = config_dir / "credentials.yaml.template"

    if template_file.exists():
        with open(template_file, 'r') as f:
            config_data = yaml.safe_load(f) or {}
    else:
        config_data = {}

    # Update with API keys
    config_data['anthropic'] = {'api_key': anthropic_key}
    config_data['openai'] = {'api_key': openai_key}

    # Ensure other required sections exist
    if 'aws' not in config_data:
        config_data['aws'] = {
            'access_key_id': 'YOUR_AWS_ACCESS_KEY_ID',
            'secret_access_key': 'YOUR_AWS_SECRET_ACCESS_KEY'
        }

    if 'rds' not in config_data:
        config_data['rds'] = {
            'host': 'YOUR_RDS_ENDPOINT.us-east-1.rds.amazonaws.com',
            'username': 'YOUR_DB_USERNAME',
            'password': 'YOUR_DB_PASSWORD'
        }

    # Write credentials file
    with open(credentials_file, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Created credentials file: {credentials_file}")
    print("⚠️  IMPORTANT: Never commit credentials.yaml to version control!")

def test_integration():
    """Test the full integration with real API keys."""
    print("\n🚀 STEP 4: Testing Integration")
    print("-" * 30)

    try:
        # Test models endpoint
        models_response = requests.get("http://localhost:5001/api/models")
        if models_response.status_code != 200:
            print("❌ Flask server not running. Please start it with: python3 web/app.py")
            return False

        print("✅ Flask server is running")

        # Test each AI model
        models_to_test = [
            ("claude-haiku", "Claude Haiku (fastest)"),
            ("gpt-3.5-turbo", "GPT-3.5 Turbo (fastest)")
        ]

        for model_id, model_name in models_to_test:
            payload = {
                "message": f"Hello! Testing {model_name}",
                "model": model_id
            }

            response = requests.post(
                "http://localhost:5001/api/chat/test",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()
                if "Demo Response" not in data.get('response', ''):
                    print(f"✅ {model_name} → Real AI response received!")
                else:
                    print(f"⚠️  {model_name} → Still in demo mode")
            else:
                print(f"❌ {model_name} → Failed to connect")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        return False

def main():
    print_header()

    # Step 1: Guide user to get API keys
    get_api_keys_info()

    # Step 2: Collect API keys
    anthropic_key, openai_key = collect_api_keys()

    # Step 3: Test API keys (optional, requires installing packages)
    print("\n🧪 STEP 2.5: Testing API Keys")
    print("-" * 30)

    try:
        # Try to test keys if packages are available
        print("Testing API keys...")
        anthropic_works = test_api_key("Anthropic", anthropic_key, test_anthropic_key)
        openai_works = test_api_key("OpenAI", openai_key, test_openai_key)

        if not anthropic_works:
            print("⚠️  Anthropic key may not be working - proceeding anyway")
        if not openai_works:
            print("⚠️  OpenAI key may not be working - proceeding anyway")

    except ImportError:
        print("📦 API testing packages not available - skipping key validation")
        print("✅ Will proceed with configuration")

    # Step 4: Create credentials file
    create_credentials_file(anthropic_key, openai_key)

    # Step 5: Instructions for next steps
    print("\n🎯 FINAL STEPS:")
    print("-" * 30)
    print("1. Restart your Flask server:")
    print("   • Stop current server (Ctrl+C)")
    print("   • Run: python3 web/app.py")
    print()
    print("2. Test the integration:")
    print("   • Run: python3 test_ai_integration.py")
    print("   • Or visit: http://localhost:3000")
    print()
    print("3. You should now see real AI responses instead of demo messages!")
    print()
    print("🎉 Setup complete! Your chat interface is now connected to real AI APIs.")

if __name__ == "__main__":
    main()