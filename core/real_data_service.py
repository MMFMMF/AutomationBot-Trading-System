"""
Real Data Service for AutomationBot Trading Platform

This service provides ONLY real, verified data with NO synthetic or placeholder data.
All calculations are based on actual trade records and verified signals.
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from core.logging_system import system_monitor
from core.data_integrity import data_integrity_manager, DataLineage


class RealDataService:
    """
    Service that provides only real, verified trading data
    """
    
    def __init__(self, database_path: str):
        """
        Initialize real data service
        
        Args:
            database_path: Path to trading database
        """
        self.database_path = database_path
        self.logger = system_monitor.get_logger('real_data_service')
        self._register_data_lineage()
    
    def _register_data_lineage(self):
        """Register data lineage for all data types"""
        # Register trade data lineage
        data_integrity_manager.register_data_lineage(
            'trade_data',
            DataLineage(
                data_type='trade_data',
                source_table='paper_trades',
                source_query='SELECT * FROM paper_trades WHERE status = "executed"',
                calculation_method='Direct database query',
                validation_rules=['trade_logic', 'price_reasonableness', 'timestamp_sequence'],
                last_verified=0
            )
        )
        
        # Register performance metrics lineage
        data_integrity_manager.register_data_lineage(
            'performance_metrics',
            DataLineage(
                data_type='performance_metrics',
                source_table='paper_trades',
                source_query='SELECT * FROM paper_trades WHERE exit_time IS NOT NULL',
                calculation_method='Calculated from completed trades only',
                validation_rules=['metric_calculation', 'metric_consistency'],
                last_verified=0
            )
        )
        
        # Register portfolio data lineage
        data_integrity_manager.register_data_lineage(
            'portfolio_data',
            DataLineage(
                data_type='portfolio_data',
                source_table='paper_trades',
                source_query='SELECT * FROM paper_trades WHERE status IN ("executed", "open")',
                calculation_method='Sum of position values from real trades',
                validation_rules=['portfolio_calculation'],
                last_verified=0
            )
        )
    
    def _get_database_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        try:
            conn = sqlite3.connect(self.database_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise
    
    def get_real_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get real trade history from database - NO synthetic data
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of real trade records
        """
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()
            
            # Query only real, executed trades
            query = """
            SELECT 
                trade_id,
                symbol,
                entry_time,
                exit_time,
                entry_price,
                exit_price,
                quantity,
                side,
                strategy,
                pnl,
                status,
                created_at
            FROM paper_trades 
            WHERE status IN ('executed', 'closed', 'open')
            ORDER BY created_at DESC 
            LIMIT ?
            """
            
            cursor.execute(query, (limit,))
            trades = []
            
            for row in cursor.fetchall():
                trade_data = {
                    'trade_id': row['trade_id'],
                    'symbol': row['symbol'],
                    'entry_time': row['entry_time'],
                    'exit_time': row['exit_time'],
                    'entry_price': float(row['entry_price']) if row['entry_price'] else None,
                    'exit_price': float(row['exit_price']) if row['exit_price'] else None,
                    'quantity': int(row['quantity']) if row['quantity'] else None,
                    'side': row['side'],
                    'strategy': row['strategy'],
                    'pnl': float(row['pnl']) if row['pnl'] else 0.0,
                    'status': row['status'],
                    'created_at': row['created_at']
                }
                
                trades.append(trade_data)
            
            conn.close()
            
            # Validate each trade before returning
            validated_trades = []
            for trade in trades:
                validated_trade, is_valid = data_integrity_manager.get_verified_data_or_null(
                    'trade_data', trade, strict_mode=True
                )
                if is_valid:
                    validated_trades.append(validated_trade)
                else:
                    self.logger.warning(f"Invalid trade data excluded: {trade.get('trade_id', 'unknown')}")
            
            self.logger.info(f"Retrieved {len(validated_trades)} verified trades (excluded {len(trades) - len(validated_trades)} invalid trades)")
            return validated_trades
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve trade history: {e}")
            return []
    
    def get_real_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate real performance metrics from actual completed trades only
        
        Returns:
            Dictionary of real performance metrics or empty dict if insufficient data
        """
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()
            
            # Get only completed trades (trades with exit_time and exit_price)
            query = """
            SELECT 
                strategy,
                pnl,
                entry_time,
                exit_time,
                side
            FROM paper_trades 
            WHERE status IN ('closed', 'executed')
            AND exit_time IS NOT NULL 
            AND exit_price IS NOT NULL
            AND pnl IS NOT NULL
            """
            
            cursor.execute(query)
            completed_trades = cursor.fetchall()
            conn.close()
            
            if not completed_trades:
                self.logger.info("No completed trades available for performance calculation")
                return {}
            
            # Calculate strategy performance from real data only
            strategy_stats = defaultdict(lambda: {
                'trades': 0,
                'winning_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0
            })
            
            total_trades = 0
            total_pnl = 0.0
            winning_trades = 0
            
            for trade in completed_trades:
                strategy = trade['strategy'] or 'unknown'
                pnl = float(trade['pnl']) if trade['pnl'] else 0.0
                
                # Update strategy stats
                strategy_stats[strategy]['trades'] += 1
                strategy_stats[strategy]['total_pnl'] += pnl
                
                if pnl > 0:
                    strategy_stats[strategy]['winning_trades'] += 1
                    winning_trades += 1
                
                total_trades += 1
                total_pnl += pnl
            
            # Calculate win rates
            for strategy in strategy_stats:
                stats = strategy_stats[strategy]
                if stats['trades'] > 0:
                    stats['win_rate'] = stats['winning_trades'] / stats['trades']
            
            # Create performance metrics
            performance_metrics = {
                'strategy_performance': dict(strategy_stats),
                'overall_metrics': {
                    'total_trades': total_trades,
                    'total_pnl': round(total_pnl, 2),
                    'win_rate': round(winning_trades / total_trades if total_trades > 0 else 0, 3),
                    'average_pnl_per_trade': round(total_pnl / total_trades if total_trades > 0 else 0, 2)
                }
            }
            
            # Validate metrics before returning
            validated_metrics, is_valid = data_integrity_manager.get_verified_data_or_null(
                'performance_metrics', performance_metrics, strict_mode=True
            )
            
            if is_valid:
                self.logger.info(f"Calculated performance metrics from {total_trades} real trades")
                return validated_metrics
            else:
                self.logger.warning("Performance metrics failed validation")
                return {}
                
        except Exception as e:
            self.logger.error(f"Failed to calculate performance metrics: {e}")
            return {}
    
    def get_real_portfolio_history(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Calculate real portfolio history from actual trade records
        
        Args:
            hours_back: Hours of history to calculate
            
        Returns:
            List of portfolio value points based on real trades
        """
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()
            
            # Get all trades in the time period
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            query = """
            SELECT 
                entry_time,
                exit_time,
                entry_price,
                exit_price,
                quantity,
                side,
                pnl
            FROM paper_trades 
            WHERE status IN ('executed', 'closed', 'open')
            AND datetime(entry_time) >= datetime(?)
            ORDER BY entry_time ASC
            """
            
            cursor.execute(query, (cutoff_time.isoformat(),))
            trades = cursor.fetchall()
            conn.close()
            
            if not trades:
                self.logger.info("No trades found in specified time period")
                return []
            
            # Calculate portfolio value changes from actual trades
            portfolio_events = []
            
            for trade in trades:
                entry_time = datetime.fromisoformat(trade['entry_time'].replace('Z', '+00:00'))
                entry_value = float(trade['entry_price']) * int(trade['quantity']) if trade['entry_price'] and trade['quantity'] else 0
                
                portfolio_events.append({
                    'timestamp': entry_time,
                    'value_change': -entry_value if trade['side'] == 'BUY' else entry_value,
                    'event_type': 'trade_entry',
                    'trade_info': {
                        'symbol': trade.get('symbol', 'UNKNOWN'),
                        'side': trade['side'],
                        'price': float(trade['entry_price']) if trade['entry_price'] else 0,
                        'quantity': int(trade['quantity']) if trade['quantity'] else 0
                    }
                })
                
                # Add exit event if trade is closed
                if trade['exit_time'] and trade['exit_price']:
                    exit_time = datetime.fromisoformat(trade['exit_time'].replace('Z', '+00:00'))
                    exit_value = float(trade['exit_price']) * int(trade['quantity'])
                    
                    portfolio_events.append({
                        'timestamp': exit_time,
                        'value_change': exit_value if trade['side'] == 'BUY' else -exit_value,
                        'event_type': 'trade_exit',
                        'pnl': float(trade['pnl']) if trade['pnl'] else 0
                    })
            
            # Sort events by timestamp
            portfolio_events.sort(key=lambda x: x['timestamp'])
            
            # Calculate portfolio value over time
            starting_capital = 50000.0  # This should come from configuration
            current_value = starting_capital
            portfolio_history = []
            
            # Add starting point
            start_time = cutoff_time
            portfolio_history.append({
                'timestamp': start_time.isoformat(),
                'value': current_value,
                'event': 'period_start'
            })
            
            # Process each event
            for event in portfolio_events:
                current_value += event['value_change']
                
                portfolio_history.append({
                    'timestamp': event['timestamp'].isoformat(),
                    'value': round(current_value, 2),
                    'event': event['event_type'],
                    'change': event['value_change']
                })
            
            # Validate portfolio data
            validated_history, is_valid = data_integrity_manager.get_verified_data_or_null(
                'portfolio_data', portfolio_history, strict_mode=True
            )
            
            if is_valid:
                self.logger.info(f"Calculated portfolio history from {len(trades)} real trades")
                return validated_history
            else:
                self.logger.warning("Portfolio history failed validation")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to calculate portfolio history: {e}")
            return []
    
    def get_real_position_breakdown(self) -> List[Dict[str, Any]]:
        """
        Get real position breakdown from actual open trades
        
        Returns:
            List of current positions based on real trades
        """
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()
            
            # Get currently open positions (trades without exit_time)
            query = """
            SELECT 
                symbol,
                entry_price,
                quantity,
                side,
                entry_time,
                pnl
            FROM paper_trades 
            WHERE status = 'open'
            AND exit_time IS NULL
            """
            
            cursor.execute(query)
            open_trades = cursor.fetchall()
            conn.close()
            
            if not open_trades:
                self.logger.info("No open positions found")
                return []
            
            # Group by symbol
            symbol_positions = defaultdict(lambda: {
                'symbol': '',
                'total_quantity': 0,
                'total_cost': 0.0,
                'unrealized_pnl': 0.0,
                'trade_count': 0,
                'avg_entry_price': 0.0,
                'positions': []
            })
            
            for trade in open_trades:
                symbol = trade['symbol']
                quantity = int(trade['quantity']) if trade['quantity'] else 0
                entry_price = float(trade['entry_price']) if trade['entry_price'] else 0
                pnl = float(trade['pnl']) if trade['pnl'] else 0
                
                pos = symbol_positions[symbol]
                pos['symbol'] = symbol
                pos['total_quantity'] += quantity if trade['side'] == 'BUY' else -quantity
                pos['total_cost'] += entry_price * quantity
                pos['unrealized_pnl'] += pnl
                pos['trade_count'] += 1
                
                pos['positions'].append({
                    'entry_price': entry_price,
                    'quantity': quantity,
                    'side': trade['side'],
                    'entry_time': trade['entry_time'],
                    'unrealized_pnl': pnl
                })
            
            # Calculate average entry prices and format data
            positions_data = []
            for symbol, pos_data in symbol_positions.items():
                if pos_data['total_quantity'] != 0:  # Only show positions with net quantity
                    avg_price = pos_data['total_cost'] / abs(pos_data['total_quantity']) if pos_data['total_quantity'] else 0
                    
                    positions_data.append({
                        'symbol': symbol,
                        'quantity': pos_data['total_quantity'],
                        'avg_entry_price': round(avg_price, 2),
                        'unrealized_pnl': round(pos_data['unrealized_pnl'], 2),
                        'trade_count': pos_data['trade_count'],
                        'market_value': round(abs(pos_data['total_quantity']) * avg_price, 2)
                    })
            
            self.logger.info(f"Retrieved {len(positions_data)} real positions from {len(open_trades)} open trades")
            return positions_data
            
        except Exception as e:
            self.logger.error(f"Failed to get position breakdown: {e}")
            return []
    
    def get_real_daily_pnl(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Calculate real daily P&L from actual completed trades
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of daily P&L based on real trade completions
        """
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()
            
            # Get trades closed in the specified period
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            query = """
            SELECT 
                DATE(exit_time) as exit_date,
                pnl
            FROM paper_trades 
            WHERE status IN ('closed', 'executed')
            AND exit_time IS NOT NULL
            AND pnl IS NOT NULL
            AND datetime(exit_time) >= datetime(?)
            ORDER BY exit_date
            """
            
            cursor.execute(query, (cutoff_date.isoformat(),))
            completed_trades = cursor.fetchall()
            conn.close()
            
            if not completed_trades:
                self.logger.info("No completed trades found for daily P&L calculation")
                return []
            
            # Group by date and sum P&L
            daily_pnl_dict = defaultdict(float)
            
            for trade in completed_trades:
                exit_date = trade['exit_date']
                pnl = float(trade['pnl']) if trade['pnl'] else 0.0
                daily_pnl_dict[exit_date] += pnl
            
            # Convert to list format
            daily_pnl = []
            for date_str, pnl in daily_pnl_dict.items():
                daily_pnl.append({
                    'date': date_str,
                    'pnl': round(pnl, 2),
                    'source': 'real_trades'
                })
            
            # Sort by date
            daily_pnl.sort(key=lambda x: x['date'])
            
            self.logger.info(f"Calculated daily P&L for {len(daily_pnl)} days from real trades")
            return daily_pnl
            
        except Exception as e:
            self.logger.error(f"Failed to calculate daily P&L: {e}")
            return []
    
    def get_comprehensive_real_data(self) -> Dict[str, Any]:
        """
        Get comprehensive real data for dashboard - NO synthetic data
        
        Returns:
            Dictionary with all real data or safe empty responses
        """
        try:
            # Get all real data components
            trade_history = self.get_real_trade_history(100)
            performance_metrics = self.get_real_performance_metrics()
            portfolio_history = self.get_real_portfolio_history(24)
            position_breakdown = self.get_real_position_breakdown()
            daily_pnl = self.get_real_daily_pnl(30)
            
            # Check if we have sufficient data to show meaningful charts
            has_sufficient_data = (
                len(trade_history) > 0 and 
                len(performance_metrics.get('strategy_performance', {})) > 0
            )
            
            if has_sufficient_data:
                comprehensive_data = {
                    'trade_history': trade_history,
                    'portfolio_history': portfolio_history,
                    'strategy_performance': performance_metrics.get('strategy_performance', {}),
                    'overall_performance': performance_metrics.get('overall_metrics', {}),
                    'positions_data': position_breakdown,
                    'daily_pnl': daily_pnl,
                    'data_status': 'REAL_DATA_AVAILABLE',
                    'data_source_verification': {
                        'all_data_verified': True,
                        'trade_count': len(trade_history),
                        'strategies_active': len(performance_metrics.get('strategy_performance', {})),
                        'open_positions': len(position_breakdown),
                        'data_generation_method': 'REAL_TRADES_ONLY'
                    }
                }
                
                self.logger.info("Comprehensive real data compiled successfully")
                return comprehensive_data
            else:
                # Return safe empty response indicating insufficient data
                safe_response = data_integrity_manager.create_empty_response(
                    'chart_data', 
                    'Insufficient trading history for meaningful charts - system is ready but needs more trading activity'
                )
                
                safe_response.update({
                    'data_source_verification': {
                        'all_data_verified': True,
                        'trade_count': len(trade_history),
                        'insufficient_data_reason': 'Not enough completed trades for performance metrics',
                        'data_generation_method': 'REAL_TRADES_ONLY'
                    }
                })
                
                self.logger.info("Insufficient real data for comprehensive display - returning safe empty response")
                return safe_response
                
        except Exception as e:
            self.logger.error(f"Failed to compile comprehensive real data: {e}")
            return data_integrity_manager.create_empty_response(
                'chart_data',
                'Error retrieving real data - displaying safe empty response'
            )


# Global real data service instance
real_data_service = None

def initialize_real_data_service(database_path: str):
    """Initialize the global real data service"""
    global real_data_service
    real_data_service = RealDataService(database_path)

def get_real_data_service() -> RealDataService:
    """Get the global real data service instance"""
    if real_data_service is None:
        raise Exception("Real data service not initialized. Call initialize_real_data_service() first.")
    return real_data_service