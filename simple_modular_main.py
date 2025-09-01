#!/usr/bin/env python3
"""
AutomationBot - Simple Modular System
Working version with basic dashboard
"""

import logging
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from api.simple_modular_routes import create_simple_modular_app
from config import system_config

def setup_logging():
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logs_dir = Path('./logs')
    logs_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, system_config.log_level),
        format=log_format,
        handlers=[
            logging.FileHandler('./logs/simple_modular_bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    
    logger.info("Starting AutomationBot Simple Modular System")
    
    try:
        app = create_simple_modular_app()
        logger.info("Simple modular application ready")
        logger.info(f"Dashboard: http://localhost:{system_config.api_port}/")
        logger.info(f"Health: http://localhost:{system_config.api_port}/health")
        
        app.run(
            host='0.0.0.0',
            port=system_config.api_port,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Shutting down")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()