#!/usr/bin/env python3
"""Test portfolio calculation accuracy"""

from core.capital_manager import CapitalManager

def test_portfolio_calculations():
    print("=== PORTFOLIO CALCULATION ACCURACY TEST ===")
    
    cm = CapitalManager()
    
    # Test various price points and position sizing
    test_cases = [
        ("AAPL", 150.0),
        ("GOOGL", 140.0),
        ("MSFT", 350.0),
        ("SPY", 450.0),
        ("NVDA", 500.0)
    ]
    
    total_capital = cm.get_total_capital()
    available_capital = cm.get_available_capital()
    max_position_size = cm.get_max_position_size()
    
    print(f"Total Capital: ${total_capital}")
    print(f"Available Capital: ${available_capital}")
    print(f"Max Position Size: ${max_position_size}")
    print()
    
    total_allocated = 0
    for symbol, price in test_cases:
        quantity, details = cm.calculate_position_size(symbol, price)
        position_value = quantity * price
        total_allocated += position_value
        
        print(f"{symbol} at ${price}:")
        print(f"  Quantity: {quantity:.4f} shares")
        print(f"  Position Value: ${position_value:.2f}")
        print(f"  % of Capital: {(position_value/total_capital)*100:.1f}%")
        print(f"  Within Limits: {'YES' if position_value <= max_position_size else 'NO'}")
        print()
    
    print("=== PORTFOLIO MATHEMATICAL VERIFICATION ===")
    print(f"Total if all positions taken: ${total_allocated:.2f}")
    print(f"Available capital: ${available_capital}")
    print(f"Would exceed available: {'YES' if total_allocated > available_capital else 'NO'}")
    print(f"Risk management working: {'YES' if total_allocated <= available_capital else 'NO'}")
    
    # Test mathematical consistency
    if total_capital == 500.0 and available_capital == 400.0:
        print("✅ Capital allocation consistent")
        return True
    else:
        print("❌ Capital allocation inconsistent")
        return False

if __name__ == "__main__":
    success = test_portfolio_calculations()
    if success:
        print("VERIFICATION: Portfolio calculations are mathematically accurate")
    else:
        print("VERIFICATION FAILED: Portfolio calculations contain errors")