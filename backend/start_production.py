"""
Production entrypoint for Railway deployment
Runs both token_server and LiveKit agent
"""
import os
import sys
import subprocess
import signal
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def run_production():
    """Run both services for production"""
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Import token server
    from token_server import app as token_app
    
    # Import LiveKit agent main
    import main
    
    # Get port from Railway environment
    port = int(os.getenv('PORT', 5000))
    
    logger.info(f"🚀 Starting Chef AI Voice Agent on port {port}")
    logger.info("📡 Token Server: Enabled")
    logger.info("🎙️ LiveKit Agent: Starting...")
    
    # Start token server in background thread
    import threading
    def run_token_server():
        token_app.run(host='0.0.0.0', port=port)
    
    t = threading.Thread(target=run_token_server, daemon=True)
    t.start()
    
    logger.info(f"✅ Token server listening on 0.0.0.0:{port}")
    
    # Run LiveKit agent (blocks)
    main.run_agent_production()

if __name__ == "__main__":
    run_production()
