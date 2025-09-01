"""
Enhanced Performance Tracker
Integrates with paper trading engine to provide accurate P&L and performance metrics
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from dataclasses import asdict

from core.pnl_calculator import RealTimePnLCalculator, PerformanceMetrics, PositionPnL
from core.real_time_price_updater import RealTimePriceUpdater, PnLPriceIntegration
from core.config_manager import SystemConfig

logger = logging.getLogger(__name__)

class EnhancedPerformanceTracker:
    """
    Enhanced performance tracker that fixes all P&L calculation issues:
    1. Connects to paper trading engine for real trade data
    2. Provides accurate unrealized P&L calculations
    3. Fixes win rate calculations (closed trades only)
    4. Adds position-level P&L tracking
    5. Comprehensive logging and debugging
    """
    
    def __init__(self, config: SystemConfig, paper_trading_engine=None, polygon_provider=None):
        self.config = config
        self.paper_trading_engine = paper_trading_engine
        self.polygon_provider = polygon_provider
        
        # Initialize P&L calculator
        self.pnl_calculator = RealTimePnLCalculator(config, polygon_provider)
        
        # Initialize price updater
        self.price_updater = RealTimePriceUpdater(config, polygon_provider)
        
        # Create integrated system
        self.integration = PnLPriceIntegration(self.pnl_calculator, self.price_updater)
        
        # Performance tracking
        self.last_calculation = None
        self.calculation_history = []
        self.is_active = False
        
        logger.info("Enhanced performance tracker initialized")
    
    def start_tracking(self):
        """Start performance tracking with real-time updates"""
        if self.is_active:
            logger.warning("Performance tracking already active")
            return
        
        self.is_active = True
        
        # Start price updates
        self.price_updater.start_background_updates()
        
        # Get symbols from paper trading engine
        if self.paper_trading_engine:
            self._sync_tracked_symbols()
        
        logger.info("Performance tracking started")
    
    def stop_tracking(self):
        """Stop performance tracking"""
        self.is_active = False
        self.price_updater.stop_price_updates()
        logger.info("Performance tracking stopped")
    
    def _sync_tracked_symbols(self):
        """Sync tracked symbols with paper trading engine"""
        if not self.paper_trading_engine:
            return
        
        try:
            # Get all symbols from open positions in paper trading engine
            symbols = set()
            
            if hasattr(self.paper_trading_engine, 'paper_trades'):
                for trade in self.paper_trading_engine.paper_trades.values():
                    if trade.status == 'open':
                        symbols.add(trade.symbol)
            
            if symbols:
                self.price_updater.add_symbols(list(symbols))
                logger.info(f"Synced {len(symbols)} symbols with price updater: {symbols}")
            
        except Exception as e:
            logger.error(f"Failed to sync tracked symbols: {e}")
    
    def get_trade_data_from_engine(self) -> List[Dict]:
        """Extract trade data from paper trading engine in memory"""
        if not self.paper_trading_engine:
            logger.warning("No paper trading engine available")
            return []
        
        trade_data = []
        
        try:
            if hasattr(self.paper_trading_engine, 'paper_trades'):
                for trade in self.paper_trading_engine.paper_trades.values():
                    trade_dict = {
                        'trade_id': trade.trade_id,
                        'symbol': trade.symbol,
                        'side': trade.side,
                        'quantity': trade.quantity,
                        'entry_price': trade.entry_price,
                        'entry_time': trade.entry_time.isoformat() if trade.entry_time else None,
                        'exit_price': trade.exit_price,
                        'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                        'pnl': trade.pnl,
                        'status': trade.status,
                        'strategy': trade.strategy,
                        'fees': trade.fees,
                        'slippage': trade.slippage
                    }
                    trade_data.append(trade_dict)
                
                logger.debug(f"Extracted {len(trade_data)} trades from paper trading engine")
            
        except Exception as e:
            logger.error(f"Failed to extract trade data: {e}")
        
        return trade_data
    
    async def calculate_comprehensive_metrics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics with real-time data
        """
        try:
            # Get trade data from paper trading engine
            trade_data = self.get_trade_data_from_engine()
            
            if not trade_data:
                return {
                    "status": "No trade data available",
                    "total_trades": 0,
                    "message": "Paper trading engine has no trades or is not connected",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Sync symbols for price tracking
            self._sync_tracked_symbols()
            
            # Calculate position P&L with real-time prices
            positions = self.pnl_calculator.calculate_position_pnl(trade_data)
            
            # Calculate performance metrics
            metrics = self.pnl_calculator.calculate_performance_metrics(trade_data)
            
            # Get position summary
            position_summary = self.pnl_calculator.get_position_summary()
            
            # Get performance summary  
            performance_summary = self.pnl_calculator.get_performance_summary()
            
            # Create comprehensive report
            comprehensive_metrics = {
                "calculation_timestamp": datetime.now().isoformat(),
                "data_source": "paper_trading_engine_memory",
                "trade_analysis": {
                    "total_trades_found": len(trade_data),
                    "open_trades": len([t for t in trade_data if t.get('status') == 'open']),
                    "closed_trades": len([t for t in trade_data if t.get('status') == 'closed']),
                    "data_integrity": {
                        "all_trades_have_ids": all(t.get('trade_id') for t in trade_data),
                        "all_trades_have_symbols": all(t.get('symbol') for t in trade_data),
                        "all_trades_have_prices": all(t.get('entry_price') for t in trade_data)
                    }
                },
                "position_analysis": position_summary,
                "performance_metrics": performance_summary,
                "raw_metrics": asdict(metrics) if metrics else {},
                "position_details": [
                    {
                        "symbol": pos.symbol,
                        "side": pos.side,
                        "quantity": pos.quantity,
                        "entry_price": pos.entry_price,
                        "current_price": pos.current_price,
                        "unrealized_pnl": pos.unrealized_pnl,
                        "unrealized_pnl_percent": pos.unrealized_pnl_percent,
                        "market_value": pos.market_value,
                        "cost_basis": pos.cost_basis,
                        "trade_count": len(pos.trade_ids),
                        "last_price_update": pos.last_price_update.isoformat()
                    }
                    for pos in positions.values()
                ],
                "debugging_info": {
                    "pnl_calculator_active": True,
                    "price_updater_active": self.price_updater.is_running,
                    "market_hours": self.price_updater.is_market_hours(),
                    "tracked_symbols": len(self.price_updater.tracked_symbols),
                    "current_prices_available": len(self.price_updater.latest_prices),
                    "calculation_method": "real_time_with_market_data"
                }
            }
            
            # Store calculation for history
            self.last_calculation = comprehensive_metrics
            self.calculation_history.append({
                'timestamp': datetime.now(),
                'total_pnl': metrics.total_pnl if metrics else 0,
                'unrealized_pnl': metrics.unrealized_pnl if metrics else 0,
                'win_rate': metrics.win_rate if metrics else 0,
                'total_trades': len(trade_data)
            })
            
            # Keep only last 100 calculations
            if len(self.calculation_history) > 100:
                self.calculation_history = self.calculation_history[-100:]
            
            logger.info(f"""
            Comprehensive Metrics Calculated:
            - Total Trades: {len(trade_data)}
            - Open Positions: {len(positions)}
            - Total P&L: ${metrics.total_pnl:.2f if metrics else 0}
            - Unrealized P&L: ${metrics.unrealized_pnl:.2f if metrics else 0}
            - Win Rate: {metrics.win_rate:.1f if metrics else 0}%
            """)
            
            return comprehensive_metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate comprehensive metrics: {e}", exc_info=True)
            return {
                "status": "calculation_error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_position_pnl_details(self) -> List[Dict[str, Any]]:
        """Get detailed P&L information for each position"""
        try:
            trade_data = self.get_trade_data_from_engine()
            positions = self.pnl_calculator.calculate_position_pnl(trade_data)
            
            position_details = []
            
            for position in positions.values():
                # Get individual trades for this position
                individual_trades = []
                for trade_id in position.trade_ids:
                    trade = next((t for t in trade_data if t.get('trade_id') == trade_id), None)
                    if trade:
                        individual_trades.append({
                            'trade_id': trade_id,
                            'quantity': trade.get('quantity', 0),
                            'entry_price': trade.get('entry_price', 0),
                            'entry_time': trade.get('entry_time'),
                            'cost': trade.get('quantity', 0) * trade.get('entry_price', 0)
                        })
                
                position_detail = {
                    'position_key': f"{position.symbol}_{position.side}",
                    'symbol': position.symbol,
                    'side': position.side,
                    'summary': {
                        'total_quantity': position.quantity,
                        'average_entry_price': position.entry_price,
                        'current_market_price': position.current_price,
                        'total_cost_basis': position.cost_basis,
                        'current_market_value': position.market_value,
                        'unrealized_pnl': position.unrealized_pnl,
                        'unrealized_pnl_percent': position.unrealized_pnl_percent
                    },
                    'calculation_details': {
                        'price_difference': position.current_price - position.entry_price,
                        'price_difference_percent': ((position.current_price - position.entry_price) / position.entry_price * 100) if position.entry_price > 0 else 0,
                        'position_multiplier': 1 if position.side.lower() == 'buy' else -1,
                        'pnl_per_share': (position.current_price - position.entry_price) if position.side.lower() == 'buy' else (position.entry_price - position.current_price),
                        'total_shares': position.quantity
                    },
                    'individual_trades': individual_trades,
                    'trade_count': len(individual_trades),
                    'last_price_update': position.last_price_update.isoformat(),
                    'manual_verification': {
                        'expected_pnl_calculation': f"({position.current_price} - {position.entry_price}) * {position.quantity} = {position.unrealized_pnl:.2f}",
                        'side_adjusted': position.side.lower() == 'buy'
                    }
                }
                
                position_details.append(position_detail)
            
            # Sort by absolute P&L (largest gains/losses first)
            position_details.sort(key=lambda x: abs(x['summary']['unrealized_pnl']), reverse=True)
            
            return position_details
            
        except Exception as e:
            logger.error(f"Failed to get position P&L details: {e}")
            return []
    
    def get_debugging_report(self) -> Dict[str, Any]:
        """Generate comprehensive debugging report for P&L calculations"""
        try:
            trade_data = self.get_trade_data_from_engine()
            
            # Analyze trade data quality
            open_trades = [t for t in trade_data if t.get('status') == 'open']
            closed_trades = [t for t in trade_data if t.get('status') == 'closed']
            
            # Check for data issues
            issues = []
            
            if not trade_data:
                issues.append("No trade data found in paper trading engine")
            
            if all(t.get('pnl') == 0 for t in open_trades):
                issues.append("All open trades show $0.00 unrealized P&L - price updates may be missing")
            
            missing_prices = [t['symbol'] for t in open_trades if t['symbol'] not in self.price_updater.latest_prices]
            if missing_prices:
                issues.append(f"Missing current prices for: {missing_prices}")
            
            # Performance calculation verification
            manual_calculations = {}
            if open_trades:
                total_unrealized = 0
                for trade in open_trades:
                    symbol = trade['symbol']
                    current_price = self.price_updater.get_current_price(symbol)
                    entry_price = trade.get('entry_price', 0)
                    quantity = trade.get('quantity', 0)
                    side = trade.get('side', '')
                    
                    if current_price and entry_price > 0:
                        if side.lower() == 'buy':
                            pnl = (current_price - entry_price) * quantity
                        else:
                            pnl = (entry_price - current_price) * quantity
                        
                        total_unrealized += pnl
                        manual_calculations[trade.get('trade_id', 'unknown')] = {
                            'symbol': symbol,
                            'calculation': f"({current_price} - {entry_price}) * {quantity} = {pnl:.2f}",
                            'side_adjusted': side.lower() == 'buy',
                            'manual_pnl': pnl
                        }
            
            return {
                "debugging_timestamp": datetime.now().isoformat(),
                "data_analysis": {
                    "total_trades_in_memory": len(trade_data),
                    "open_trades_count": len(open_trades),
                    "closed_trades_count": len(closed_trades),
                    "unique_symbols": len(set(t['symbol'] for t in trade_data)),
                    "trades_with_valid_prices": len([t for t in trade_data if t.get('entry_price', 0) > 0])
                },
                "price_data_analysis": {
                    "tracked_symbols": list(self.price_updater.tracked_symbols),
                    "symbols_with_current_prices": list(self.price_updater.latest_prices.keys()),
                    "price_updater_running": self.price_updater.is_running,
                    "last_price_update": max((u.timestamp for u in self.price_updater.latest_prices.values()), default=datetime.now()).isoformat(),
                    "market_hours": self.price_updater.is_market_hours()
                },
                "calculation_verification": {
                    "manual_unrealized_pnl": sum(calc['manual_pnl'] for calc in manual_calculations.values()),
                    "individual_calculations": manual_calculations
                },
                "identified_issues": issues,
                "system_status": {
                    "paper_trading_engine_connected": self.paper_trading_engine is not None,
                    "polygon_provider_available": self.polygon_provider is not None,
                    "pnl_calculator_initialized": self.pnl_calculator is not None,
                    "price_updater_active": self.is_active,
                    "last_comprehensive_calculation": self.last_calculation.get('calculation_timestamp') if self.last_calculation else None
                },
                "recommendations": self._generate_recommendations(issues, trade_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate debugging report: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_recommendations(self, issues: List[str], trade_data: List[Dict]) -> List[str]:
        """Generate recommendations based on identified issues"""
        recommendations = []
        
        if not trade_data:
            recommendations.append("Check paper trading engine connection and ensure trades are being created")
        
        if "price updates may be missing" in str(issues):
            recommendations.append("Start price updater with price_updater.start_background_updates()")
            recommendations.append("Verify Polygon.io API key is configured correctly")
        
        if any("Missing current prices" in issue for issue in issues):
            recommendations.append("Force price update with price_updater.force_update(symbols)")
        
        if not recommendations:
            recommendations.append("P&L calculations appear to be working correctly")
        
        return recommendations
    
    def force_full_recalculation(self) -> Dict[str, Any]:
        """Force complete recalculation of all metrics"""
        logger.info("Forcing full P&L recalculation...")
        
        try:
            # Refresh symbol tracking
            self._sync_tracked_symbols()
            
            # Force price updates
            if self.price_updater.tracked_symbols:
                asyncio.create_task(self.price_updater.force_update())
            
            # Recalculate everything
            return asyncio.create_task(self.calculate_comprehensive_metrics())
            
        except Exception as e:
            logger.error(f"Failed to force recalculation: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_calculation_history(self) -> List[Dict]:
        """Get history of P&L calculations for trend analysis"""
        return [
            {
                "timestamp": calc['timestamp'].isoformat(),
                "total_pnl": calc['total_pnl'],
                "unrealized_pnl": calc['unrealized_pnl'],
                "win_rate": calc['win_rate'],
                "total_trades": calc['total_trades']
            }
            for calc in self.calculation_history[-20:]  # Last 20 calculations
        ]


def create_enhanced_tracker(config: SystemConfig, paper_trading_engine=None, polygon_provider=None) -> EnhancedPerformanceTracker:
    """Factory function to create enhanced performance tracker"""
    return EnhancedPerformanceTracker(config, paper_trading_engine, polygon_provider)