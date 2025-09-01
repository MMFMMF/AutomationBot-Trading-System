import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

from core.models import TradingSignal, OrderSide, OrderType
from core.execution_mode_manager import ExecutionModeManager

logger = logging.getLogger(__name__)

class ExecutionTestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ExecutionTestResult:
    test_id: str
    test_name: str
    provider: str
    mode: str
    status: ExecutionTestStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    trade_amount: float
    expected_outcome: str
    actual_outcome: Optional[str]
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ExecutionValidator:
    """Framework for validating execution readiness and testing all modes"""
    
    def __init__(self, automation_engine, execution_mode_manager: ExecutionModeManager):
        self.automation_engine = automation_engine
        self.execution_mode_manager = execution_mode_manager
        self.test_results: List[ExecutionTestResult] = []
        self.active_tests: Dict[str, ExecutionTestResult] = {}
        
    def create_execution_test_plan(self, max_test_amount: float = 50.0) -> List[Dict[str, Any]]:
        """Create comprehensive execution test plan"""
        test_plan = []
        
        # Test 1: Simulation mode validation
        test_plan.append({
            "test_name": "Simulation Mode - Stock Trade",
            "provider": "tradestation",
            "mode": "simulation",
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 1,
            "max_amount": max_test_amount,
            "expected_outcome": "simulated_execution",
            "description": "Verify simulation works correctly for stock trades"
        })
        
        # Test 2: Simulation mode - DeFi
        test_plan.append({
            "test_name": "Simulation Mode - DeFi Trade",
            "provider": "defi", 
            "mode": "simulation",
            "symbol": "ETH",
            "side": "buy",
            "quantity": 0.01,
            "max_amount": max_test_amount,
            "expected_outcome": "simulated_execution",
            "description": "Verify DeFi simulation works correctly"
        })
        
        # Test 3: Execution mode readiness (small amounts)
        test_plan.append({
            "test_name": "Execution Mode - Small Stock Trade",
            "provider": "tradestation",
            "mode": "execution",
            "symbol": "AAPL", 
            "side": "buy",
            "quantity": 1,
            "max_amount": 10.0,  # Very small for initial testing
            "expected_outcome": "real_execution",
            "description": "Test real execution with minimal risk",
            "requires_approval": True
        })
        
        # Test 4: Risk management validation
        test_plan.append({
            "test_name": "Risk Management - Oversized Trade",
            "provider": "tradestation",
            "mode": "simulation",
            "symbol": "AAPL",
            "side": "buy", 
            "quantity": 1000,  # Intentionally large
            "max_amount": 100000,
            "expected_outcome": "risk_blocked",
            "description": "Verify risk management blocks oversized trades"
        })
        
        return test_plan
    
    def validate_execution_readiness(self) -> Dict[str, Any]:
        """Comprehensive execution readiness assessment"""
        readiness = {
            "overall_ready": False,
            "readiness_score": 0,
            "max_score": 100,
            "checks": {},
            "recommendations": [],
            "blockers": []
        }
        
        # Check 1: Capital Configuration (20 points)
        if self.automation_engine.capital_manager.is_initialized:
            readiness["checks"]["capital_configured"] = {"status": "passed", "points": 20, "message": "Capital properly initialized"}
            readiness["readiness_score"] += 20
        else:
            readiness["checks"]["capital_configured"] = {"status": "failed", "points": 0, "message": "Capital not initialized"}
            readiness["blockers"].append("Initialize capital amount before execution")
        
        # Check 2: Provider Credentials (25 points)
        provider_status = self.automation_engine.get_provider_status()
        credentials_ready = 0
        total_providers = len(provider_status)
        
        for provider, health in provider_status.items():
            if hasattr(health, 'status') and health.status.value == 'connected':
                credentials_ready += 1
        
        credential_score = int((credentials_ready / total_providers) * 25)
        readiness["checks"]["credentials"] = {
            "status": "passed" if credential_score > 15 else "partial" if credential_score > 0 else "failed",
            "points": credential_score,
            "message": f"{credentials_ready}/{total_providers} providers properly authenticated"
        }
        readiness["readiness_score"] += credential_score
        
        if credential_score < 15:
            readiness["recommendations"].append("Complete provider authentication for full readiness")
        
        # Check 3: Execution Mode Safety (20 points)  
        mode_summary = self.execution_mode_manager.get_mode_summary()
        if mode_summary['global_execution_mode']:
            readiness["checks"]["execution_mode"] = {"status": "warning", "points": 10, "message": "Execution mode enabled - review safety settings"}
            readiness["recommendations"].append("Consider testing in simulation mode first")
            readiness["readiness_score"] += 10
        else:
            readiness["checks"]["execution_mode"] = {"status": "passed", "points": 20, "message": "Simulation mode - safe for testing"}
            readiness["readiness_score"] += 20
        
        # Check 4: Risk Management (20 points)
        try:
            # Test risk validation with dummy signal
            test_signal = TradingSignal(
                id="test_validation",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=10,
                order_type=OrderType.MARKET,
                price=100.0
            )
            risk_check = self.automation_engine.risk_manager.validate_trade(test_signal)
            if risk_check:
                readiness["checks"]["risk_management"] = {"status": "passed", "points": 20, "message": "Risk management functional"}
                readiness["readiness_score"] += 20
            else:
                readiness["checks"]["risk_management"] = {"status": "failed", "points": 0, "message": "Risk management not responding"}
                readiness["blockers"].append("Fix risk management system")
                
        except Exception as e:
            readiness["checks"]["risk_management"] = {"status": "failed", "points": 0, "message": f"Risk management error: {str(e)}"}
            readiness["blockers"].append("Debug risk management system")
        
        # Check 5: System Health (15 points)
        try:
            health_status = self.automation_engine.get_status_summary()
            if health_status and "total_signals" in health_status:
                readiness["checks"]["system_health"] = {"status": "passed", "points": 15, "message": "System responding normally"}
                readiness["readiness_score"] += 15
            else:
                readiness["checks"]["system_health"] = {"status": "partial", "points": 5, "message": "System partially responsive"}
                readiness["readiness_score"] += 5
        except Exception as e:
            readiness["checks"]["system_health"] = {"status": "failed", "points": 0, "message": f"System health check failed: {str(e)}"}
            readiness["blockers"].append("Fix system health issues")
        
        # Determine overall readiness
        if readiness["readiness_score"] >= 80 and not readiness["blockers"]:
            readiness["overall_ready"] = True
            readiness["recommendations"].append("System ready for controlled execution testing")
        elif readiness["readiness_score"] >= 60:
            readiness["recommendations"].append("Address remaining issues before full execution")
        else:
            readiness["blockers"].append("Critical issues must be resolved before execution")
        
        return readiness
    
    def run_execution_test(self, test_config: Dict[str, Any]) -> ExecutionTestResult:
        """Run a single execution test"""
        test_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        test_result = ExecutionTestResult(
            test_id=test_id,
            test_name=test_config["test_name"],
            provider=test_config["provider"],
            mode=test_config["mode"],
            status=ExecutionTestStatus.RUNNING,
            start_time=start_time,
            end_time=None,
            duration_seconds=None,
            trade_amount=test_config.get("max_amount", 0),
            expected_outcome=test_config["expected_outcome"],
            actual_outcome=None
        )
        
        self.active_tests[test_id] = test_result
        logger.info(f"Starting execution test: {test_config['test_name']}")
        
        try:
            # Create test signal
            test_signal = TradingSignal(
                id=f"test_{test_id}",
                symbol=test_config["symbol"],
                side=OrderSide(test_config["side"]),
                quantity=test_config["quantity"],
                order_type=OrderType.MARKET,
                price=test_config.get("price")
            )
            
            # Set execution mode for test
            original_mode = self.execution_mode_manager.is_execution_mode()
            if test_config["mode"] == "execution":
                self.execution_mode_manager.set_execution_mode(True)
            else:
                self.execution_mode_manager.set_execution_mode(False)
            
            # Process the signal
            result = self.automation_engine.process_signal(test_signal)
            
            # Restore original mode
            self.execution_mode_manager.set_execution_mode(original_mode)
            
            # Evaluate result
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            test_result.end_time = end_time
            test_result.duration_seconds = duration
            
            # Determine actual outcome
            if result.status.value == "executed":
                test_result.actual_outcome = "real_execution" if test_config["mode"] == "execution" else "simulated_execution"
                test_result.status = ExecutionTestStatus.PASSED if test_result.actual_outcome == test_config["expected_outcome"] else ExecutionTestStatus.FAILED
            elif result.status.value == "blocked":
                test_result.actual_outcome = "risk_blocked"
                test_result.status = ExecutionTestStatus.PASSED if test_config["expected_outcome"] == "risk_blocked" else ExecutionTestStatus.FAILED
            else:
                test_result.actual_outcome = f"unexpected_{result.status.value}"
                test_result.status = ExecutionTestStatus.FAILED
            
            # Serialize result properly for JSON
            signal_result = {}
            if hasattr(result, '__dict__'):
                for key, value in result.__dict__.items():
                    if hasattr(value, 'value'):  # Handle Enum types
                        signal_result[key] = value.value
                    elif hasattr(value, 'isoformat'):  # Handle datetime
                        signal_result[key] = value.isoformat()
                    else:
                        signal_result[key] = str(value) if not isinstance(value, (int, float, str, bool, type(None))) else value
            else:
                signal_result = str(result)
                
            test_result.metadata = {
                "signal_result": signal_result,
                "execution_price": getattr(result, 'execution_price', None),
                "block_reason": getattr(result, 'block_reason', None)
            }
            
        except Exception as e:
            test_result.status = ExecutionTestStatus.FAILED
            test_result.error_message = str(e)
            test_result.actual_outcome = f"error_{type(e).__name__}"
            test_result.end_time = datetime.now()
            test_result.duration_seconds = (test_result.end_time - start_time).total_seconds()
            logger.error(f"Execution test failed: {test_config['test_name']} - {str(e)}")
        
        # Store result and clean up active test
        self.test_results.append(test_result)
        del self.active_tests[test_id]
        
        logger.info(f"Execution test completed: {test_config['test_name']} - {test_result.status.value}")
        return test_result
    
    def run_full_test_suite(self, max_test_amount: float = 50.0) -> Dict[str, Any]:
        """Run complete execution test suite"""
        test_plan = self.create_execution_test_plan(max_test_amount)
        suite_start = datetime.now()
        
        suite_results = {
            "suite_id": str(uuid.uuid4()),
            "start_time": suite_start.isoformat(),
            "end_time": None,
            "total_tests": len(test_plan),
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "tests": []
        }
        
        for test_config in test_plan:
            # Skip execution tests if not approved
            if test_config.get("requires_approval") and not self.execution_mode_manager.is_execution_mode():
                test_result = ExecutionTestResult(
                    test_id=str(uuid.uuid4()),
                    test_name=test_config["test_name"],
                    provider=test_config["provider"],
                    mode=test_config["mode"],
                    status=ExecutionTestStatus.SKIPPED,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_seconds=0,
                    trade_amount=test_config.get("max_amount", 0),
                    expected_outcome=test_config["expected_outcome"],
                    actual_outcome="skipped_approval_required",
                    error_message="Execution mode not enabled - test skipped for safety"
                )
                suite_results["skipped"] += 1
            else:
                test_result = self.run_execution_test(test_config)
                if test_result.status == ExecutionTestStatus.PASSED:
                    suite_results["passed"] += 1
                else:
                    suite_results["failed"] += 1
            
            suite_results["tests"].append(test_result.__dict__)
        
        suite_end = datetime.now()
        suite_results["end_time"] = suite_end.isoformat()
        suite_results["duration_seconds"] = (suite_end - suite_start).total_seconds()
        
        return suite_results
    
    def get_test_history(self, limit: int = 50) -> List[ExecutionTestResult]:
        """Get recent test execution history"""
        return sorted(self.test_results, key=lambda x: x.start_time, reverse=True)[:limit]
    
    def create_rollback_plan(self) -> Dict[str, Any]:
        """Create rollback plan for emergency return to simulation"""
        return {
            "rollback_steps": [
                "Switch all providers to simulation mode",
                "Verify no pending orders in execution",
                "Check account balances for discrepancies", 
                "Review execution logs for any real trades",
                "Confirm system is in safe simulation state"
            ],
            "emergency_contacts": [
                "System administrator",
                "Risk management team",
                "Broker support (if applicable)"
            ],
            "rollback_commands": {
                "force_simulation": "POST /execution-mode/toggle with execution_mode=false",
                "provider_override": "POST /execution-mode/provider-override with force_simulation=true",
                "system_status": "GET /health and GET /execution-mode"
            }
        }