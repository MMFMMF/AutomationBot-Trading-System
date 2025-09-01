import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional

from .base_handler import BaseVenueHandler
from ..models import TradingSignal, SignalStatus, OrderType, OrderSide
from config import api_config, BLOCK_REASONS

logger = logging.getLogger(__name__)

class TradeStationHandler(BaseVenueHandler):
    """TradeStation API execution handler"""
    
    def __init__(self):
        super().__init__("TradeStation")
        self.base_url = "https://sim-api.tradestation.com/v3"  # Simulation URL
        self.access_token = None
        self.account_id = None
        self.session = requests.Session()
        
        # Initialize connection
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with TradeStation API"""
        try:
            if not api_config.tradestation_client_id or not api_config.tradestation_client_secret:
                logger.error("TradeStation credentials not configured")
                return False
            
            # OAuth2 authentication flow
            auth_url = "https://signin.tradestation.com/oauth/token"
            auth_data = {
                'grant_type': 'client_credentials',
                'client_id': api_config.tradestation_client_id,
                'client_secret': api_config.tradestation_client_secret,
                'scope': 'MarketData ReadAccount Trade Crypto'
            }
            
            response = self.session.post(auth_url, data=auth_data)
            
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
            logger.error(f"TradeStation authentication error: {str(e)}")
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
            logger.error(f"Error getting account info: {str(e)}")
    
    def execute_trade(self, signal: TradingSignal) -> TradingSignal:
        """Execute trade through TradeStation API"""
        try:
            if not self._update_connection_status():
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = BLOCK_REASONS['VENUE_UNAVAILABLE']
                return signal
            
            # Prepare order data
            order_data = self._prepare_order(signal)
            if not order_data:
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = BLOCK_REASONS['API_ERROR']
                return signal
            
            # Submit order
            order_url = f"{self.base_url}/brokerage/accounts/{self.account_id}/orders"
            response = self.session.post(order_url, json=order_data)
            
            if response.status_code in [200, 201]:
                order_response = response.json()
                signal.status = SignalStatus.EXECUTED
                signal.execution_price = signal.price  # Use order price for now
                signal.execution_time = datetime.now()
                signal.metadata.update({
                    'venue': 'tradestation',
                    'order_id': order_response.get('OrderID'),
                    'order_status': order_response.get('Status')
                })
                
                logger.info(f"TradeStation order executed: {order_response.get('OrderID')}")
                return signal
            else:
                error_msg = response.json().get('Message', 'Unknown error')
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = f"TradeStation API error: {error_msg}"
                logger.error(f"TradeStation order failed: {error_msg}")
                return signal
                
        except Exception as e:
            logger.error(f"TradeStation execution error: {str(e)}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = BLOCK_REASONS['API_ERROR']
            return signal
    
    def _prepare_order(self, signal: TradingSignal) -> Optional[Dict[str, Any]]:
        """Prepare order data for TradeStation API"""
        try:
            order_data = {
                'AccountID': self.account_id,
                'Symbol': signal.symbol,
                'Quantity': str(int(signal.quantity)),
                'OrderType': self._map_order_type(signal.order_type),
                'TradeAction': self._map_order_side(signal.side),
                'TimeInForce': 'DAY',
                'Route': 'Intelligent'
            }
            
            # Add price for limit orders
            if signal.order_type == OrderType.LIMIT and signal.price:
                order_data['LimitPrice'] = str(signal.price)
            
            # Add stop price for stop orders
            if signal.order_type == OrderType.STOP and signal.stop_price:
                order_data['StopPrice'] = str(signal.stop_price)
            
            return order_data
            
        except Exception as e:
            logger.error(f"Error preparing order data: {str(e)}")
            return None
    
    def _map_order_type(self, order_type: OrderType) -> str:
        """Map internal order type to TradeStation format"""
        mapping = {
            OrderType.MARKET: 'Market',
            OrderType.LIMIT: 'Limit',
            OrderType.STOP: 'StopMarket'
        }
        return mapping.get(order_type, 'Market')
    
    def _map_order_side(self, order_side: OrderSide) -> str:
        """Map internal order side to TradeStation format"""
        mapping = {
            OrderSide.BUY: 'BUY',
            OrderSide.SELL: 'SELL'
        }
        return mapping.get(order_side, 'BUY')
    
    def get_account_status(self) -> Dict[str, Any]:
        """Get TradeStation account status"""
        try:
            if not self.account_id:
                return {'error': 'No account ID available'}
            
            response = self.session.get(f"{self.base_url}/brokerage/accounts/{self.account_id}/balances")
            
            if response.status_code == 200:
                balance_data = response.json()
                return {
                    'account_id': self.account_id,
                    'total_equity': balance_data.get('Equity', 0),
                    'available_cash': balance_data.get('CashBalance', 0),
                    'buying_power': balance_data.get('DayTradingBuyingPower', 0),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'error': f'API error: {response.status_code}'}
                
        except Exception as e:
            logger.error(f"Error getting account status: {str(e)}")
            return {'error': str(e)}
    
    def check_connection(self) -> bool:
        """Check TradeStation API connection"""
        try:
            if not self.access_token:
                return self._authenticate()
            
            # Test connection with a simple API call
            response = self.session.get(f"{self.base_url}/brokerage/accounts")
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"TradeStation connection check failed: {str(e)}")
            return False