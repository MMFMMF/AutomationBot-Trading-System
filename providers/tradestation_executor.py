import requests
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from .base_providers import (
    ExecutionProvider, ExecutionResult, ProviderHealthCheck, ProviderStatus
)
from core.execution_mode_manager import ExecutionModeManager

logger = logging.getLogger(__name__)

class TradeStationExecutor(ExecutionProvider):
    """TradeStation execution provider with placeholder credential system"""
    
    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any], execution_mode_manager: Optional[ExecutionModeManager] = None):
        self.config = config
        self.credentials = credentials
        self.access_token = None
        self.account_id = None
        self.session = requests.Session()
        self._last_health_check = None
        
        # Execution mode management
        self.execution_mode_manager = execution_mode_manager or ExecutionModeManager()
        
        # Credential status tracking
        self.credential_status = self._check_credential_status()
        
        # Set up base URLs based on environment
        environment = config.get("environment", "simulation")
        if environment == "production":
            self.base_url = "https://api.tradestation.com/v3"
            self.auth_url = "https://signin.tradestation.com/oauth/token"
        else:
            self.base_url = "https://sim-api.tradestation.com/v3"
            self.auth_url = "https://signin.tradestation.com/oauth/token"
        
        # Simulated account data for placeholder mode
        self.simulated_balance = 16000.0
        self.simulated_positions = {}
        
        # Initialize connection based on credential status
        self._initialize_connection()
        
        # Log initialization status
        status_msg = self._get_status_message()
        logger.info(f"TradeStation executor initialized: {status_msg}")
    
    @property
    def provider_name(self) -> str:
        return "tradestation"
    
    def _check_credential_status(self) -> str:
        """Check the status of TradeStation credentials"""
        client_id = self.credentials.get("client_id")
        client_secret = self.credentials.get("client_secret")
        
        # Check for placeholder values or missing credentials
        if not client_id or not client_secret:
            return "MISSING_CREDENTIALS"
        
        if client_id.startswith("${TRADESTATION") or client_secret.startswith("${TRADESTATION"):
            return "AWAITING_CREDENTIALS"
        
        if client_id == "your_client_id_here" or client_secret == "your_client_secret_here":
            return "PLACEHOLDER_VALUES"
        
        return "CREDENTIALS_PROVIDED"
    
    def _get_status_message(self) -> str:
        """Get human-readable status message"""
        status_map = {
            "MISSING_CREDENTIALS": "No credentials configured - API access disabled",
            "AWAITING_CREDENTIALS": "Environment variables not set - waiting for credentials", 
            "PLACEHOLDER_VALUES": "Placeholder credentials detected - replace with real values",
            "CREDENTIALS_PROVIDED": "Real credentials provided - API access enabled"
        }
        return status_map.get(self.credential_status, "Unknown credential status")
    
    def _initialize_connection(self):
        """Initialize connection based on credential status"""
        if self.credential_status == "CREDENTIALS_PROVIDED":
            self._authenticate()
        else:
            logger.warning(f"TradeStation authentication skipped: {self._get_status_message()}")
    
    def _authenticate(self):
        """Authenticate with TradeStation API"""
        try:
            client_id = self.credentials.get("client_id")
            client_secret = self.credentials.get("client_secret")
            
            if self.credential_status != "CREDENTIALS_PROVIDED":
                logger.error(f"Cannot authenticate: {self._get_status_message()}")
                return False
            
            # OAuth2 authentication flow
            auth_data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': 'MarketData ReadAccount Trade Crypto'
            }
            
            response = self.session.post(self.auth_url, data=auth_data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                })
                
                # Get account info
                self._get_account_info()
                logger.info("TradeStation authentication successful")
                return True
            else:
                logger.error(f"TradeStation authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"TradeStation authentication error: {e}")
            return False
    
    def _get_account_info(self):
        """Get account information"""
        try:
            response = self.session.get(f"{self.base_url}/brokerage/accounts")
            if response.status_code == 200:
                accounts = response.json()
                if accounts and len(accounts) > 0:
                    self.account_id = accounts[0]['AccountID']
                    logger.info(f"Using TradeStation account: {self.account_id}")
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
    
    def execute_market_order(self, symbol: str, side: str, quantity: float) -> ExecutionResult:
        """Execute market order"""
        return self._execute_order(symbol, side, quantity, "Market")
    
    def execute_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> ExecutionResult:
        """Execute limit order"""
        return self._execute_order(symbol, side, quantity, "Limit", price=price)
    
    def execute_stop_order(self, symbol: str, side: str, quantity: float, stop_price: float) -> ExecutionResult:
        """Execute stop order"""
        return self._execute_order(symbol, side, quantity, "StopMarket", stop_price=stop_price)
    
    def _execute_order(self, symbol: str, side: str, quantity: float, order_type: str, 
                      price: Optional[float] = None, stop_price: Optional[float] = None) -> ExecutionResult:
        """Internal method to execute orders"""
        try:
            if not self.access_token or not self.account_id:
                return ExecutionResult(
                    success=False,
                    error_message="TradeStation not authenticated"
                )
            
            # Prepare order data
            order_data = {
                'AccountID': self.account_id,
                'Symbol': symbol.upper(),
                'Quantity': str(int(quantity)),
                'OrderType': order_type,
                'TradeAction': side.upper(),
                'TimeInForce': 'DAY',
                'Route': 'Intelligent'
            }
            
            # Add price for limit orders
            if order_type == 'Limit' and price:
                order_data['LimitPrice'] = str(price)
            
            # Add stop price for stop orders
            if order_type == 'StopMarket' and stop_price:
                order_data['StopPrice'] = str(stop_price)
            
            # Submit order
            order_url = f"{self.base_url}/brokerage/accounts/{self.account_id}/orders"
            response = self.session.post(order_url, json=order_data)
            
            if response.status_code in [200, 201]:
                order_response = response.json()
                
                return ExecutionResult(
                    success=True,
                    order_id=order_response.get('OrderID'),
                    execution_price=price if order_type == 'Market' else price,  # Will be updated with actual fill
                    executed_quantity=quantity,
                    execution_time=datetime.now(timezone.utc),
                    metadata={
                        "provider": self.provider_name,
                        "order_status": order_response.get('Status'),
                        "route": "Intelligent",
                        "time_in_force": "DAY"
                    }
                )
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('Message', f'HTTP {response.status_code}')
                
                return ExecutionResult(
                    success=False,
                    error_message=f"TradeStation API error: {error_msg}",
                    metadata={
                        "provider": self.provider_name,
                        "http_status": response.status_code,
                        "response": error_data
                    }
                )
                
        except Exception as e:
            logger.error(f"TradeStation execution error: {e}")
            return ExecutionResult(
                success=False,
                error_message=f"Execution error: {str(e)}"
            )
    
    def _simulate_order_execution(self, symbol: str, side: str, quantity: float, order_type: str,
                                 price: Optional[float] = None, stop_price: Optional[float] = None) -> ExecutionResult:
        """Simulate order execution with realistic behavior"""
        try:
            # Simulate market price (would normally come from price provider)
            simulated_price = price if price else 100.0  # Default estimate
            
            # Apply realistic slippage for market orders
            if order_type == "Market":
                slippage = 0.001  # 0.1% slippage
                if side.upper() == "BUY":
                    simulated_price *= (1 + slippage)
                else:
                    simulated_price *= (1 - slippage)
            
            # Generate simulated order ID
            simulated_order_id = f"SIM_TS_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Update simulated balance
            position_value = quantity * simulated_price
            if side.upper() == "BUY":
                if position_value > self.simulated_balance:
                    return ExecutionResult(
                        success=False,
                        error_message=f"Insufficient simulated balance: ${self.simulated_balance:.2f} < ${position_value:.2f}"
                    )
                self.simulated_balance -= position_value
            else:  # SELL
                self.simulated_balance += position_value
            
            # Track simulated positions
            if symbol not in self.simulated_positions:
                self.simulated_positions[symbol] = 0
            
            if side.upper() == "BUY":
                self.simulated_positions[symbol] += quantity
            else:
                self.simulated_positions[symbol] -= quantity
            
            logger.info(f"TradeStation simulation: {order_type} {side} {quantity} {symbol} @ ${simulated_price:.4f}")
            
            return ExecutionResult(
                success=True,
                order_id=simulated_order_id,
                execution_price=simulated_price,
                executed_quantity=quantity,
                execution_time=datetime.now(timezone.utc),
                metadata={
                    "provider": self.provider_name,
                    "simulation": True,
                    "order_type": order_type,
                    "credential_status": self.credential_status,
                    "simulated_balance_after": self.simulated_balance,
                    "route": "Simulated_Intelligent"
                }
            )
            
        except Exception as e:
            logger.error(f"TradeStation simulation error: {e}")
            return ExecutionResult(
                success=False,
                error_message=f"Simulation error: {str(e)}"
            )
    
    def get_account_balance(self) -> Optional[float]:
        """Get available account balance with placeholder support"""
        try:
            # Add realistic delay
            self.execution_mode_manager.simulate_api_delay('balance_check')
            
            # Handle credential status
            if self.credential_status != "CREDENTIALS_PROVIDED":
                logger.info(f"Returning simulated balance - {self._get_status_message()}")
                return self.simulated_balance
            
            # Real API call if authenticated
            if not self.account_id:
                logger.warning("No account ID available, returning simulated balance")
                return self.simulated_balance
            
            response = self.session.get(f"{self.base_url}/brokerage/accounts/{self.account_id}/balances")
            
            if response.status_code == 200:
                balance_data = response.json()
                return float(balance_data.get('CashBalance', 0))
            else:
                logger.error(f"Failed to get account balance: {response.status_code}, using simulated")
                return self.simulated_balance
                
        except Exception as e:
            logger.error(f"Error getting account balance: {e}, using simulated")
            return self.simulated_balance
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        try:
            if not self.account_id:
                return []
            
            response = self.session.get(f"{self.base_url}/brokerage/accounts/{self.account_id}/positions")
            
            if response.status_code == 200:
                positions_data = response.json()
                
                normalized_positions = []
                for pos in positions_data:
                    normalized_positions.append({
                        "symbol": pos.get("Symbol"),
                        "quantity": float(pos.get("Quantity", 0)),
                        "market_value": float(pos.get("MarketValue", 0)),
                        "average_price": float(pos.get("AveragePrice", 0)),
                        "unrealized_pnl": float(pos.get("UnrealizedProfitLoss", 0)),
                        "provider": self.provider_name
                    })
                
                return normalized_positions
            else:
                logger.error(f"Failed to get positions: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            if not self.account_id:
                return False
            
            cancel_url = f"{self.base_url}/brokerage/accounts/{self.account_id}/orders/{order_id}"
            response = self.session.delete(cancel_url)
            
            success = response.status_code in [200, 204]
            if success:
                logger.info(f"Order {order_id} cancelled successfully")
            else:
                logger.error(f"Failed to cancel order {order_id}: {response.status_code}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def health_check(self) -> ProviderHealthCheck:
        """Check provider health and connectivity"""
        start_time = datetime.now()
        
        try:
            # Check execution mode and environment settings
            is_execution_mode = self.execution_mode_manager.is_execution_mode()
            environment = self.config.get("environment", "simulation")
            logger.info(f"TradeStation health check - Execution mode: {is_execution_mode}, Environment: {environment}")
            
            # In simulation mode, always return healthy status
            if not is_execution_mode or environment == "simulation":
                result = ProviderHealthCheck(
                    provider_name=self.provider_name,
                    status=ProviderStatus.CONNECTED,
                    last_check=start_time,
                    error_message="Simulation mode - no authentication required",
                    metadata={
                        "mode": "simulation",
                        "environment": environment,
                        "authenticated": False,
                        "simulation_ready": True,
                        "execution_mode_checked": is_execution_mode
                    }
                )
                logger.info(f"TradeStation health check returning CONNECTED status: {result.status.value}")
                return result
            
            if not self.access_token:
                return ProviderHealthCheck(
                    provider_name=self.provider_name,
                    status=ProviderStatus.ERROR,
                    last_check=start_time,
                    error_message="Not authenticated"
                )
            
            # Test connection with accounts endpoint
            response = self.session.get(f"{self.base_url}/brokerage/accounts")
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                self._last_health_check = ProviderHealthCheck(
                    provider_name=self.provider_name,
                    status=ProviderStatus.CONNECTED,
                    last_check=end_time,
                    response_time_ms=response_time,
                    metadata={
                        "account_id": self.account_id,
                        "environment": self.config.get("environment", "simulation"),
                        "authenticated": True
                    }
                )
            else:
                self._last_health_check = ProviderHealthCheck(
                    provider_name=self.provider_name,
                    status=ProviderStatus.ERROR,
                    last_check=end_time,
                    response_time_ms=response_time,
                    error_message=f"HTTP {response.status_code}"
                )
            
            return self._last_health_check
            
        except Exception as e:
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            self._last_health_check = ProviderHealthCheck(
                provider_name=self.provider_name,
                status=ProviderStatus.ERROR,
                last_check=end_time,
                response_time_ms=response_time,
                error_message=str(e)
            )
            
            return self._last_health_check