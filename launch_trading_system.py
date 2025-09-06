#!/usr/bin/env python3
"""
AutomationBot Trading System Launcher
Ensures backend is running and launches comprehensive viewer
SINGLE SOURCE OF TRUTH LAUNCHER
"""

import subprocess
import sys
import time
import requests
import threading
from pathlib import Path
import os

class TradingSystemLauncher:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.backend_process = None
        self.backend_running = False
        self.backend_url = "http://localhost:5000"
        
    def check_backend_status(self):
        """Check if backend is running"""
        try:
            response = requests.get(f"{self.backend_url}/api/chart-data", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_backend(self):
        """Start the backend server"""
        print("Starting AutomationBot backend server...")
        
        try:
            # Change to the project directory
            os.chdir(self.base_dir)
            
            # Start the backend server
            self.backend_process = subprocess.Popen([
                sys.executable, "-m", "api.simple_modular_routes"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for backend to start
            max_wait = 30  # 30 seconds max wait
            wait_count = 0
            
            print("Waiting for backend to start...")
            while wait_count < max_wait:
                if self.check_backend_status():
                    print("Backend server is running!")
                    self.backend_running = True
                    return True
                    
                time.sleep(1)
                wait_count += 1
                print(f"   Waiting... ({wait_count}/{max_wait})")
            
            print("Backend failed to start within timeout")
            return False
            
        except Exception as e:
            print(f"Error starting backend: {e}")
            return False
    
    def launch_comprehensive_viewer(self):
        """Launch the comprehensive trading viewer"""
        print("📊 Launching Comprehensive Trading Viewer...")
        
        try:
            # Launch the viewer
            viewer_path = self.base_dir / "comprehensive_trading_viewer.py"
            
            if not viewer_path.exists():
                print(f"❌ Viewer not found at {viewer_path}")
                return False
                
            subprocess.run([sys.executable, str(viewer_path)])
            return True
            
        except Exception as e:
            print(f"❌ Error launching viewer: {e}")
            return False
    
    def shutdown_backend(self):
        """Shutdown the backend server"""
        if self.backend_process:
            print("🔴 Shutting down backend server...")
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
            print("✅ Backend server stopped")
    
    def run(self):
        """Run the complete trading system"""
        print("="*70)
        print("AUTOMATIONBOT COMPREHENSIVE TRADING SYSTEM")
        print("   SINGLE SOURCE OF TRUTH - NO WEB DEPENDENCY")
        print("="*70)
        print()
        
        try:
            # Check if backend is already running
            if self.check_backend_status():
                print("✅ Backend already running - connecting to existing instance")
                self.backend_running = True
            else:
                # Start backend
                if not self.start_backend():
                    print("❌ Failed to start backend server")
                    return False
            
            print()
            print("🎯 SYSTEM READY - Launching Comprehensive Trading Viewer")
            print("📊 This desktop interface is now your SINGLE SOURCE OF TRUTH")
            print("🚫 No web browser needed - all functionality is here")
            print()
            
            # Launch viewer
            success = self.launch_comprehensive_viewer()
            
            return success
            
        except KeyboardInterrupt:
            print("\n🔴 Interrupted by user")
            return False
        except Exception as e:
            print(f"❌ System launch error: {e}")
            return False
        finally:
            # Only shutdown if we started the backend
            if self.backend_process and self.backend_running:
                self.shutdown_backend()

if __name__ == "__main__":
    launcher = TradingSystemLauncher()
    success = launcher.run()
    
    if not success:
        print("\n❌ System launch failed")
        input("Press Enter to exit...")
        sys.exit(1)
    else:
        print("\n✅ Trading system completed successfully")