#!/usr/bin/env python3
"""Test real market data functionality"""

from providers.polygon_price_provider import PolygonPriceProvider
import os

def test_market_data():
    print("=== MARKET DATA PROVIDER TEST ===")
    
    # Test Polygon provider
    api_key = "0fixRWuE5yPnLldd54hFnvx115Y3fykn"  # From .env file
    provider = PolygonPriceProvider(api_key)
    
    print(f"Provider name: {provider.provider_name}")
    
    # Test getting current price for AAPL
    try:
        price_data = provider.get_current_price("AAPL")
        if price_data:
            print(f"AAPL current price: ${price_data.price}")
            print(f"Timestamp: {price_data.timestamp}")
            print(f"Volume: {price_data.volume}")
            print("MARKET DATA: Successfully retrieved real-time price data")
            return True
        else:
            print("MARKET DATA: Failed to retrieve price data")
            return False
    except Exception as e:
        print(f"MARKET DATA ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_market_data()
    if success:
        print("VERIFICATION: Market data provider working with real prices")
    else:
        print("VERIFICATION FAILED: Market data provider not working")