# AutomationBot - Deployment Guide

## Quick Deployment

The AutomationBot paper trading platform is designed for easy local deployment with minimal setup. Follow these steps to get the system running with $500 starting capital.

## System Requirements

### Hardware
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 1GB for application and database
- **Network**: Stable internet connection for market data

### Software
- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Browser**: Modern web browser for dashboard access

## Installation Steps

### 1. Environment Setup

```bash
# Navigate to project directory
cd AutomationBot

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. API Configuration

```bash
# Copy environment template
cp .env.template .env

# Edit .env file with your API credentials
# Required: Polygon.io API key (free tier available)
POLYGON_API_KEY=your_polygon_api_key_here

# Optional: TradeStation credentials for future live trading
TRADESTATION_CLIENT_ID=your_client_id
TRADESTATION_CLIENT_SECRET=your_client_secret

# System settings (defaults work for most setups)
LOG_LEVEL=INFO
API_PORT=5000
```

### 3. Start the Application

```bash
# Start the AutomationBot system
python simple_modular_main.py
```

### 4. Verify Installation

1. **Dashboard Access**: Open `http://localhost:5000/` in your browser
2. **Health Check**: Visit `http://localhost:5000/health` to verify system status
3. **Expected Display**: Bloomberg-style dashboard with $500 starting capital

## Configuration Options

### Environment Variables (.env)

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `POLYGON_API_KEY` | Market data API key | None | Yes |
| `TRADESTATION_CLIENT_ID` | Live trading client ID | None | No |
| `TRADESTATION_CLIENT_SECRET` | Live trading secret | None | No |
| `LOG_LEVEL` | Logging verbosity | INFO | No |
| `API_PORT` | Web interface port | 5000 | No |

### Trading Parameters

The system is pre-configured for $500 micro-trading:

- **Starting Capital**: $500.00
- **Max Position Size**: $50-60 per position (10% of capital)
- **Max Positions**: 5-8 concurrent positions
- **Risk Management**: 5% daily loss limit (~$25)
- **Fractional Shares**: Enabled for optimal capital utilization

### Strategy Configuration

Available trading strategies:
- **Mixed**: Combines multiple approaches (recommended)
- **MA Crossover**: Moving average signals
- **RSI Mean Reversion**: Oversold/overbought signals  
- **Momentum Breakout**: Price momentum signals

## API Key Setup

### Polygon.io API Key (Required)

1. **Sign up**: Visit [polygon.io](https://polygon.io) and create account
2. **Free Tier**: Get free API key with basic market data access
3. **Copy Key**: Add to `.env` file as `POLYGON_API_KEY=your_key_here`
4. **Verify**: Check `/health` endpoint shows "polygon_integration: connected"

### TradeStation API (Optional)

Required only for future live trading capabilities:
1. **Account**: Open TradeStation developer account
2. **Application**: Create new application for API access
3. **Credentials**: Add client ID and secret to `.env` file
4. **Status**: Currently used for configuration only (paper trading active)

## Basic Usage

### Starting Paper Trading

#### Via Dashboard
1. Open `http://localhost:5000/` in browser
2. Click "Start Paper Trading" button
3. Select strategy (Mixed recommended)
4. Monitor real-time performance

#### Via API
```bash
# Start mixed strategy trading
curl -X POST http://localhost:5000/paper-trading/start \
  -H "Content-Type: application/json" \
  -d '{"strategy": "mixed", "signal_interval": 2}'
```

### Monitoring Portfolio

#### Dashboard View
- Real-time charts with portfolio performance
- Position tracking with P&L calculations
- Trading KPIs: Sharpe ratio, drawdown, win rate
- Strategy performance breakdown

#### API Monitoring
```bash
# Check system health
curl http://localhost:5000/health

# Get portfolio status
curl http://localhost:5000/paper-trading/status

# Real-time chart data
curl http://localhost:5000/api/chart-data
```

## Directory Structure

```
AutomationBot/
├── simple_modular_main.py    # Application entry point
├── .env                      # Environment configuration
├── .env.template             # Configuration template
├── requirements.txt          # Python dependencies
├── api/                      # Web interface
│   └── simple_modular_routes.py
├── core/                     # Trading engine
│   ├── dynamic_portfolio_manager.py
│   ├── paper_trading_engine.py
│   └── security_manager.py
├── config/                   # JSON configuration files
│   ├── capital_config.json
│   └── platform_config.json
├── data/                     # SQLite database (auto-created)
└── logs/                     # Application logs (auto-created)
```

## Production Considerations

### Security
- **API Keys**: Never commit `.env` file to version control
- **Network**: Consider firewall rules for production deployment
- **Access**: Dashboard runs on localhost by default (secure for development)

### Performance
- **Caching**: 30-second market data caching improves performance
- **Database**: SQLite suitable for single-user development
- **Memory**: ~200MB typical memory usage

### Monitoring
- **Logs**: Check `./logs/simple_modular_bot.log` for application activity
- **Health**: Use `/health` endpoint for system monitoring
- **Database**: SQLite database created automatically in `./data/`

## Troubleshooting

### Common Issues

#### Port 5000 Already in Use
```bash
# Change port in .env file
echo "API_PORT=5001" >> .env
python simple_modular_main.py
```

#### API Key Authentication Errors
```bash
# Verify API key in health check
curl http://localhost:5000/health
# Look for "polygon_integration": {"status": "connected"}
```

#### Missing Dependencies
```bash
# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

#### Database Permission Issues
```bash
# Ensure data directory is writable
mkdir -p data
chmod 755 data
```

### Log Analysis

Application logs are stored in `./logs/simple_modular_bot.log`:

```bash
# View recent log entries
tail -f ./logs/simple_modular_bot.log

# Search for errors
grep -i error ./logs/simple_modular_bot.log

# Check system startup
grep -i "starting" ./logs/simple_modular_bot.log
```

### System Validation

#### Health Check Response
Expected `/health` endpoint response:
```json
{
  "status": "success",
  "data": {
    "system_status": "healthy",
    "capital_status": {
      "initial_capital": 500.00,
      "current_portfolio_value": 500.00
    },
    "components": {
      "polygon_integration": {
        "status": "connected"
      }
    }
  }
}
```

#### Dashboard Verification
- Page loads at `http://localhost:5000/`
- Shows $500.00 starting capital
- Real-time charts display correctly
- Trading controls are functional

## Advanced Configuration

### Custom Port Configuration
```bash
# Set custom port
echo "API_PORT=8080" >> .env
python simple_modular_main.py
# Access dashboard at http://localhost:8080/
```

### Logging Configuration
```bash
# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env
python simple_modular_main.py
```

### Strategy Parameters
Edit `config/platform_config.json` for advanced strategy customization:
```json
{
  "trading": {
    "signal_interval": 30,
    "max_positions": 8,
    "risk_per_trade": 0.02
  }
}
```

---

**Deployment Guide Version**: 3.0  
**Target Environment**: Local Development & Testing  
**Last Updated**: September 2025  
**Support**: Paper trading simulation with $500 capital