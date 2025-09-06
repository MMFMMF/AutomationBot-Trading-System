from PIL import ImageGrab
import time

def take_screenshot():
    """Take a screenshot after a short delay"""
    print("Taking screenshot in 3 seconds...")
    time.sleep(3)
    
    screenshot = ImageGrab.grab()
    screenshot.save('AFTER_trading_viewer.png')
    print("Screenshot saved as AFTER_trading_viewer.png")

if __name__ == "__main__":
    take_screenshot()