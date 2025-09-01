# AutomationBot - Professional Trading Platform

A sophisticated paper trading platform designed for learning and strategy development with $500 starting capital. Features real-time market data, professional dashboard, and multiple trading strategies.

## 🚀 Quick Start

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
   python simple_modular_main.py
   ```

3. **Access Dashboard**:
   - Open browser to: `http://localhost:5000/`
   - View real-time trading dashboard with charts and KPIs

## 🏗️ System Features

### Professional Trading Dashboard
- **Real-time Charts**: Live market data visualization using Chart.js
- **Trading KPIs**: Sharpe ratio, max drawdown, win rate, profit factor
- **Portfolio Management**: Position tracking with P&L calculations
- **Strategy Controls**: Start/stop trading with multiple strategy options
- **Bloomberg-style Interface**: Dark theme with professional layout

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

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Internet connection for market data
- Polygon.io API key (free tier available)

### Installation Steps

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
   python simple_modular_main.py
   ```

4. **Verify Installation**:
   - Dashboard: `http://localhost:5000/`
   - Health Check: `http://localhost:5000/health`

## 🎯 Trading Strategies

### Available Strategies
- **Mixed Strategy**: Combines multiple approaches
- **MA Crossover**: Moving average signals
- **RSI Mean Reversion**: Oversold/overbought signals
- **Momentum Breakout**: Price momentum signals

### Strategy Configuration
```bash
# Start paper trading with mixed strategy
curl -X POST http://localhost:5000/paper-trading/start \
  -H "Content-Type: application/json" \
  -d '{"strategy": "mixed", "signal_interval": 2}'
```

## 📈 API Endpoints

### Core Endpoints
- **GET `/`** - Trading dashboard interface
- **GET `/health`** - System health status
- **GET `/api/chart-data`** - Real-time portfolio data

### Paper Trading Management
- **POST `/paper-trading/start`** - Begin trading session
- **POST `/paper-trading/stop`** - End trading session
- **GET `/paper-trading/status`** - Current portfolio status
- **POST `/paper-trading/generate-signal`** - Manual signal testing

### Example API Usage
```python
import requests

# Check system health
health = requests.get('http://localhost:5000/health')
print(health.json())

# Get portfolio data
portfolio = requests.get('http://localhost:5000/api/chart-data')
print(portfolio.json())

# Start trading
trading = requests.post('http://localhost:5000/paper-trading/start', 
                       json={"strategy": "mixed"})
print(trading.json())
```

## ⚙️ Configuration

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

### Risk Management Settings
- **Max Position Size**: 10% of capital (~$50)
- **Max Daily Loss**: 5% of capital (~$25)
- **Position Diversity**: 5-8 positions maximum
- **Fractional Shares**: Enabled for optimal capital utilization

## 🔧 Project Structure

```
AutomationBot/
├── simple_modular_main.py    # Application entry point
├── api/                      # Web interface and API routes
│   └── simple_modular_routes.py
├── core/                     # Trading engine and portfolio management
│   ├── dynamic_portfolio_manager.py
│   ├── paper_trading_engine.py
│   └── security_manager.py
├── config/                   # Configuration files
│   ├── capital_config.json
│   └── platform_config.json
├── data/                     # SQLite database
└── logs/                     # Application logs
```

## 📋 Usage Examples

### Start Paper Trading
```bash
# Basic mixed strategy
curl -X POST http://localhost:5000/paper-trading/start \
  -H "Content-Type: application/json" \
  -d '{"strategy": "mixed"}'

# Specific strategy with custom interval
curl -X POST http://localhost:5000/paper-trading/start \
  -H "Content-Type: application/json" \
  -d '{"strategy": "ma_crossover", "signal_interval": 5}'
```

### Check Portfolio Status
```bash
curl http://localhost:5000/paper-trading/status
```

### Generate Test Signal
```bash
curl -X POST http://localhost:5000/paper-trading/generate-signal \
  -H "Content-Type: application/json" \
  -d '{"strategy": "test", "symbol": "AAPL", "side": "buy"}'
```

## 🚨 System Requirements

### Hardware
- **CPU**: 2+ cores
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 1GB for application and logs
- **Network**: Stable internet for market data

### Software
- **Python**: 3.8 or higher
- **OS**: Windows, macOS, or Linux
- **Browser**: Modern browser for dashboard interface

## 📝 Logs and Monitoring

### Log Files
- **Application Logs**: `./logs/simple_modular_bot.log`
- **Trading Activity**: Portfolio changes and signals
- **Error Logs**: System errors and API failures

### Health Monitoring
```bash
# System health check
curl http://localhost:5000/health

# Expected response includes:
# - System status
# - Portfolio value
# - Database connection
# - API provider status
```

## 🤝 Support

### Common Issues
- **Port 5000 in use**: Change `API_PORT` in `.env` file
- **API key errors**: Verify Polygon.io API key is valid
- **Database errors**: Check write permissions in `./data/` directory

### Getting Help
1. Check application logs in `./logs/` directory
2. Verify API configuration in `.env` file
3. Test API connectivity with health endpoint
4. Review system requirements and installation steps

---

**Version**: 3.0  
**License**: MIT  
**Python**: 3.8+  
**Status**: Production Ready for Paper Trading