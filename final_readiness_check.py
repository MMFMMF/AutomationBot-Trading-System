#!/usr/bin/env python3
"""Final system readiness verification"""

import requests
import sqlite3

def final_readiness_check():
    print("=== FINAL SYSTEM READINESS CHECK ===")
    
    # API Check
    try:
        response = requests.get('http://localhost:5000/api/chart-data')
        if response.status_code == 200:
            data = response.json()
            ps = data['data']['portfolio_summary']
            
            print("API VERIFICATION:")
            print(f"  Total Value: ${ps['total_value']}")
            print(f"  Cash Balance: ${ps['cash_balance']}")
            print(f"  Market Value: ${ps['market_value']}")
            print(f"  Total P&L: ${ps['total_pnl']}")
            print(f"  Open Positions: {len(data['data']['positions_data'])}")
            print(f"  Data Status: {data['data'].get('data_status', 'unknown')}")
            
            # Mathematical consistency check
            math_consistent = abs(ps['total_value'] - (ps['cash_balance'] + ps['market_value'])) < 0.01
            print(f"  Mathematical Consistency: {math_consistent}")
            
            api_ready = (ps['total_value'] == 500.0 and 
                        ps['cash_balance'] == 500.0 and 
                        ps['market_value'] == 0.0 and 
                        ps['total_pnl'] == 0.0 and
                        len(data['data']['positions_data']) == 0)
            print(f"  Clean Baseline: {api_ready}")
        else:
            print("API VERIFICATION: FAILED")
            return False
    except Exception as e:
        print(f"API VERIFICATION ERROR: {e}")
        return False
    
    # Database Check
    try:
        conn = sqlite3.connect(r'data/automation_bot.db')
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM paper_trades')
        trade_count = c.fetchone()[0]
        
        c.execute('SELECT key, value FROM portfolio_config WHERE key = "total_capital"')
        capital_result = c.fetchone()
        total_capital = float(capital_result[1]) if capital_result else 0.0
        
        conn.close()
        
        print("DATABASE VERIFICATION:")
        print(f"  Paper Trades: {trade_count}")
        print(f"  Total Capital: ${total_capital}")
        
        db_ready = (trade_count == 0 and total_capital == 500.0)
        print(f"  Clean Database: {db_ready}")
        
    except Exception as e:
        print(f"DATABASE VERIFICATION ERROR: {e}")
        return False
    
    # Health Check
    try:
        response = requests.get('http://localhost:5000/health')
        if response.status_code == 200:
            data = response.json()
            providers = data['data']['components']['providers']
            
            print("HEALTH VERIFICATION:")
            for provider_type, provider_info in providers.items():
                print(f"  {provider_type}: {provider_info['status']}")
            
            all_connected = all(p['status'] == 'connected' for p in providers.values())
            print(f"  All Providers Connected: {all_connected}")
        else:
            print("HEALTH VERIFICATION: FAILED")
            return False
    except Exception as e:
        print(f"HEALTH VERIFICATION ERROR: {e}")
        return False
    
    print()
    print("FINAL ASSESSMENT:")
    if api_ready and db_ready and all_connected:
        print("SYSTEM READY FOR BUYER TESTING")
        return True
    else:
        print("SYSTEM NOT READY - ISSUES DETECTED")
        return False

if __name__ == "__main__":
    success = final_readiness_check()
    if success:
        print("✅ VERIFICATION COMPLETE: System ready for 72-hour autonomous testing")
    else:
        print("❌ VERIFICATION FAILED: System requires additional fixes")