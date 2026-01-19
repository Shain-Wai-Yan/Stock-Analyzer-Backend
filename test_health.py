#!/usr/bin/env python3
"""
Simple health check script for the API
Usage: python test_health.py [API_URL]
"""
import sys
import requests
from datetime import datetime

def test_api(base_url="http://localhost:8000"):
    """Test API endpoints"""
    print(f"🧪 Testing Stock Gap Analysis API")
    print(f"📍 URL: {base_url}")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Health check
    print("\n1️⃣  Health Check...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {data.get('status', 'unknown')}")
            print(f"   ✅ Version: {data.get('version', 'unknown')}")
            tests_passed += 1
        else:
            print(f"   ❌ Failed: HTTP {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        tests_failed += 1
    
    # Test 2: Gap scanner
    print("\n2️⃣  Gap Scanner...")
    try:
        response = requests.get(f"{base_url}/api/gaps?limit=5", timeout=15)
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            print(f"   ✅ Found {count} gaps")
            if data.get('data'):
                first = data['data'][0]
                print(f"   📊 Example: {first.get('symbol', 'N/A')} - {first.get('gapPercent', 0):.2f}%")
            tests_passed += 1
        else:
            print(f"   ❌ Failed: HTTP {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        tests_failed += 1
    
    # Test 3: Gap details
    print("\n3️⃣  Gap Details (AAPL)...")
    try:
        response = requests.get(f"{base_url}/api/gaps/AAPL", timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                prob = data.get('data', {}).get('probability', {})
                fill_rate = prob.get('fill_rate', 0)
                print(f"   ✅ Fill probability: {fill_rate*100:.1f}%")
                tests_passed += 1
            else:
                print(f"   ⚠️  No gap data available")
                tests_passed += 1
        elif response.status_code == 404:
            print(f"   ⚠️  No current gap (expected)")
            tests_passed += 1
        else:
            print(f"   ❌ Failed: HTTP {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        tests_failed += 1
    
    # Test 4: Backtest
    print("\n4️⃣  Backtest (TSLA)...")
    try:
        response = requests.get(f"{base_url}/api/backtest/TSLA?days=100", timeout=20)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                result = data.get('data', {})
                win_rate = result.get('win_rate', 0)
                trades = result.get('total_trades', 0)
                print(f"   ✅ Win rate: {win_rate*100:.1f}%")
                print(f"   ✅ Total trades: {trades}")
                tests_passed += 1
            else:
                print(f"   ⚠️  No backtest data")
                tests_passed += 1
        else:
            print(f"   ❌ Failed: HTTP {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"🏁 Tests Completed!")
    print(f"   ✅ Passed: {tests_passed}")
    print(f"   ❌ Failed: {tests_failed}")
    print(f"   📊 Success Rate: {tests_passed/(tests_passed+tests_failed)*100:.0f}%")
    
    if tests_failed == 0:
        print("\n🎉 All tests passed! Backend is working correctly.")
        print("\n💡 Next steps:")
        print("   1. Copy your API URL")
        print("   2. Update frontend: NEXT_PUBLIC_API_URL=" + base_url)
        print("   3. Deploy frontend to Vercel")
        print("   4. Start analyzing gaps! 🚀")
    else:
        print("\n⚠️  Some tests failed. Check:")
        print("   - API keys are set correctly")
        print("   - Environment variables are loaded")
        print("   - Alpaca/Groq services are accessible")
        print("   - View backend logs for details")
    
    print("=" * 60)
    
    return tests_failed == 0

if __name__ == "__main__":
    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    success = test_api(api_url)
    sys.exit(0 if success else 1)
