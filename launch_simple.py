#!/usr/bin/env python3
"""
AutomationBot Simple Launcher - ASCII only
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def check_backend():
    """Check if backend is running"""
    try:
        response = requests.get("http://localhost:5000/api/chart-data", timeout=3)
        return response.status_code == 200
    except:
        return False

def main():
    print("="*60)
    print("AUTOMATIONBOT COMPREHENSIVE TRADING VIEWER")
    print("SINGLE SOURCE OF TRUTH - NO WEB DEPENDENCY")
    print("="*60)
    print()
    
    # Check if backend is running
    if not check_backend():
        print("Backend not running. Please start the backend first:")
        print("python -m api.simple_modular_routes")
        print()
        input("Press Enter after starting backend...")
        
        if not check_backend():
            print("Still cannot connect to backend. Exiting.")
            return
    
    print("Backend connected successfully!")
    print("Launching Comprehensive Trading Viewer...")
    print()
    
    # Launch viewer
    try:
        viewer_path = Path(__file__).parent / "comprehensive_trading_viewer.py"
        subprocess.run([sys.executable, str(viewer_path)])
    except Exception as e:
        print(f"Error launching viewer: {e}")

if __name__ == "__main__":
    main()