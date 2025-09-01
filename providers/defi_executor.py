import logging
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import json

from providers.base_providers import (
    ExecutionProvider, ExecutionResult, ProviderHealthCheck, ProviderStatus
)
from core.execution_mode_manager import ExecutionModeManager

logger = logging.getLogger(__name__)

class DeFiExecutor(ExecutionProvider):
    """Real DeFi execution provider using DEX aggregator APIs"""
    
    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any], execution_mode_manager: Optional[ExecutionModeManager] = None):
        self.config = config
        self.credentials = credentials
        self._last_health_check = None
        
        # Execution mode management
        self.execution_mode_manager = execution_mode_manager or ExecutionModeManager()
        
        # DeFi configuration
        self.wallet_address = credentials.get("wallet_address", "0x742d35Cc6635C0532925a3b8D716C7E5532")  # Demo wallet
        self.private_key = credentials.get("private_key")  # Would be encrypted in production
        
        # 1inch API for DEX aggregation (free tier available)
        self.oneinch_base_url = "https://api.1inch.io/v5.0/1"  # Ethereum mainnet
        self.session = requests.Session()
        
        # Balance for simulation
        self.simulated_balance = 16000  # USDC equivalent
        
        # Check execution mode
        is_execution, reason = self.execution_mode_manager.get_provider_mode('defi')
        mode_str = "EXECUTION" if is_execution else "SIMULATION"
        logger.info(f"DeFi executor initialized in {mode_str} mode ({reason})")
    
    @property
    def provider_name(self) -> str:
        return "defi"
    
    def execute_market_order(self, symbol: str, side: str, quantity: float) -> ExecutionResult:
        """Execute market order via DEX aggregation"""
        try:
            # Check execution mode and safety
            is_execution_mode, mode_reason = self.execution_mode_manager.get_provider_mode('defi')
            position_value = quantity * 100  # Estimate for safety check
            is_safe, safety_reason = self.execution_mode_manager.validate_execution_safety('defi', 'market_order', position_value)
            
            # Log the action
            self.execution_mode_manager.log_action('defi', 'market_order', {
                'symbol': symbol,
                'side': side, 
                'quantity': quantity,
                'estimated_value': position_value
            })
            
            # Add realistic delay
            self.execution_mode_manager.simulate_api_delay('order_execution')
            
            # Convert traditional symbol to token address
            token_info = self._get_token_info(symbol)
            if not token_info:
                return ExecutionResult(
                    success=False,
                    error_message=f"Token {symbol} not supported on DeFi"
                )
            
            # Get quote from 1inch aggregator
            quote = self._get_dex_quote(token_info, side, quantity)
            if not quote:
                return ExecutionResult(
                    success=False,
                    error_message="Unable to get DEX quote"
                )
            
            # Execute based on mode
            if is_execution_mode and is_safe:
                logger.warning(f"REAL DeFi execution for {symbol} - This would execute on blockchain!")
                return self._execute_real_swap(token_info, side, quantity, quote)
            else:
                # Always simulate if not safe or in simulation mode
                reason = safety_reason if not is_safe else mode_reason
                logger.info(f"Simulating DeFi execution for {symbol} - {reason}")
                return self._simulate_swap_execution(symbol, side, quantity, quote)
                
        except Exception as e:
            logger.error(f"DeFi execution error: {e}")
            return ExecutionResult(
                success=False,
                error_message=f"DeFi execution failed: {str(e)}"
            )
    
    def execute_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> ExecutionResult:
        """Execute limit order (DeFi doesn't typically support limits, use market)"""
        logger.warning("DeFi limit orders not supported, executing as market order")
        return self.execute_market_order(symbol, side, quantity)
    
    def execute_stop_order(self, symbol: str, side: str, quantity: float, stop_price: float) -> ExecutionResult:
        """Execute stop order (not supported in basic DeFi)"""
        return ExecutionResult(
            success=False,
            error_message="Stop orders not supported in DeFi mode"
        )
    
    def _get_token_info(self, symbol: str) -> Optional[Dict]:
        """Get token contract address and info"""
        # Common token mappings
        token_map = {
            'ETH': {
                'address': '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE',  # ETH special address
                'decimals': 18,
                'name': 'Ethereum'
            },
            'USDC': {
                'address': '0xA0b86a33E6A2B2c9Ba92C0d55B2a6dc9F8FE4c7f',  # USDC on Ethereum
                'decimals': 6,
                'name': 'USD Coin'
            },
            'USDT': {
                'address': '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT on Ethereum
                'decimals': 6,
                'name': 'Tether'
            },
            'BTC': {
                'address': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',  # WBTC on Ethereum
                'decimals': 8,
                'name': 'Wrapped Bitcoin'
            }
        }
        
        return token_map.get(symbol.upper())
    
    def _get_dex_quote(self, token_info: Dict, side: str, quantity: float) -> Optional[Dict]:
        """Get quote from 1inch DEX aggregator"""
        try:
            # For demo purposes, simulate a quote
            if self.simulation_mode:
                base_price = 100.0  # Mock price
                if token_info['name'] == 'Ethereum':
                    base_price = 2500.0
                elif token_info['name'] == 'Wrapped Bitcoin':
                    base_price = 45000.0
                
                return {
                    'price': base_price,
                    'amount_out': quantity * base_price if side == 'sell' else quantity / base_price,
                    'gas_estimate': 150000,
                    'slippage': 0.5  # 0.5%
                }
            
            # Real 1inch API call (would need API key for production)
            usdc_address = "0xA0b86a33E6A2B2c9Ba92C0d55B2a6dc9F8FE4c7f"
            token_address = token_info['address']
            
            if side == 'buy':
                from_token = usdc_address
                to_token = token_address
                amount = int(quantity * (10 ** 6))  # USDC amount
            else:
                from_token = token_address
                to_token = usdc_address
                amount = int(quantity * (10 ** token_info['decimals']))
            
            url = f"{self.oneinch_base_url}/quote"
            params = {
                'fromTokenAddress': from_token,
                'toTokenAddress': to_token,
                'amount': str(amount)
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"1inch API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting DEX quote: {e}")
            return None
    
    def _simulate_swap_execution(self, symbol: str, side: str, quantity: float, quote: Dict) -> ExecutionResult:
        """Simulate DeFi swap execution"""
        try:
            execution_price = quote['price']
            slippage = quote.get('slippage', 0.5) / 100  # Convert to decimal
            
            # Apply slippage
            if side == 'buy':
                actual_price = execution_price * (1 + slippage)
            else:
                actual_price = execution_price * (1 - slippage)
            
            # Simulate gas cost
            gas_cost_usd = 0.02 * quote.get('gas_estimate', 150000) / 150000  # ~$0.02 per 150k gas
            
            # Generate transaction hash simulation
            tx_hash = f"0x{hash(f'{symbol}{side}{quantity}{datetime.now()}') % (16**64):064x}"
            
            # Update simulated balance
            if side == 'buy':
                cost = quantity * actual_price + gas_cost_usd
                if cost > self.simulated_balance:
                    return ExecutionResult(
                        success=False,
                        error_message=f"Insufficient balance. Need ${cost:.2f}, have ${self.simulated_balance:.2f}"
                    )
                self.simulated_balance -= cost
            else:
                revenue = quantity * actual_price - gas_cost_usd
                self.simulated_balance += revenue
            
            logger.info(f"DeFi swap executed: {quantity} {symbol} @ ${actual_price:.4f} (gas: ${gas_cost_usd:.4f})")
            
            return ExecutionResult(
                success=True,
                order_id=tx_hash,
                execution_price=actual_price,
                executed_quantity=quantity,
                execution_time=datetime.now(timezone.utc),
                metadata={
                    "provider": self.provider_name,
                    "tx_hash": tx_hash,
                    "gas_used": quote.get('gas_estimate', 150000),
                    "gas_cost_usd": gas_cost_usd,
                    "slippage_applied": f"{slippage * 100:.2f}%",
                    "dex_route": "Uniswap V3 -> 1inch",
                    "simulation": True
                }
            )
            
        except Exception as e:
            logger.error(f"Simulation execution error: {e}")
            return ExecutionResult(
                success=False,
                error_message=f"Simulation failed: {str(e)}"
            )
    
    def _execute_real_swap(self, token_info: Dict, side: str, quantity: float, quote: Dict) -> ExecutionResult:
        """Execute real DeFi swap (requires web3.py and wallet setup)"""
        # This would be the real Web3 implementation
        # For now, return error since we don't have wallet setup
        return ExecutionResult(
            success=False,
            error_message="Real DeFi execution requires wallet setup and web3 configuration"
        )
    
    def get_account_balance(self) -> Optional[float]:
        """Get wallet balance (simulated)"""
        if self.simulation_mode:
            return self.simulated_balance
        
        # Real implementation would query wallet balance via web3
        try:
            # Would use web3.eth.get_balance() for ETH
            # And token contract calls for ERC20 balances
            return None  # Not implemented for real mode
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return None
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current token positions"""
        if self.simulation_mode:
            return [
                {
                    "symbol": "USDC",
                    "quantity": self.simulated_balance,
                    "market_value": self.simulated_balance,
                    "average_price": 1.0,
                    "unrealized_pnl": 0.0,
                    "provider": self.provider_name
                }
            ]
        
        # Real implementation would query all token balances
        return []
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order (not applicable to DeFi swaps)"""
        logger.warning("DeFi swaps cannot be cancelled once submitted")
        return False
    
    def health_check(self) -> ProviderHealthCheck:
        """Check DeFi provider health"""
        start_time = datetime.now()
        
        try:
            # Test 1inch API connectivity
            response = self.session.get(f"{self.oneinch_base_url}/healthcheck", timeout=10)
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                status = ProviderStatus.CONNECTED
                error_message = None
            else:
                status = ProviderStatus.ERROR
                error_message = f"1inch API returned {response.status_code}"
            
            self._last_health_check = ProviderHealthCheck(
                provider_name=self.provider_name,
                status=status,
                last_check=end_time,
                response_time_ms=response_time,
                error_message=error_message,
                metadata={
                    "wallet_address": self.wallet_address,
                    "simulation_mode": self.simulation_mode,
                    "balance": self.get_account_balance(),
                    "dex_aggregator": "1inch"
                }
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