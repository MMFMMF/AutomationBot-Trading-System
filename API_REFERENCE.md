# AutomationBot Enhanced Trading Platform - API Reference

## Overview

The AutomationBot Enhanced API provides comprehensive RESTful access to the professional trading platform with **Enhanced Desktop Trading Viewer integration**, real-time portfolio data, advanced trading controls, and system monitoring. Features 5 specialized desktop viewer endpoints plus traditional web API.

**Base URL**: `http://localhost:5000`  
**Current Version**: 4.0 - Enhanced Professional Trading Platform  
**Capital Scale**: $500 paper trading platform  
**Desktop Integration**: Enhanced Comprehensive Trading Viewer

## Response Format

All API responses follow this standardized structure:

### Success Response
```json
{
  "status": "success",
  "timestamp": "2025-09-01T12:00:00Z",
  "data": {
    // Endpoint-specific response data
  },
  "metadata": {
    "version": "3.0",
    "execution_time_ms": 45
  }
}
```

### Error Response
```json
{
  "status": "error",
  "timestamp": "2025-09-01T12:00:00Z",
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "The 'symbol' parameter is required",
    "details": "Symbol must be a valid stock ticker"
  },
  "metadata": {
    "version": "3.0",
    "execution_time_ms": 12
  }
}
```

## 🚀 Enhanced Desktop Viewer API Endpoints

### **Enhanced Trading Viewer Integration**

The Enhanced Desktop Trading Viewer uses 5 specialized API endpoints for comprehensive real-time integration:

#### GET `/api/positions`
**Purpose**: Current position data for desktop viewer display  
**Integration**: Updates every 5 seconds in desktop viewer

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-09-06T10:30:00Z",
  "data": {
    "positions": [
      {
        "symbol": "AAPL",
        "quantity": 5.0,
        "current_price": 175.50,
        "market_value": 877.50,
        "cost_basis": 850.00,
        "unrealized_pnl": 27.50,
        "unrealized_pnl_percent": 3.24
      }
    ],
    "total_positions": 3,
    "total_market_value": 2456.78
  }
}
```

#### GET `/api/trades`
**Purpose**: Recent trade history for desktop display  
**Integration**: Trading activity feed in Enhanced Viewer

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-09-06T10:30:00Z",
  "data": {
    "recent_trades": [
      {
        "timestamp": "2025-09-06T09:15:00Z",
        "symbol": "MSFT",
        "side": "buy",
        "quantity": 2.5,
        "price": 380.25,
        "total_value": 950.63,
        "strategy": "ma_crossover"
      }
    ],
    "trade_count_today": 4,
    "total_volume_today": 3456.78
  }
}
```

#### GET `/api/capital`
**Purpose**: Capital allocation and utilization metrics  
**Integration**: Capital management dashboard tab

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-09-06T10:30:00Z",
  "data": {
    "total_capital": 500.00,
    "available_cash": 123.45,
    "invested_capital": 376.55,
    "capital_utilization_percent": 75.31,
    "daily_pnl": 15.67,
    "daily_pnl_percent": 3.13,
    "max_position_size": 50.00,
    "positions_count": 3,
    "max_positions": 8
  }
}
```

#### GET `/api/strategies`
**Purpose**: Available strategies and configurations  
**Integration**: Strategy management tab

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-09-06T10:30:00Z",
  "data": {
    "available_strategies": [
      "ma_crossover",
      "rsi_mean_reversion", 
      "momentum_breakout"
    ],
    "active_strategy": "ma_crossover",
    "strategy_profiles": [
      "Conservative",
      "Moderate", 
      "Aggressive",
      "Custom"
    ],
    "current_profile": "Moderate"
  }
}
```

#### GET `/api/signals`
**Purpose**: Recent trading signals and performance  
**Integration**: Signal monitoring in desktop viewer

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-09-06T10:30:00Z",
  "data": {
    "recent_signals": [
      {
        "timestamp": "2025-09-06T09:30:00Z",
        "symbol": "TSLA",
        "signal": "buy",
        "strength": 0.75,
        "strategy": "momentum_breakout",
        "executed": true
      }
    ],
    "signals_today": 6,
    "signals_executed": 4,
    "signals_blocked": 2,
    "success_rate_percent": 66.67
  }
}
```

---

## Core Web API Endpoints

### Dashboard Interface

#### GET `/`
Returns the professional trading dashboard HTML interface.

**Description**: Bloomberg-style dashboard with real-time charts, KPIs, and trading controls.

**Response**: HTML page (not JSON)

**Features**:
- Real-time Chart.js portfolio visualization
- Trading KPIs: Sharpe ratio, drawdown, win rate, profit factor
- Interactive trading controls and strategy selection
- 30-second auto-refresh with live market data

---

### System Health

#### GET `/health`
Comprehensive system health check with component status.

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-09-01T12:00:00Z",
  "data": {
    "system_status": "healthy",
    "version": "AutomationBot 3.0",
    "capital_status": {
      "initial_capital": 500.00,
      "current_portfolio_value": 500.00,
      "active_positions": 0
    },
    "components": {
      "dynamic_portfolio_manager": {
        "status": "operational",
        "portfolio_value": 500.00
      },
      "paper_trading_engine": {
        "status": "ready",
        "is_running": false,
        "total_trades": 0
      },
      "polygon_integration": {
        "status": "connected",
        "api_key_valid": true
      }
    },
    "database": {
      "type": "sqlite",
      "status": "connected"
    }
  }
}
```

---

### Real-time Portfolio Data

#### GET `/api/chart-data`
Real-time analytics data for dashboard charts and portfolio visualization.

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-09-01T12:00:00Z",
  "data": {
    "portfolio_summary": {
      "total_value": 500.00,
      "cash_balance": 500.00,
      "market_value": 0.00,
      "unrealized_pnl": 0.00,
      "realized_pnl": 0.00,
      "total_pnl": 0.00,
      "day_change": 0.00,
      "day_change_percent": 0.00
    },
    "portfolio_history": [
      {
        "time": "2025-09-01 12:00",
        "value": 500.00,
        "change_percent": 0.00
      }
    ],
    "positions_data": [],
    "strategy_performance": {
      "ma_crossover": {
        "pnl": 0.00,
        "trades": 0,
        "win_rate": 0.00,
        "sharpe_ratio": 0.00
      },
      "rsi_mean_reversion": {
        "pnl": 0.00,
        "trades": 0,
        "win_rate": 0.00,
        "sharpe_ratio": 0.00
      },
      "momentum_breakout": {
        "pnl": 0.00,
        "trades": 0,
        "win_rate": 0.00,
        "sharpe_ratio": 0.00
      }
    },
    "risk_metrics": {
      "sharpe_ratio": 0.00,
      "max_drawdown": 0.00,
      "portfolio_beta": 0.00,
      "var_1d": 0.00
    },
    "trading_summary": {
      "total_trades": 0,
      "win_rate": 0.00,
      "total_pnl": 0.00,
      "open_positions": 0,
      "available_capital": 500.00
    }
  }
}
```

## Paper Trading Management

### Start Trading Session

#### POST `/paper-trading/start`
Start a paper trading session with specified strategy and parameters.

**Request Body**:
```json
{
  "strategy": "mixed",
  "signal_interval": 2
}
```

**Parameters**:
- `strategy` (string, required): Strategy type
  - `mixed`: Combined multiple strategies
  - `ma_crossover`: Moving average crossover
  - `rsi_mean_reversion`: RSI-based signals
  - `momentum_breakout`: Momentum signals
- `signal_interval` (integer, optional): Signal generation interval in minutes (default: 2)

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-09-01T12:00:00Z",
  "data": {
    "trading_session": {
      "session_id": "session_20250901_120000",
      "status": "started",
      "strategy": "mixed",
      "capital": 500.00,
      "start_time": "2025-09-01T12:00:00Z"
    },
    "configuration": {
      "signal_interval": 2,
      "max_position_size": 50.00,
      "max_positions": 8,
      "fractional_shares": true
    },
    "risk_parameters": {
      "capital_scale": "micro_trading",
      "position_concentration": "10%",
      "diversification_target": "5-8_positions"
    }
  }
}
```

---

### Stop Trading Session

#### POST `/paper-trading/stop`
Stop the current paper trading session.

**Request Body**: None

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-09-01T12:05:00Z",
  "data": {
    "session_summary": {
      "session_id": "session_20250901_120000",
      "status": "stopped",
      "duration_minutes": 5,
      "stop_time": "2025-09-01T12:05:00Z",
      "final_statistics": {
        "total_trades": 3,
        "realized_pnl": 12.50,
        "unrealized_pnl": 5.75,
        "win_rate": 0.67,
        "final_capital": 518.25
      }
    }
  }
}
```

---

### Trading Status

#### GET `/paper-trading/status`
Get current paper trading session status and portfolio information.

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-09-01T12:00:00Z",
  "data": {
    "trading_status": {
      "is_running": false,
      "session_id": null,
      "ready_to_start": true
    },
    "portfolio": {
      "total_value": 500.00,
      "cash_balance": 500.00,
      "invested_amount": 0.00,
      "unrealized_pnl": 0.00,
      "realized_pnl": 0.00,
      "total_pnl": 0.00,
      "day_change": 0.00,
      "day_change_percent": 0.00
    },
    "positions": [],
    "performance_metrics": {
      "total_trades": 0,
      "winning_trades": 0,
      "losing_trades": 0,
      "win_rate": 0.00,
      "profit_factor": 0.00,
      "sharpe_ratio": 0.00,
      "max_drawdown": 0.00,
      "total_return_percent": 0.00
    },
    "system_capabilities": {
      "fractional_shares": true,
      "max_position_size": 50.00,
      "max_concurrent_positions": 8,
      "real_time_pricing": true
    }
  }
}
```

---

### Generate Test Signal

#### POST `/paper-trading/generate-signal`
Manually generate a trading signal for testing purposes.

**Request Body**:
```json
{
  "strategy": "test",
  "symbol": "AAPL",
  "side": "buy",
  "quantity": 10,
  "order_type": "market"
}
```

**Parameters**:
- `strategy` (string, required): Strategy identifier
- `symbol` (string, optional): Stock symbol to trade
- `side` (string, optional): Trade direction (`buy`, `sell`)
- `quantity` (number, optional): Number of shares
- `order_type` (string, optional): Order type (`market`, `limit`)

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-09-01T12:00:00Z",
  "data": {
    "signal": {
      "signal_id": "signal_20250901_120000_001",
      "symbol": "AAPL",
      "side": "buy",
      "quantity": 10,
      "order_type": "market",
      "price": 194.25,
      "strategy": "test",
      "timestamp": "2025-09-01T12:00:00Z",
      "status": "generated"
    },
    "execution_result": {
      "status": "executed",
      "execution_price": 194.30,
      "execution_time": "2025-09-01T12:00:01Z",
      "fees": 1.25,
      "net_amount": 1944.25
    },
    "risk_check": {
      "passed": true,
      "checks_performed": [
        "position_limits",
        "capital_requirements",
        "concentration_limits"
      ]
    }
  }
}
```

## Error Handling

### HTTP Status Codes
- **200 OK**: Request successful
- **400 Bad Request**: Invalid request parameters
- **403 Forbidden**: Request denied (risk limits exceeded)
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource conflict (trading already running)
- **500 Internal Server Error**: System error
- **503 Service Unavailable**: System temporarily unavailable

### Common Error Codes

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `INVALID_PARAMETER` | Required parameter missing | Check parameter format and requirements |
| `SYMBOL_NOT_FOUND` | Stock symbol not recognized | Verify symbol is valid and tradeable |
| `INSUFFICIENT_CAPITAL` | Not enough buying power | Reduce position size or wait for capital |
| `POSITION_LIMIT_EXCEEDED` | Position size exceeds limits | Reduce quantity to stay within limits |
| `MARKET_CLOSED` | Market not open for trading | Wait for market hours |
| `PROVIDER_UNAVAILABLE` | API provider not accessible | Check network and provider status |
| `TRADING_SUSPENDED` | Trading temporarily suspended | Check system status |

## Usage Examples

### Python Examples

#### Basic System Check
```python
import requests

# Check system health
response = requests.get('http://localhost:5000/health')
health_data = response.json()
print(f"System Status: {health_data['data']['system_status']}")
```

#### Start Paper Trading
```python
# Start mixed strategy trading
trading_request = {
    "strategy": "mixed",
    "signal_interval": 2
}

response = requests.post('http://localhost:5000/paper-trading/start', 
                        json=trading_request)
session_data = response.json()
print(f"Session ID: {session_data['data']['trading_session']['session_id']}")
```

#### Monitor Portfolio
```python
# Get current portfolio status
response = requests.get('http://localhost:5000/paper-trading/status')
portfolio = response.json()
print(f"Portfolio Value: ${portfolio['data']['portfolio']['total_value']}")
print(f"P&L: ${portfolio['data']['portfolio']['total_pnl']}")
```

### cURL Examples

#### Health Check
```bash
curl http://localhost:5000/health
```

#### Start Trading
```bash
curl -X POST http://localhost:5000/paper-trading/start \
  -H "Content-Type: application/json" \
  -d '{"strategy": "mixed", "signal_interval": 2}'
```

#### Get Portfolio Data
```bash
curl http://localhost:5000/api/chart-data
```

#### Generate Test Signal
```bash
curl -X POST http://localhost:5000/paper-trading/generate-signal \
  -H "Content-Type: application/json" \
  -d '{"strategy": "test", "symbol": "AAPL", "side": "buy", "quantity": 5}'
```

---

**API Version**: 3.0  
**Compatible with**: AutomationBot 3.0+  
**Last Updated**: September 2025  
**Support**: Paper trading simulation optimized for $500 capital