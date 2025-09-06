import time
import pyautogui
from PIL import Image, ImageGrab
import tkinter as tk

def focus_trading_viewer():
    """Focus the trading viewer window and take screenshot"""
    try:
        # Try to find the trading viewer window
        import win32gui
        import win32con
        
        def find_trading_window(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if "Modern Professional Trading Viewer" in window_text or "Trading" in window_text:
                    windows.append((hwnd, window_text))
        
        windows = []
        win32gui.EnumWindows(find_trading_window, windows)
        
        if windows:
            hwnd, title = windows[0]
            print(f"Found window: {title}")
            
            # Bring window to foreground
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(1)
            
            # Take screenshot
            screenshot = ImageGrab.grab()
            screenshot.save('AFTER_focused_trading_viewer.png')
            print("Screenshot saved as AFTER_focused_trading_viewer.png")
            return True
        else:
            print("No trading viewer window found")
            return False
            
    except ImportError:
        print("win32gui not available, taking full screenshot")
        screenshot = ImageGrab.grab()
        screenshot.save('AFTER_full_screen.png')
        print("Full screenshot saved as AFTER_full_screen.png")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    focus_trading_viewer()