#!/usr/bin/env python3
"""
Create credentials file template for easy manual setup
"""

import yaml
from pathlib import Path

def create_template():
    """Create a credentials.yaml template ready for API keys."""

    print("🔑 Creating API Keys Template")
    print("=" * 30)

    config_dir = Path("config")
    credentials_file = config_dir / "credentials.yaml"

    # Check if file already exists
    if credentials_file.exists():
        print("⚠️  credentials.yaml already exists!")
        response = input("Overwrite it? (y/n): ").strip().lower()
        if response != 'y':
            print("❌ Cancelled")
            return False

    # Create the template
    template = {
        'anthropic': {
            'api_key': 'sk-ant-YOUR_ANTHROPIC_API_KEY_HERE'
        },
        'openai': {
            'api_key': 'sk-YOUR_OPENAI_API_KEY_HERE'
        },
        'aws': {
            'access_key_id': 'YOUR_AWS_ACCESS_KEY_ID',
            'secret_access_key': 'YOUR_AWS_SECRET_ACCESS_KEY'
        },
        'rds': {
            'host': 'YOUR_RDS_ENDPOINT.us-east-1.rds.amazonaws.com',
            'username': 'YOUR_DB_USERNAME',
            'password': 'YOUR_DB_PASSWORD'
        }
    }

    with open(credentials_file, 'w') as f:
        yaml.dump(template, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Created template: {credentials_file}")
    print()
    print("📝 NEXT STEPS:")
    print("1. Get your API keys:")
    print("   • Anthropic: https://console.anthropic.com/ → API Keys")
    print("   • OpenAI: https://platform.openai.com/api-keys")
    print()
    print("2. Edit the file and replace:")
    print("   • sk-ant-YOUR_ANTHROPIC_API_KEY_HERE ← with real Anthropic key")
    print("   • sk-YOUR_OPENAI_API_KEY_HERE ← with real OpenAI key")
    print()
    print("3. Restart Flask server: python3 web/app.py")
    print("4. Test: python3 verify_real_apis.py")

    return True

if __name__ == "__main__":
    create_template()