"""
Production entrypoint for Railway deployment
Runs token server and LiveKit agent together
"""
import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Get port from Railway
    port = int(os.getenv('PORT', 5000))
    
    logger.info("=" * 60)
    logger.info("🚀 Chef Voice AI Agent - Production")
    logger.info("=" * 60)
    logger.info(f"Token Server Port: {port}")
    
    # Start token server in background thread
    from token_server import app
    import threading
    
    def run_token_server():
        app.run(host='0.0.0.0', port=port, debug=False)
    
    token_thread = threading.Thread(target=run_token_server, daemon=True)
    token_thread.start()
    
    logger.info(f"✅ Token server started on port {port}")
    logger.info("🎙️ Starting LiveKit agent...")
    
    # Import and run main agent
    from main import run_agent_production
    run_agent_production()
