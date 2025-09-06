import time
import requests
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def capture_dashboard():
    # First, verify the server is responding
    try:
        response = requests.get('http://localhost:5000', timeout=5)
        print(f"Server response status: {response.status_code}")
    except Exception as e:
        print(f"Server check failed: {e}")
        return False
    
    # Configure Edge options
    edge_options = Options()
    edge_options.add_argument('--start-maximized')
    edge_options.add_argument('--disable-cache')
    edge_options.add_argument('--disable-application-cache')
    edge_options.add_argument('--disable-offline-load-stale-cache')
    edge_options.add_argument('--disk-cache-size=0')
    
    driver = None
    try:
        # Create WebDriver instance
        driver = webdriver.Edge(options=edge_options)
        
        # Navigate to dashboard
        print("Navigating to dashboard...")
        driver.get('http://localhost:5000')
        
        # Wait for page to load completely
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait to ensure dynamic content loads
        time.sleep(3)
        
        # Take screenshot
        screenshot_path = r"C:\Users\Kamyar Shah\Documents\AutomationBot\dashboard_selenium.png"
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to: {screenshot_path}")
        
        # Get page title for verification
        title = driver.title
        print(f"Page title: {title}")
        
        return True
        
    except Exception as e:
        print(f"Error capturing dashboard: {e}")
        return False
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    success = capture_dashboard()
    if success:
        print("Dashboard capture completed successfully!")
    else:
        print("Dashboard capture failed!")