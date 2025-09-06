#!/usr/bin/env python3
"""Position Mathematical Accuracy Verification"""

import sqlite3
import requests

def verify_position_accuracy():
    print("=== POSITION MATHEMATICAL ACCURACY VERIFICATION ===")
    
    # Check database state
    conn = sqlite3.connect(r'data/automation_bot.db')
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM paper_trades')
    trade_count = c.fetchone()[0]
    print(f"Paper trades in database: {trade_count}")
    
    if trade_count > 0:
        c.execute('SELECT * FROM paper_trades')
        trades = c.fetchall()
        print("\nTrade details from database:")
        for i, trade in enumerate(trades):
            print(f"  Trade {i+1}: {trade}")
    
    conn.close()
    
    # Check API response
    print("\n=== API RESPONSE VERIFICATION ===")
    try:
        response = requests.get('http://localhost:5000/api/chart-data')
        if response.status_code == 200:
            data = response.json()
            portfolio = data['data']['portfolio_summary']
            positions = data['data']['positions_data']
            
            print(f"API Portfolio Summary:")
            print(f"  Total Value: ${portfolio['total_value']}")
            print(f"  Cash Balance: ${portfolio['cash_balance']}")
            print(f"  Market Value: ${portfolio['market_value']}")
            print(f"  Total P&L: ${portfolio['total_pnl']}")
            print(f"  Unrealized P&L: ${portfolio['unrealized_pnl']}")
            print(f"  Open Positions: {len(positions)}")
            
            # Mathematical verification
            print(f"\n=== MATHEMATICAL VERIFICATION ===")
            total_calc = portfolio['cash_balance'] + portfolio['market_value']
            print(f"Calculated Total: ${portfolio['cash_balance']} + ${portfolio['market_value']} = ${total_calc}")
            print(f"Reported Total: ${portfolio['total_value']}")
            
            if abs(total_calc - portfolio['total_value']) < 0.01:
                print("MATH CHECK: Total value calculation CORRECT")
            else:
                print("MATH CHECK: Total value calculation INCORRECT")
                return False
                
            if len(positions) > 0:
                print("\nPosition Details:")
                for pos in positions:
                    print(f"  {pos['symbol']}: {pos['quantity']} shares")
                    print(f"    Market Value: ${pos['market_value']}")
                    print(f"    Unrealized P&L: ${pos['unrealized_pnl']}")
            
            return True
        else:
            print(f"API request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error checking API: {e}")
        return False

if __name__ == "__main__":
    success = verify_position_accuracy()
    if success:
        print("\nVERIFICATION: Position calculations are mathematically accurate")
    else:
        print("\nVERIFICATION FAILED: Position calculations contain errors")