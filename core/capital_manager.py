import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class CapitalManager:
    """Manages capital allocation and dynamic position sizing"""
    
    def __init__(self, config_path: str = "./config/capital_config.json"):
        self.config_path = Path(config_path)
        self.capital_config = {}
        self.is_initialized = False
        self._load_capital_config()
    
    def _load_capital_config(self):
        """Load capital configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.capital_config = json.load(f)
                self.is_initialized = self.capital_config.get('initialized', False)
                logger.info(f"Capital configuration loaded. Initialized: {self.is_initialized}")
            else:
                logger.warning("Capital configuration file not found. Creating default.")
                self._create_default_config()
        except Exception as e:
            logger.error(f"Error loading capital configuration: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default capital configuration"""
        self.capital_config = {
            "total_capital": None,
            "allocation_percentages": {
                "max_position_pct": 10.0,
                "max_daily_loss_pct": 5.0,
                "emergency_reserve_pct": 20.0,
                "available_trading_pct": 80.0
            },
            "min_capital_threshold": 1000.0,
            "currency": "USD",
            "last_updated": None,
            "initialized": False
        }
        self._save_capital_config()
    
    def _save_capital_config(self):
        """Save capital configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.capital_config, f, indent=2)
            logger.info("Capital configuration saved")
        except Exception as e:
            logger.error(f"Error saving capital configuration: {e}")
    
    def initialize_capital(self, total_capital: float) -> bool:
        """Initialize the system with total capital amount"""
        try:
            if total_capital <= 0:
                raise ValueError("Capital must be positive")
            
            min_threshold = self.capital_config.get('min_capital_threshold', 1000.0)
            if total_capital < min_threshold:
                raise ValueError(f"Capital must be at least ${min_threshold:,.2f}")
            
            self.capital_config['total_capital'] = total_capital
            self.capital_config['last_updated'] = datetime.now().isoformat()
            self.capital_config['initialized'] = True
            self.is_initialized = True
            
            self._save_capital_config()
            
            logger.info(f"Capital initialized: ${total_capital:,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing capital: {e}")
            return False
    
    def update_capital(self, new_capital: float) -> bool:
        """Update total capital amount"""
        if not self.is_initialized:
            return self.initialize_capital(new_capital)
        
        try:
            old_capital = self.capital_config.get('total_capital', 0)
            if new_capital <= 0:
                raise ValueError("Capital must be positive")
            
            self.capital_config['total_capital'] = new_capital
            self.capital_config['last_updated'] = datetime.now().isoformat()
            self._save_capital_config()
            
            logger.info(f"Capital updated: ${old_capital:,.2f} -> ${new_capital:,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating capital: {e}")
            return False
    
    def get_total_capital(self) -> Optional[float]:
        """Get total capital amount"""
        return self.capital_config.get('total_capital')
    
    def get_available_capital(self) -> Optional[float]:
        """Get available capital for trading (excluding reserves)"""
        total = self.get_total_capital()
        if total is None:
            return None
        
        available_pct = self.capital_config['allocation_percentages']['available_trading_pct']
        return total * (available_pct / 100.0)
    
    def get_max_position_size(self) -> Optional[float]:
        """Get maximum position size in dollars"""
        available = self.get_available_capital()
        if available is None:
            return None
        
        max_position_pct = self.capital_config['allocation_percentages']['max_position_pct']
        return available * (max_position_pct / 100.0)
    
    def get_max_daily_loss(self) -> Optional[float]:
        """Get maximum daily loss amount in dollars"""
        total = self.get_total_capital()
        if total is None:
            return None
        
        max_daily_loss_pct = self.capital_config['allocation_percentages']['max_daily_loss_pct']
        return total * (max_daily_loss_pct / 100.0)
    
    def calculate_position_size(self, symbol: str, price: float, risk_pct: Optional[float] = None) -> Tuple[float, Dict[str, Any]]:
        """Calculate appropriate position size for a trade"""
        max_position = self.get_max_position_size()
        if max_position is None:
            raise ValueError("Capital not initialized. Please set total capital first.")
        
        # Use provided risk percentage or default
        if risk_pct is None:
            risk_pct = self.capital_config['allocation_percentages']['max_position_pct']
        
        # Calculate quantity based on price and max position size
        max_quantity = max_position / price
        
        calculation_details = {
            'total_capital': self.get_total_capital(),
            'available_capital': self.get_available_capital(),
            'max_position_usd': max_position,
            'symbol_price': price,
            'max_quantity': max_quantity,
            'risk_percentage': risk_pct
        }
        
        return max_quantity, calculation_details
    
    def validate_trade(self, symbol: str, quantity: float, price: float) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate if a trade fits within capital allocation rules"""
        try:
            max_position = self.get_max_position_size()
            if max_position is None:
                return False, "Capital not initialized", {}
            
            position_value = quantity * price
            
            # Check position size limit
            if position_value > max_position:
                return False, f"Position size ${position_value:,.2f} exceeds max allowed ${max_position:,.2f}", {
                    'position_value': position_value,
                    'max_position': max_position,
                    'excess_amount': position_value - max_position
                }
            
            # Check available capital
            available = self.get_available_capital()
            if position_value > available:
                return False, f"Position size ${position_value:,.2f} exceeds available capital ${available:,.2f}", {
                    'position_value': position_value,
                    'available_capital': available
                }
            
            return True, "Trade approved", {
                'position_value': position_value,
                'max_position': max_position,
                'available_capital': available,
                'utilization_pct': (position_value / max_position) * 100
            }
            
        except Exception as e:
            return False, f"Validation error: {str(e)}", {}
    
    def get_allocation_summary(self) -> Dict[str, Any]:
        """Get comprehensive capital allocation summary"""
        total = self.get_total_capital()
        if total is None:
            return {"error": "Capital not initialized"}
        
        allocation = self.capital_config['allocation_percentages']
        
        return {
            'total_capital': total,
            'available_trading': self.get_available_capital(),
            'emergency_reserve': total * (allocation['emergency_reserve_pct'] / 100.0),
            'max_position_size': self.get_max_position_size(),
            'max_daily_loss': self.get_max_daily_loss(),
            'allocation_percentages': allocation,
            'currency': self.capital_config.get('currency', 'USD'),
            'last_updated': self.capital_config.get('last_updated'),
            'initialized': self.is_initialized
        }
    
    def update_allocation_percentages(self, new_percentages: Dict[str, float]) -> bool:
        """Update allocation percentages with validation"""
        try:
            # Validate percentages
            required_keys = ['max_position_pct', 'max_daily_loss_pct', 'emergency_reserve_pct', 'available_trading_pct']
            for key in required_keys:
                if key not in new_percentages:
                    raise ValueError(f"Missing required percentage: {key}")
                
                if new_percentages[key] < 0 or new_percentages[key] > 100:
                    raise ValueError(f"Percentage {key} must be between 0 and 100")
            
            # Validate that reserve + trading = 100%
            total_allocation = new_percentages['emergency_reserve_pct'] + new_percentages['available_trading_pct']
            if abs(total_allocation - 100.0) > 0.01:  # Allow small floating point differences
                raise ValueError(f"Emergency reserve and trading percentages must sum to 100%, got {total_allocation}%")
            
            # Update configuration
            self.capital_config['allocation_percentages'].update(new_percentages)
            self.capital_config['last_updated'] = datetime.now().isoformat()
            self._save_capital_config()
            
            logger.info("Allocation percentages updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating allocation percentages: {e}")
            return False
    
    def prompt_for_capital_input(self) -> bool:
        """Prompt user for capital input (for CLI usage)"""
        if self.is_initialized:
            current_capital = self.get_total_capital()
            print(f"Current capital: ${current_capital:,.2f}")
            response = input("Do you want to update the capital amount? (y/n): ")
            if response.lower() != 'y':
                return True
        
        while True:
            try:
                capital_input = input("Enter your total trading capital (USD): $")
                capital_amount = float(capital_input.replace(',', '').replace('$', ''))
                
                if self.initialize_capital(capital_amount):
                    print(f"Capital set to ${capital_amount:,.2f}")
                    return True
                else:
                    print("Error setting capital. Please try again.")
                    
            except ValueError:
                print("Please enter a valid number.")
            except KeyboardInterrupt:
                print("\nCapital setup cancelled.")
                return False