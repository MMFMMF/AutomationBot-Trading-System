from flask import Flask, request, jsonify
import logging
from datetime import datetime
import uuid

from core.modular_automation_engine import ModularAutomationEngine
from core.di_container import DIContainer
from core.models import TradingSignal, OrderSide, OrderType

logger = logging.getLogger(__name__)

def create_modular_app():
    """Create Flask application with modular architecture"""
    app = Flask(__name__)
    
    # Initialize DI container and automation engine
    try:
        di_container = DIContainer()
        automation_engine = ModularAutomationEngine(di_container)
        logger.info("Modular application initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize modular application: {e}")
        raise
    
    @app.route('/', methods=['GET'])
    def dashboard():
        """Enhanced dashboard with provider status"""
        try:
            status = automation_engine.get_status_summary()
            provider_status = automation_engine.get_provider_status()
            risk_metrics = automation_engine.get_risk_metrics()
            
            # Enhanced HTML dashboard
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AutomationBot - Modular Trading System</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #2c3e50, #34495e); color: white; padding: 30px; }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header p {{ margin: 10px 0 0; opacity: 0.9; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
        .card {{ background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; }}
        .card-header {{ background: #3498db; color: white; padding: 15px; font-weight: bold; }}
        .card-content {{ padding: 20px; }}
        .metric {{ text-align: center; margin: 15px 0; }}
        .metric-value {{ font-size: 2.2em; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ color: #7f8c8d; font-size: 0.9em; margin-top: 5px; }}
        .status-ok {{ color: #27ae60; }}
        .status-error {{ color: #e74c3c; }}
        .status-warning {{ color: #f39c12; }}
        .provider-item {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
        .provider-item:last-child {{ border-bottom: none; }}
        .endpoint {{ font-family: 'Courier New', monospace; background: #ecf0f1; padding: 12px; border-radius: 6px; margin: 8px 0; }}
        .mode-info {{ background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .risk-item {{ display: flex; justify-content: space-between; margin: 8px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🤖 AutomationBot</h1>
            <p>Modular Architecture • {status['operating_mode'].replace('_', ' ').title()} Mode • {status['mode_config']['description']}</p>
        </div>
    </div>
    
    <div class="container">
        <div class="grid">
            <div class="card">
                <div class="card-header">📊 Signal Metrics</div>
                <div class="card-content">
                    <div class="metric">
                        <div class="metric-value">{status['total_signals']}</div>
                        <div class="metric-label">Total Signals</div>
                    </div>
                    <div class="risk-item">
                        <span>Executed:</span>
                        <span class="status-ok">{status['executed']}</span>
                    </div>
                    <div class="risk-item">
                        <span>Blocked:</span>
                        <span class="status-error">{status['blocked']}</span>
                    </div>
                    <div class="risk-item">
                        <span>Processing:</span>
                        <span>{status['processing']}</span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">🏦 Provider Status</div>
                <div class="card-content">
                    <div class="provider-item">
                        <span>Price Data:</span>
                        <span class="{'status-ok' if isinstance(status['providers'].get('price_data'), dict) and status['providers']['price_data'].get('status') == 'connected' else 'status-error'}">
                            {status['providers'].get('price_data', {}).get('provider_name', 'Unknown') if isinstance(status['providers'].get('price_data'), dict) else 'Error'}
                        </span>
                    </div>
                    <div class="provider-item">
                        <span>Execution:</span>
                        <span class="{'status-ok' if isinstance(status['providers'].get('execution'), dict) and status['providers']['execution'].get('status') == 'connected' else 'status-error'}">
                            {status['providers'].get('execution', {}).get('provider_name', 'Unknown') if isinstance(status['providers'].get('execution'), dict) else 'Error'}
                        </span>
                    </div>
                    <div class="provider-item">
                        <span>News:</span>
                        <span class="status-warning">
                            {status['providers'].get('news', {}).get('provider_name', 'Not Available') if isinstance(status['providers'].get('news'), dict) else 'Optional'}
                        </span>
                    </div>
                    <div class="provider-item">
                        <span>Analytics:</span>
                        <span class="{'status-ok' if isinstance(status['providers'].get('analytics'), dict) else 'status-warning'}">
                            {status['providers'].get('analytics', {}).get('provider_name', 'Available') if isinstance(status['providers'].get('analytics'), dict) else 'Optional'}
                        </span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">⚖️ Risk Management</div>
                <div class="card-content">
                    <div class="risk-item">
                        <span>Available Balance:</span>
                        <span class="status-ok">${risk_metrics.get('available_balance', 0):,.2f}</span>
                    </div>
                    <div class="risk-item">
                        <span>Daily P&L:</span>
                        <span class="{'status-ok' if risk_metrics.get('daily_pnl', 0) >= 0 else 'status-error'}">${risk_metrics.get('daily_pnl', 0):,.2f}</span>
                    </div>
                    <div class="risk-item">
                        <span>Max Position:</span>
                        <span>${risk_metrics.get('max_position_size', 0):,.2f} ({risk_metrics.get('max_position_pct', 0):.1%})</span>
                    </div>
                    <div class="risk-item">
                        <span>Daily Loss Limit:</span>
                        <span>${risk_metrics.get('daily_loss_limit', 0):,.2f}</span>
                    </div>
                    <div class="risk-item">
                        <span>Open Positions:</span>
                        <span>{risk_metrics.get('current_positions_count', 0)}</span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">🎯 Symbol Routing</div>
                <div class="card-content">
                    <div class="mode-info">
                        <strong>Current Mode:</strong> {status['mode_config']['description']}
                    </div>
"""
            
            # Add symbol routing info
            for symbol_type, venue in status['mode_config']['symbol_routing'].items():
                html += f"""
                    <div class="risk-item">
                        <span>{symbol_type.title()}:</span>
                        <span class="{'status-ok' if venue != 'blocked' else 'status-error'}">{venue.title()}</span>
                    </div>
"""
            
            html += f"""
                </div>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <div class="card-header">🔌 API Endpoints</div>
            <div class="card-content">
                <div class="endpoint">POST /signal - Submit trading signal</div>
                <div class="endpoint">GET /status - System status</div>
                <div class="endpoint">GET /signals?type=all|executed|blocked|active - Signal history</div>
                <div class="endpoint">GET /providers - Provider status</div>
                <div class="endpoint">GET /risk-metrics - Risk management data</div>
                <div class="endpoint">POST /switch-mode - Change trading mode</div>
                
                <h3>Sample Signal:</h3>
                <div class="endpoint">{{"symbol":"AAPL","side":"buy","quantity":10,"order_type":"market"}}</div>
                
                <div style="margin-top: 15px; color: #7f8c8d; font-size: 0.9em;">
                    <strong>Last Update:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
                    <strong>Mode:</strong> {status['operating_mode']} | 
                    <strong>Auto-refresh:</strong> 30s
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
            return html
            
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return f"<h1>AutomationBot - Modular</h1><p>Error loading dashboard: {str(e)}</p>"

    @app.route('/health', methods=['GET'])
    def health_check():
        """Enhanced health check with provider status"""
        try:
            provider_health = automation_engine.get_provider_status()
            
            # Convert ProviderHealthCheck objects to dictionaries
            serializable_health = {}
            for provider_type, health_check in provider_health.items():
                if hasattr(health_check, 'status'):
                    serializable_health[provider_type] = {
                        'provider_name': health_check.provider_name,
                        'status': health_check.status.value,
                        'last_check': health_check.last_check.isoformat(),
                        'response_time_ms': health_check.response_time_ms,
                        'error_message': health_check.error_message
                    }
                else:
                    serializable_health[provider_type] = str(health_check)
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '2.0.0-modular',
                'architecture': 'modular',
                'providers': serializable_health
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/signal', methods=['POST'])
    def receive_signal():
        """Process trading signal through modular architecture"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['symbol', 'side', 'quantity']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Create trading signal
            signal = TradingSignal(
                id=str(uuid.uuid4()),
                symbol=data['symbol'].upper(),
                side=OrderSide(data['side'].lower()),
                quantity=float(data['quantity']),
                order_type=OrderType(data.get('order_type', 'market').lower()),
                price=float(data['price']) if data.get('price') else None,
                stop_price=float(data['stop_price']) if data.get('stop_price') else None
            )
            
            # Process signal through modular automation engine
            processed_signal = automation_engine.process_signal(signal)
            
            # Enhanced response with provider information
            response = {
                'signal_id': processed_signal.id,
                'status': processed_signal.status.value,
                'symbol': processed_signal.symbol,
                'side': processed_signal.side.value,
                'quantity': processed_signal.quantity,
                'venue': processed_signal.venue,
                'timestamp': processed_signal.timestamp.isoformat(),
                'providers_used': {
                    'price_data': processed_signal.metadata.get('market_data', {}).get('provider'),
                    'execution': processed_signal.metadata.get('execution', {}).get('provider')
                }
            }
            
            if processed_signal.status.value == 'executed':
                response.update({
                    'execution_price': processed_signal.execution_price,
                    'execution_time': processed_signal.execution_time.isoformat() if processed_signal.execution_time else None,
                    'execution_details': processed_signal.metadata.get('execution', {})
                })
            elif processed_signal.status.value == 'blocked':
                response['block_reason'] = processed_signal.block_reason
            
            # Add enhanced metadata
            if 'market_data' in processed_signal.metadata:
                response['market_data'] = processed_signal.metadata['market_data']
            
            if 'sentiment' in processed_signal.metadata:
                response['sentiment'] = processed_signal.metadata['sentiment']
                
            if 'technical_analysis' in processed_signal.metadata:
                response['technical_analysis'] = processed_signal.metadata['technical_analysis']
            
            status_code = 200 if processed_signal.status.value == 'executed' else 422
            return jsonify(response), status_code
            
        except ValueError as e:
            return jsonify({'error': f'Invalid input: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Error processing signal: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/status', methods=['GET'])
    def get_status():
        """Get comprehensive system status"""
        try:
            status = automation_engine.get_status_summary()
            return jsonify(status)
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/providers', methods=['GET'])
    def get_providers():
        """Get detailed provider status"""
        try:
            provider_status = automation_engine.get_provider_status()
            current_mode = automation_engine.di_container.modes_config["current_mode"]
            mode_config = automation_engine.di_container.get_current_mode_config()
            
            return jsonify({
                'current_mode': current_mode,
                'mode_config': mode_config,
                'provider_health': provider_status,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error getting provider status: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/risk-metrics', methods=['GET'])
    def get_risk_metrics():
        """Get risk management metrics"""
        try:
            risk_metrics = automation_engine.get_risk_metrics()
            return jsonify(risk_metrics)
        except Exception as e:
            logger.error(f"Error getting risk metrics: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/switch-mode', methods=['POST'])
    def switch_mode():
        """Switch trading mode"""
        try:
            data = request.get_json()
            new_mode = data.get('mode')
            
            if not new_mode:
                return jsonify({'error': 'Mode parameter required'}), 400
            
            available_modes = list(automation_engine.di_container.modes_config['trading_modes'].keys())
            if new_mode not in available_modes:
                return jsonify({
                    'error': f'Invalid mode. Available modes: {available_modes}'
                }), 400
            
            automation_engine.switch_mode(new_mode)
            
            return jsonify({
                'success': True,
                'new_mode': new_mode,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error switching mode: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/signals', methods=['GET'])
    def get_signals():
        """Get signal history with enhanced metadata"""
        try:
            signal_type = request.args.get('type', 'all')
            
            if signal_type == 'executed':
                signals = automation_engine.get_executed_signals()
            elif signal_type == 'blocked':
                signals = automation_engine.get_blocked_signals()
            elif signal_type == 'active':
                signals = automation_engine.get_active_signals()
            else:
                signals = automation_engine.active_signals
            
            # Convert signals to enhanced JSON format
            signals_data = []
            for signal in signals:
                signal_data = {
                    'id': signal.id,
                    'symbol': signal.symbol,
                    'side': signal.side.value,
                    'quantity': signal.quantity,
                    'order_type': signal.order_type.value,
                    'status': signal.status.value,
                    'timestamp': signal.timestamp.isoformat(),
                    'venue': signal.venue
                }
                
                if signal.price:
                    signal_data['price'] = signal.price
                if signal.execution_price:
                    signal_data['execution_price'] = signal.execution_price
                if signal.execution_time:
                    signal_data['execution_time'] = signal.execution_time.isoformat()
                if signal.block_reason:
                    signal_data['block_reason'] = signal.block_reason
                
                # Add enhanced metadata
                if signal.metadata:
                    signal_data['metadata'] = signal.metadata
                
                signals_data.append(signal_data)
            
            return jsonify({
                'signals': signals_data,
                'count': len(signals_data),
                'type': signal_type,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting signals: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    return app