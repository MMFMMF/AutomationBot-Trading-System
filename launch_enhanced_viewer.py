#!/usr/bin/env python3
"""
Launch Enhanced Comprehensive Trading Viewer
Complete desktop trading control center with all functionality
"""

import requests
import subprocess
import sys
import time
from pathlib import Path

def check_backend():
    """Check if backend is running and ready"""
    try:
        response = requests.get("http://127.0.0.1:5000/api/chart-data", timeout=3)
        return response.status_code == 200
    except:
        return False

def verify_enhanced_functionality():
    """Verify all enhanced functionality is available"""
    endpoints = ['/api/positions', '/api/trades', '/api/capital', '/api/strategies', '/api/signals']
    working = 0
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"http://127.0.0.1:5000{endpoint}", timeout=2)
            if response.status_code == 200:
                working += 1
        except:
            pass
    
    return working == len(endpoints)

def main():
    print("ENHANCED COMPREHENSIVE TRADING VIEWER LAUNCHER")
    print("="*60)
    print("Complete Desktop Trading Control Center")
    print("Single Source of Truth - No Web Dependency")
    print()
    
    # Check backend
    if not check_backend():
        print("Backend not running. Please start the backend first:")
        print("python -c \"from api.simple_modular_routes import create_simple_modular_app; app = create_simple_modular_app(); app.run(host='127.0.0.1', port=5000)\"")
        print()
        input("Press Enter after starting backend...")
        
        if not check_backend():
            print("Still cannot connect to backend. Exiting.")
            return False
    
    # Verify enhanced functionality
    print("Verifying enhanced functionality...")
    if verify_enhanced_functionality():
        print("All enhanced API endpoints: WORKING")
    else:
        print("Some API endpoints not responding - viewer may have limited functionality")
    
    print()
    print("Backend connected successfully!")
    print("Launching Enhanced Comprehensive Trading Viewer...")
    print()
    print("ENHANCED FEATURES AVAILABLE:")
    print("- Complete dashboard metrics with real-time updates")
    print("- Enhanced trading controls with state management")
    print("- Advanced strategy configuration with preset profiles")
    print("- Real-time data verification with API transparency")
    print("- Comprehensive system health monitoring")
    print("- Enhanced screenshot verification system")
    print("- 7 specialized tabs with complete functionality")
    print()
    
    # Launch enhanced viewer
    try:
        viewer_path = Path(__file__).parent / "enhanced_comprehensive_viewer.py"
        if not viewer_path.exists():
            print(f"Enhanced viewer not found at {viewer_path}")
            print("Please ensure enhanced_comprehensive_viewer.py exists")
            return False
            
        subprocess.run([sys.executable, str(viewer_path)])
        return True
    except Exception as e:
        print(f"Error launching enhanced viewer: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("Enhanced Comprehensive Trading Viewer closed successfully")
    else:
        print("Failed to launch Enhanced Comprehensive Trading Viewer")
        input("Press Enter to exit...")