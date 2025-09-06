#!/usr/bin/env python3
"""
AutomationBot Dashboard Viewer
Creates a dedicated application window for viewing the dashboard
"""

import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox
import requests
import webbrowser
import subprocess
import sys
import time
import threading

class DashboardViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AutomationBot Dashboard Viewer")
        self.root.geometry("1200x800")
        self.root.configure(bg='#0f1419')
        
        # Dashboard URL
        self.dashboard_url = "http://localhost:5000"
        
        self.create_widgets()
        self.check_server_status()
        
    def create_widgets(self):
        # Header frame
        header_frame = tk.Frame(self.root, bg='#1a1f2e', height=80)
        header_frame.pack(fill='x', padx=10, pady=5)
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(header_frame, text="AutomationBot Dashboard Viewer", 
                              font=('Arial', 18, 'bold'), fg='#00d4ff', bg='#1a1f2e')
        title_label.pack(side='left', padx=20, pady=20)
        
        # Status label
        self.status_label = tk.Label(header_frame, text="Checking server...", 
                                   font=('Arial', 12), fg='#a0a0a0', bg='#1a1f2e')
        self.status_label.pack(side='right', padx=20, pady=20)
        
        # Control frame
        control_frame = tk.Frame(self.root, bg='#252b3d', height=60)
        control_frame.pack(fill='x', padx=10, pady=5)
        control_frame.pack_propagate(False)
        
        # Buttons
        self.refresh_btn = tk.Button(control_frame, text="🔄 Refresh Dashboard", 
                                   command=self.refresh_dashboard,
                                   bg='#00d4ff', fg='#0f1419', font=('Arial', 10, 'bold'),
                                   relief='flat', padx=15, pady=8)
        self.refresh_btn.pack(side='left', padx=10, pady=10)
        
        self.open_browser_btn = tk.Button(control_frame, text="🌐 Open in Browser", 
                                        command=self.open_in_browser,
                                        bg='#00ff88', fg='#0f1419', font=('Arial', 10, 'bold'),
                                        relief='flat', padx=15, pady=8)
        self.open_browser_btn.pack(side='left', padx=10, pady=10)
        
        self.start_trading_btn = tk.Button(control_frame, text="▶️ Start Trading", 
                                         command=self.start_trading,
                                         bg='#4ecdc4', fg='#0f1419', font=('Arial', 10, 'bold'),
                                         relief='flat', padx=15, pady=8)
        self.start_trading_btn.pack(side='left', padx=10, pady=10)
        
        self.stop_trading_btn = tk.Button(control_frame, text="⏸️ Stop Trading", 
                                        command=self.stop_trading,
                                        bg='#ff4757', fg='white', font=('Arial', 10, 'bold'),
                                        relief='flat', padx=15, pady=8)
        self.stop_trading_btn.pack(side='left', padx=10, pady=10)
        
        # Info display frame
        info_frame = tk.Frame(self.root, bg='#252b3d')
        info_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Dashboard info text
        self.info_text = tk.Text(info_frame, bg='#252b3d', fg='#ffffff', 
                               font=('Consolas', 11), wrap='word',
                               insertbackground='#00d4ff')
        scrollbar = tk.Scrollbar(info_frame, orient='vertical', command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar.set)
        
        self.info_text.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side='right', fill='y', padx=(0, 10), pady=10)
        
        self.update_dashboard_info()
        
        # Auto-refresh every 10 seconds
        self.root.after(10000, self.auto_refresh)
        
    def check_server_status(self):
        try:
            response = requests.get(self.dashboard_url + "/health", timeout=5)
            if response.status_code == 200:
                self.status_label.config(text="✅ Server Running", fg='#00ff88')
                return True
        except:
            pass
        
        self.status_label.config(text="❌ Server Offline", fg='#ff4757')
        return False
    
    def update_dashboard_info(self):
        try:
            # Get dashboard data
            response = requests.get(self.dashboard_url + "/api/chart-data", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                info_text = "📊 AUTOMATIONBOT DASHBOARD STATUS\n"
                info_text += "=" * 50 + "\n\n"
                
                # Trading summary
                trading_summary = data['data']['trading_summary']
                info_text += f"💰 Available Capital: ${trading_summary['available_capital']:.2f}\n"
                info_text += f"📈 Total P&L: ${trading_summary['total_pnl']:.2f}\n"
                info_text += f"📊 Open Positions: {trading_summary['open_positions']}\n"
                info_text += f"🎯 Total Trades: {trading_summary['total_trades']}\n"
                info_text += f"🏆 Win Rate: {trading_summary['win_rate']:.1f}%\n\n"
                
                # Portfolio summary
                portfolio = data['data']['portfolio_summary']
                info_text += f"💵 Cash Balance: ${portfolio['cash_balance']:.2f}\n"
                info_text += f"📊 Market Value: ${portfolio['market_value']:.2f}\n"
                info_text += f"💎 Total Value: ${portfolio['total_value']:.2f}\n"
                info_text += f"📈 Day Change: ${portfolio['day_change']:.2f} ({portfolio['day_change_percent']:.2f}%)\n\n"
                
                # System status
                system_status = data['data']['system_status']
                info_text += f"🔧 Clean Slate Mode: {'✅ Active' if system_status.get('clean_slate_mode') else '❌ Inactive'}\n"
                info_text += f"🧹 Comprehensive Wipe: {'✅ Completed' if system_status.get('comprehensive_wipe_completed') else '❌ Pending'}\n"
                info_text += f"⏰ Last Reset: {system_status.get('baseline_reset', 'N/A')}\n\n"
                
                info_text += f"🌐 Dashboard URL: {self.dashboard_url}\n"
                info_text += f"🔄 Last Updated: {time.strftime('%H:%M:%S')}\n"
                
                self.info_text.delete(1.0, tk.END)
                self.info_text.insert(tk.END, info_text)
                
                self.status_label.config(text="✅ Dashboard Active", fg='#00ff88')
                
        except Exception as e:
            error_text = f"❌ ERROR LOADING DASHBOARD\n\n{str(e)}\n\n"
            error_text += f"Dashboard URL: {self.dashboard_url}\n"
            error_text += "Please ensure the AutomationBot server is running."
            
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, error_text)
            
            self.status_label.config(text="❌ Connection Error", fg='#ff4757')
    
    def refresh_dashboard(self):
        self.check_server_status()
        self.update_dashboard_info()
        
    def open_in_browser(self):
        webbrowser.open(self.dashboard_url)
        
    def start_trading(self):
        try:
            response = requests.post(self.dashboard_url + "/api/trading/start", timeout=5)
            if response.status_code == 200:
                messagebox.showinfo("Success", "Trading engine started successfully!")
                self.refresh_dashboard()
            else:
                messagebox.showerror("Error", "Failed to start trading engine")
        except Exception as e:
            messagebox.showerror("Error", f"Connection error: {str(e)}")
    
    def stop_trading(self):
        try:
            response = requests.post(self.dashboard_url + "/api/trading/stop", timeout=5)
            if response.status_code == 200:
                messagebox.showinfo("Success", "Trading engine stopped successfully!")
                self.refresh_dashboard()
            else:
                messagebox.showerror("Error", "Failed to stop trading engine")
        except Exception as e:
            messagebox.showerror("Error", f"Connection error: {str(e)}")
    
    def auto_refresh(self):
        self.refresh_dashboard()
        self.root.after(10000, self.auto_refresh)  # Refresh every 10 seconds
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = DashboardViewer()
    app.run()