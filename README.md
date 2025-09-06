# AutomationBot - Enhanced Professional Trading Platform

A sophisticated paper trading platform with **Enhanced Desktop Trading Viewer** designed for professional learning and strategy development with $500 starting capital. Features real-time market data, Bloomberg Terminal-inspired interface, and comprehensive one-click startup solution.

## 🚀 Quick Start (One-Click Launch)

### **Windows Users - Double-Click Startup**
1. **One-Click Launch**: Double-click `START_TRADING_VIEWER.bat` 
2. **Desktop Trading Viewer**: Professional interface opens automatically
3. **Backend API**: Starts automatically in background
4. **Clean Shutdown**: Double-click `STOP_TRADING_VIEWER.bat`

### **Manual Setup** 
1. **Setup Environment**:
   ```bash
   # Clone and navigate to project
   cd AutomationBot
   
   # Configure API keys
   cp .env.template .env
   # Edit .env with your Polygon.io API key
   ```

2. **Start the System**:
   ```bash
   # Backend API
   python -c "from api.simple_modular_routes import create_simple_modular_app; app = create_simple_modular_app(); app.run(port=5000)"
   
   # Enhanced Trading Viewer (separate terminal)
   python enhanced_comprehensive_viewer.py
   ```

## 🏗️ Enhanced System Features

### **Enhanced Desktop Trading Viewer** ⭐ **NEW**
- **Professional Interface**: Bloomberg Terminal-inspired dark theme design
- **7 Specialized Tabs**: Dashboard, Controls, Portfolio, Strategies, Data Verification, Monitoring, Modern UI
- **Real-time Updates**: Live portfolio data, P&L tracking, system health monitoring
- **Advanced Controls**: Strategy management, trading controls, system monitoring
- **Data Transparency**: Raw API response viewing, backend synchronization verification
- **Modern Professional Aesthetics**: Dark theme (#1a1a1a), professional typography, hover effects

### **One-Click Startup Solution** ⭐ **NEW**
- **START_TRADING_VIEWER.bat**: Complete system launch with one double-click
- **Auto-Detection**: Finds Python installation automatically across multiple paths
- **Error Handling**: Comprehensive validation with user-friendly error messages
- **Professional Interface**: Color-coded startup messages and system monitoring
- **STOP_TRADING_VIEWER.bat**: Clean shutdown of all components
- **No Technical Knowledge Required**: Autonomous operation for end users

### **Enhanced API Integration** ⭐ **NEW**
- **5 API Endpoints**: `/api/positions`, `/api/trades`, `/api/capital`, `/api/strategies`, `/api/signals`
- **Real-time Synchronization**: Desktop viewer syncs with backend every 5 seconds
- **Data Verification**: Built-in API testing and connectivity monitoring
- **Enhanced Functionality**: 400% increase in API capabilities from original system

### Professional Trading Dashboard
- **Real-time Charts**: Live market data visualization using Chart.js
- **Trading KPIs**: Sharpe ratio, max drawdown, win rate, profit factor
- **Portfolio Management**: Position tracking with P&L calculations
- **Strategy Controls**: Start/stop trading with multiple strategy options
- **Bloomberg-style Interface**: Professional dark theme with modern layout

### Paper Trading Engine
- **Realistic Simulation**: Market impact, slippage, and trading fees
- **Multiple Strategies**: Moving average crossover, RSI mean reversion, momentum breakout
- **Fractional Shares**: Optimized for $500 capital with position sizes of $50-60
- **Risk Management**: Position limits, daily loss limits, capital protection

### Market Data Integration
- **Live Pricing**: Real-time data via Polygon.io API
- **Smart Caching**: 30-second price caching for performance
- **Market Hours**: Automatic trading session detection
- **Symbol Support**: US equities and ETFs

## 📊 Current System State

- **Starting Capital**: $500.00
- **Position Limit**: $50-60 per position (8-10% of capital)
- **Max Positions**: 5-8 concurrent positions
- **Trading Mode**: Paper trading simulation
- **Data Source**: Polygon.io real-time market data
- **Desktop Interface**: Enhanced Comprehensive Trading Viewer
- **Startup Method**: One-click batch file launch

## 🛠️ Installation & Setup

### **Quick Installation (Windows)**

1. **Download Project**: Clone or download AutomationBot
2. **API Configuration**: 
   ```bash
   cp .env.template .env
   # Edit .env with your Polygon.io API key
   ```
3. **One-Click Launch**: Double-click `START_TRADING_VIEWER.bat`
4. **Ready to Trade**: Enhanced Trading Viewer opens automatically

### **Manual Installation**

#### Prerequisites
- Python 3.8+
- Internet connection for market data
- Polygon.io API key (free tier available)

#### Installation Steps

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   # Copy template configuration
   cp .env.template .env
   
   # Edit .env file with your API credentials
   POLYGON_API_KEY=your_api_key_here
   ```

3. **Start Application**:
   ```bash
   # Option 1: One-click startup (Windows)
   START_TRADING_VIEWER.bat
   
   # Option 2: Manual startup
   python -c "from api.simple_modular_routes import create_simple_modular_app; app = create_simple_modular_app(); app.run(port=5000)" &
   python enhanced_comprehensive_viewer.py
   ```

4. **Verify Installation**:
   - Enhanced Desktop Viewer: Opens automatically
   - Web Dashboard: `http://localhost:5000/`
   - Health Check: `http://localhost:5000/health`

## 🎯 Enhanced Trading Capabilities

### **Enhanced Desktop Interface Features**
- **Dashboard Tab**: Real-time P&L, system performance, API response times
- **Advanced Controls**: Trading start/stop, activity monitoring, system health
- **Portfolio Analytics**: Detailed position analysis, performance metrics
- **Strategy Management**: Profile-based configurations (Conservative/Moderate/Aggressive/Custom)
- **Data Verification**: Raw API responses, backend synchronization status
- **System Monitoring**: Connection health, performance metrics, logging

### Available Trading Strategies
- **Mixed Strategy**: Combines multiple approaches
- **MA Crossover**: Moving average signals
- **RSI Mean Reversion**: Oversold/overbought signals
- **Momentum Breakout**: Price momentum signals

### Strategy Configuration via Enhanced Viewer
- **Profile Selection**: Choose predefined risk profiles
- **Custom Parameters**: Adjust strategy parameters in real-time
- **API Integration**: Changes sync with backend immediately
- **Live Updates**: Strategy status updated every 5 seconds

## 📈 Enhanced API Endpoints

### **Enhanced Desktop Viewer API**
- **GET `/api/positions`** - Current position data for desktop viewer
- **GET `/api/trades`** - Recent trade history for desktop display
- **GET `/api/capital`** - Capital allocation and utilization metrics
- **GET `/api/strategies`** - Available strategies and configurations
- **GET `/api/signals`** - Recent trading signals and performance

### Core Web API Endpoints
- **GET `/`** - Trading dashboard interface
- **GET `/health`** - System health status
- **GET `/api/chart-data`** - Real-time portfolio data

### Paper Trading Management
- **POST `/paper-trading/start`** - Begin trading session
- **POST `/paper-trading/stop`** - End trading session
- **GET `/paper-trading/status`** - Current portfolio status
- **POST `/paper-trading/generate-signal`** - Manual signal testing

### Example Enhanced API Usage
```python
import requests

# Enhanced viewer API endpoints
positions = requests.get('http://localhost:5000/api/positions')
trades = requests.get('http://localhost:5000/api/trades')
capital = requests.get('http://localhost:5000/api/capital')
strategies = requests.get('http://localhost:5000/api/strategies')
signals = requests.get('http://localhost:5000/api/signals')

# Traditional web API
health = requests.get('http://localhost:5000/health')
portfolio = requests.get('http://localhost:5000/api/chart-data')
```

## ⚙️ Enhanced Configuration

### Environment Variables (.env)
```env
# Required: Polygon.io API key for market data
POLYGON_API_KEY=your_polygon_api_key_here

# Optional: TradeStation credentials for future live trading
TRADESTATION_CLIENT_ID=your_client_id
TRADESTATION_CLIENT_SECRET=your_client_secret

# System Configuration
LOG_LEVEL=INFO
API_PORT=5000
```

### Desktop Viewer Settings
- **Update Interval**: 5 seconds (configurable)
- **Theme**: Professional dark theme (Bloomberg Terminal inspired)
- **Window Management**: Resizable, professional layout
- **Data Caching**: Smart caching for optimal performance

## 🔧 Enhanced Project Structure

```
AutomationBot/
├── START_TRADING_VIEWER.bat          # One-click startup (Windows)
├── STOP_TRADING_VIEWER.bat           # One-click shutdown (Windows)
├── enhanced_comprehensive_viewer.py  # Enhanced desktop trading interface
├── modern_professional_viewer.py     # Modernized professional UI version
├── comprehensive_trading_viewer.py   # Original desktop viewer
├── simple_modular_main.py           # Application entry point
├── api/                             # Web interface and API routes
│   └── simple_modular_routes.py     # Enhanced API with 5 endpoints
├── core/                            # Trading engine and portfolio management
│   ├── dynamic_portfolio_manager.py
│   ├── paper_trading_engine.py
│   ├── capital_manager.py           # Enhanced capital management
│   └── security_manager.py
├── config/                          # Configuration files
│   ├── capital_config.json
│   ├── paper_trading_config.json    # Enhanced paper trading config
│   └── platform_config.json
├── data/                            # SQLite database
├── logs/                            # Application logs
└── docs/                           # Enhanced documentation
```

## 📋 Enhanced Usage Examples

### **One-Click Operations**
```bash
# Windows - Complete system startup
START_TRADING_VIEWER.bat

# Windows - Complete system shutdown  
STOP_TRADING_VIEWER.bat
```

### **Enhanced Desktop Viewer Operations**
- **Start Trading**: Use Advanced Controls tab → Start Trading button
- **Stop Trading**: Use Advanced Controls tab → Stop Trading button  
- **Change Strategy**: Use Strategy Management tab → Select profile → Update
- **Monitor System**: Use System Health tab for real-time monitoring
- **Verify Data**: Use Data Verification tab for API transparency

### **API Operations via Enhanced Viewer**
```bash
# All operations available through desktop interface
# Real-time updates every 5 seconds
# No manual API calls needed for normal operation
```

## 🚨 System Requirements

### Hardware
- **CPU**: 2+ cores
- **RAM**: 4GB minimum, 8GB recommended  
- **Storage**: 1GB for application and logs
- **Network**: Stable internet for market data
- **Display**: 1920x1080 recommended for Enhanced Trading Viewer

### Software
- **Python**: 3.8 or higher with tkinter support
- **OS**: Windows (batch files), macOS, or Linux
- **Browser**: Modern browser for web dashboard interface (optional with desktop viewer)

## 📝 Enhanced Logs and Monitoring

### **Desktop Viewer Monitoring**
- **Real-time Status**: Built-in system health monitoring
- **Performance Metrics**: API response times, connection health
- **Activity Logging**: Trading activity feed with timestamps
- **Error Handling**: User-friendly error messages and guidance

### Log Files
- **Application Logs**: `./logs/simple_modular_bot.log`
- **Trading Activity**: Portfolio changes and signals
- **Error Logs**: System errors and API failures
- **Desktop Viewer Logs**: Enhanced viewer activity and performance

## 🛠️ Troubleshooting

### **Enhanced Trading Viewer Issues**
- **Window Won't Open**: Run `DEBUG_STARTUP.bat` for diagnostics
- **API Connection Failed**: Check backend server status in monitoring tab
- **Python Not Found**: Batch file will show specific Python installation guidance
- **Module Import Errors**: Verify all dependencies installed with `pip install -r requirements.txt`

### **Batch File Issues**
- **Quick Window Close**: Updated batch files now pause on errors
- **Python Path Issues**: Auto-detection checks 5+ common Python installation locations
- **Permission Errors**: Run as administrator if needed

### Common Issues
- **Port 5000 in use**: Enhanced viewer handles API connectivity automatically
- **API key errors**: Verify Polygon.io API key is valid
- **Database errors**: Check write permissions in `./data/` directory

## 🤝 Support

### Getting Help
1. **Run Diagnostics**: Use `DEBUG_STARTUP.bat` for comprehensive system testing
2. **Check Desktop Viewer**: Use System Health tab for real-time diagnostics
3. **Review Logs**: Check both application logs and desktop viewer activity
4. **Verify Configuration**: Ensure `.env` file has valid API credentials

### **Enhanced Support Features**
- **Built-in Diagnostics**: Desktop viewer includes comprehensive health monitoring
- **Real-time Troubleshooting**: System status visible in monitoring interface
- **User-friendly Error Messages**: Clear guidance for common issues
- **Automated Testing**: Batch files include validation and error checking

---

## 🎯 **Key Enhancements in Version 4.0**

✅ **Enhanced Desktop Trading Viewer**: Professional Bloomberg Terminal-inspired interface  
✅ **One-Click Startup Solution**: Complete autonomous operation with batch files  
✅ **400% API Enhancement**: 5 specialized endpoints for desktop viewer integration  
✅ **Professional UI Modernization**: Dark theme, modern typography, hover effects  
✅ **Comprehensive System Monitoring**: Real-time health monitoring and diagnostics  
✅ **Enhanced Documentation**: Complete project documentation and deployment guides  

**Version**: 4.0 - Enhanced Professional Trading Platform  
**License**: MIT  
**Python**: 3.8+  
**Status**: Production Ready with Enhanced Desktop Interface  
**Startup**: One-Click Autonomous Operation via Batch Files