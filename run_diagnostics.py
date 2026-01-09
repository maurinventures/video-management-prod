#!/usr/bin/env python3
"""
Platform Diagnostics Script
Comprehensive health check for the internal platform
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Add project paths
sys.path.append('/Users/josephs./internal-platform')
sys.path.append('/Users/josephs./internal-platform/web')

def run_command(cmd, shell=True):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=30)
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Command timed out'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def test_database():
    """Test database connectivity and run basic queries"""
    print("🔍 Testing database connectivity...")

    try:
        from scripts.db import DatabaseSession, Video, User, Conversation

        results = {}

        with DatabaseSession() as db_session:
            # Test basic queries
            try:
                video_count = db_session.query(Video).count()
                results['videos_count'] = video_count
            except Exception as e:
                results['videos_error'] = str(e)

            try:
                user_count = db_session.query(User).count()
                results['users_count'] = user_count
            except Exception as e:
                results['users_error'] = str(e)

            try:
                conv_count = db_session.query(Conversation).count()
                results['conversations_count'] = conv_count
            except Exception as e:
                results['conversations_error'] = str(e)

        return {'success': True, 'data': results}

    except Exception as e:
        return {'success': False, 'error': str(e)}

def test_s3():
    """Test AWS S3 bucket access"""
    print("🔍 Testing S3 connectivity...")

    try:
        import boto3
        from config.credentials import get_config

        config = get_config()

        s3_client = boto3.client(
            's3',
            aws_access_key_id=config.aws_access_key,
            aws_secret_access_key=config.aws_secret_key,
            region_name='us-east-1'
        )

        # List objects in bucket
        response = s3_client.list_objects_v2(
            Bucket='mv-brain',
            MaxKeys=5
        )

        objects = response.get('Contents', [])
        object_list = [obj['Key'] for obj in objects]

        return {
            'success': True,
            'data': {
                'bucket_accessible': True,
                'object_count': response.get('KeyCount', 0),
                'sample_objects': object_list
            }
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}

def test_ai_apis():
    """Test AI API connectivity and keys"""
    print("🔍 Testing AI API connectivity...")

    results = {}

    # Check environment variables
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')

    results['anthropic_key_set'] = bool(anthropic_key)
    results['openai_key_set'] = bool(openai_key)

    if anthropic_key:
        results['anthropic_key_preview'] = anthropic_key[:10] + "..."

    if openai_key:
        results['openai_key_preview'] = openai_key[:10] + "..."

    # Test Claude API call
    try:
        import anthropic
        if anthropic_key:
            client = anthropic.Anthropic(api_key=anthropic_key)
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Say hello"}]
            )
            results['claude_test'] = {
                'success': True,
                'response': message.content[0].text if message.content else 'No content'
            }
        else:
            results['claude_test'] = {'success': False, 'error': 'No API key'}
    except Exception as e:
        results['claude_test'] = {'success': False, 'error': str(e)}

    return {'success': True, 'data': results}

def test_api_endpoints():
    """Test API endpoints"""
    print("🔍 Testing API endpoints...")

    endpoints = [
        {'method': 'GET', 'url': 'https://maurinventuresinternal.com/api/health'},
        {'method': 'GET', 'url': 'https://maurinventuresinternal.com/api/auth/me'},
        {'method': 'GET', 'url': 'https://maurinventuresinternal.com/api/library/videos'},
        {'method': 'GET', 'url': 'https://maurinventuresinternal.com/api/library/audio'},
        {'method': 'GET', 'url': 'https://maurinventuresinternal.com/api/conversations'},
    ]

    results = {}

    for endpoint in endpoints:
        try:
            if endpoint['method'] == 'GET':
                result = run_command(f"curl -s -o /dev/null -w '%{{http_code}}' {endpoint['url']}")
                if result['success']:
                    results[endpoint['url']] = {
                        'status_code': result['stdout'].strip(),
                        'success': True
                    }
                else:
                    results[endpoint['url']] = {
                        'success': False,
                        'error': result.get('error', 'Unknown error')
                    }
        except Exception as e:
            results[endpoint['url']] = {'success': False, 'error': str(e)}

    # Test POST /api/chat with demo session
    try:
        # First login to get session
        login_cmd = """curl -s -X POST -H "Content-Type: application/json" \
                     -d '{"email":"demo@maurinventures.com","password":"demo"}' \
                     -c /tmp/diagnostic_cookies.txt \
                     https://maurinventuresinternal.com/api/auth/login"""

        login_result = run_command(login_cmd)

        if login_result['success']:
            # Test chat endpoint
            chat_cmd = """curl -s -X POST -H "Content-Type: application/json" \
                        -d '{"message":"Hello test"}' \
                        -b /tmp/diagnostic_cookies.txt \
                        https://maurinventuresinternal.com/api/chat"""

            chat_result = run_command(chat_cmd)

            if chat_result['success']:
                try:
                    chat_response = json.loads(chat_result['stdout'])
                    results['POST /api/chat'] = {
                        'success': True,
                        'has_response': bool(chat_response.get('response')),
                        'model': chat_response.get('model')
                    }
                except:
                    results['POST /api/chat'] = {
                        'success': True,
                        'response_length': len(chat_result['stdout'])
                    }
            else:
                results['POST /api/chat'] = {'success': False, 'error': 'Chat request failed'}
        else:
            results['POST /api/chat'] = {'success': False, 'error': 'Login failed for chat test'}

    except Exception as e:
        results['POST /api/chat'] = {'success': False, 'error': str(e)}

    return {'success': True, 'data': results}

def check_credentials():
    """Check credentials file"""
    print("🔍 Checking credentials file...")

    cred_file = Path('/Users/josephs./internal-platform/config/credentials.yaml')

    if not cred_file.exists():
        return {'success': False, 'error': 'credentials.yaml not found'}

    try:
        from config.credentials import get_config
        config = get_config()

        # Get all attributes (keys) without values
        config_keys = [attr for attr in dir(config) if not attr.startswith('_')]

        return {
            'success': True,
            'data': {
                'file_exists': True,
                'readable': True,
                'config_keys': config_keys
            }
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}

def check_recent_errors():
    """Check recent Flask errors"""
    print("🔍 Checking recent errors...")

    try:
        # Get recent logs from production server
        log_cmd = 'ssh mv-internal "sudo journalctl -u mv-internal -n 50 --no-pager | grep -i error"'
        result = run_command(log_cmd)

        error_lines = []
        if result['success'] and result['stdout']:
            error_lines = result['stdout'].strip().split('\n')

        return {
            'success': True,
            'data': {
                'error_count': len(error_lines),
                'recent_errors': error_lines[-10:] if error_lines else []  # Last 10 errors
            }
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}

def check_git_history():
    """Check recent git commits"""
    print("🔍 Checking git history...")

    try:
        result = run_command('git log --oneline -5')

        commits = []
        if result['success'] and result['stdout']:
            commits = result['stdout'].strip().split('\n')

        return {
            'success': True,
            'data': {
                'recent_commits': commits
            }
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}

def generate_report(results):
    """Generate diagnostic report"""
    print("📄 Generating diagnostic report...")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# Platform Diagnostic Report

**Generated:** {timestamp}
**Platform:** Internal Platform (maurinventuresinternal.com)

---

## 1. Backend Connectivity

### Database (PostgreSQL/RDS)
"""

    # Database results
    db_results = results.get('database', {})
    if db_results.get('success'):
        report += "✅ **Database Connection:** SUCCESSFUL\n\n"
        data = db_results.get('data', {})
        for key, value in data.items():
            if key.endswith('_count'):
                report += f"- `{key.replace('_count', '').upper()} COUNT`: {value}\n"
            elif key.endswith('_error'):
                report += f"- `{key.replace('_error', '').upper()} ERROR`: {value}\n"
    else:
        report += f"❌ **Database Connection:** FAILED\n- Error: {db_results.get('error')}\n"

    report += "\n### AWS S3\n"

    # S3 results
    s3_results = results.get('s3', {})
    if s3_results.get('success'):
        data = s3_results.get('data', {})
        report += "✅ **S3 Connection:** SUCCESSFUL\n"
        report += f"- Objects in bucket: {data.get('object_count', 0)}\n"
        if data.get('sample_objects'):
            report += "- Sample objects:\n"
            for obj in data.get('sample_objects', []):
                report += f"  - {obj}\n"
    else:
        report += f"❌ **S3 Connection:** FAILED\n- Error: {s3_results.get('error')}\n"

    report += "\n### AI APIs\n"

    # AI API results
    ai_results = results.get('ai_apis', {})
    if ai_results.get('success'):
        data = ai_results.get('data', {})
        report += f"- **ANTHROPIC_API_KEY:** {'✅ SET' if data.get('anthropic_key_set') else '❌ NOT SET'}"
        if data.get('anthropic_key_preview'):
            report += f" ({data.get('anthropic_key_preview')})"
        report += "\n"

        report += f"- **OPENAI_API_KEY:** {'✅ SET' if data.get('openai_key_set') else '❌ NOT SET'}"
        if data.get('openai_key_preview'):
            report += f" ({data.get('openai_key_preview')})"
        report += "\n"

        claude_test = data.get('claude_test', {})
        if claude_test.get('success'):
            report += f"- **Claude API Test:** ✅ SUCCESS - Response: \"{claude_test.get('response')}\"\n"
        else:
            report += f"- **Claude API Test:** ❌ FAILED - {claude_test.get('error')}\n"
    else:
        report += f"❌ **AI APIs Check:** FAILED\n- Error: {ai_results.get('error')}\n"

    report += "\n---\n\n## 2. API Endpoints Test\n\n"

    # API endpoint results
    api_results = results.get('api_endpoints', {})
    if api_results.get('success'):
        data = api_results.get('data', {})
        for endpoint, result in data.items():
            if result.get('success'):
                status_code = result.get('status_code', 'N/A')
                if endpoint == 'POST /api/chat':
                    model = result.get('model', 'N/A')
                    report += f"- `{endpoint}`: ✅ SUCCESS (Model: {model})\n"
                else:
                    report += f"- `{endpoint}`: ✅ {status_code}\n"
            else:
                report += f"- `{endpoint}`: ❌ FAILED - {result.get('error', 'Unknown error')}\n"
    else:
        report += f"❌ **API Endpoints Test:** FAILED\n- Error: {api_results.get('error')}\n"

    report += "\n---\n\n## 3. Credentials File\n\n"

    # Credentials results
    cred_results = results.get('credentials', {})
    if cred_results.get('success'):
        data = cred_results.get('data', {})
        report += "✅ **Credentials File:** ACCESSIBLE\n"
        report += f"- File exists: {data.get('file_exists')}\n"
        report += f"- Readable: {data.get('readable')}\n"
        report += "- Configuration keys:\n"
        for key in data.get('config_keys', []):
            report += f"  - {key}\n"
    else:
        report += f"❌ **Credentials File:** FAILED\n- Error: {cred_results.get('error')}\n"

    report += "\n---\n\n## 4. Recent Errors\n\n"

    # Error results
    error_results = results.get('recent_errors', {})
    if error_results.get('success'):
        data = error_results.get('data', {})
        error_count = data.get('error_count', 0)
        report += f"**Error Count (Last 50 log entries):** {error_count}\n\n"

        if data.get('recent_errors'):
            report += "**Recent Errors:**\n```\n"
            for error in data.get('recent_errors', []):
                report += f"{error}\n"
            report += "```\n"
        else:
            report += "✅ No recent errors found\n"
    else:
        report += f"❌ **Error Check:** FAILED\n- Error: {error_results.get('error')}\n"

    report += "\n---\n\n## 5. Recent Changes\n\n"

    # Git history results
    git_results = results.get('git_history', {})
    if git_results.get('success'):
        data = git_results.get('data', {})
        report += "**Last 5 Commits:**\n```\n"
        for commit in data.get('recent_commits', []):
            report += f"{commit}\n"
        report += "```\n"
    else:
        report += f"❌ **Git History:** FAILED\n- Error: {git_results.get('error')}\n"

    report += "\n---\n\n## Summary\n\n"

    # Generate summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r.get('success'))

    report += f"**Overall Status:** {passed_tests}/{total_tests} components healthy\n\n"

    if passed_tests == total_tests:
        report += "🎉 **All systems operational**\n"
    elif passed_tests >= total_tests * 0.8:
        report += "⚠️ **Most systems operational, minor issues detected**\n"
    else:
        report += "🚨 **Multiple system issues detected, immediate attention required**\n"

    return report

def main():
    """Run all diagnostics and generate report"""
    print("🔍 Starting Platform Diagnostics...")
    print("=" * 50)

    results = {}

    # Run all tests
    results['database'] = test_database()
    results['s3'] = test_s3()
    results['ai_apis'] = test_ai_apis()
    results['api_endpoints'] = test_api_endpoints()
    results['credentials'] = check_credentials()
    results['recent_errors'] = check_recent_errors()
    results['git_history'] = check_git_history()

    # Generate report
    report = generate_report(results)

    # Save report
    report_file = Path('/Users/josephs./internal-platform/DIAGNOSTIC_REPORT.md')
    with open(report_file, 'w') as f:
        f.write(report)

    print("=" * 50)
    print(f"📄 Diagnostic report saved to: {report_file}")

    # Copy to outputs directory if it exists
    outputs_dir = Path('/mnt/user-data/outputs')
    if outputs_dir.exists():
        output_file = outputs_dir / 'DIAGNOSTIC_REPORT.md'
        with open(output_file, 'w') as f:
            f.write(report)
        print(f"📄 Report also copied to: {output_file}")

    return results

if __name__ == "__main__":
    main()