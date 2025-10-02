# Fixed logging section for server.py
# Replace the logging setup section in your server.py with this code

import sys
import os
import threading
import json
import logging
import queue
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, Request, BackgroundTasks, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# --- Path Setup & Environment Loading ---
app_dir = os.path.dirname(__file__)
framework_dir = os.path.abspath(os.path.join(app_dir, '..'))
dotenv_path = os.path.join(framework_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)

# Add the src directory to Python path
src_path = os.path.join(framework_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# --- Core Imports ---
from my_framework.models.openai import ChatOpenAI
from my_framework.agents.orchestrator import OrchestratorAgent

# Try to import style guru components (they might not exist yet)
try:
    from my_framework.style_guru.training import build_dataset, train_model
    from my_framework.style_guru.deep_analyzer import deep_style_analysis
    STYLE_GURU_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Style Guru components not available: {e}")
    STYLE_GURU_AVAILABLE = False

# --- FIXED LOGGING SETUP ---
class QueueLogHandler(logging.Handler):
    """Custom log handler that puts log messages in a queue."""
    def __init__(self, q):
        super().__init__()
        self.queue = q

    def emit(self, record):
        try:
            msg = self.format(record)
            self.queue.put(msg)
        except Exception:
            self.handleError(record)

# Create log queue
log_queue = queue.Queue(maxsize=1000)  # Limit queue size to prevent memory issues

# Create custom log handler
log_handler = QueueLogHandler(log_queue)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler.setFormatter(formatter)
log_handler.setLevel(logging.INFO)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[]  # Start with empty handlers
)

# Get root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Clear any existing handlers
root_logger.handlers.clear()

# Add console handler
console_handler = logging.StreamHandler(sys.stdout)  # Explicitly use stdout
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

# Add queue handler for WebSocket
root_logger.addHandler(log_handler)

# Also configure specific module loggers to ensure they use our handlers
for module_name in ['my_framework', 'my_framework.agents', 'my_framework.tools']:
    module_logger = logging.getLogger(module_name)
    module_logger.setLevel(logging.INFO)
    module_logger.propagate = True  # Ensure propagation to root logger

# Active WebSocket connections list
active_connections: list[WebSocket] = []
connections_lock = threading.Lock()  # Thread-safe access to connections list

async def log_sender():
    """Background task to send logs to WebSocket clients."""
    logging.info("Log sender task started")
    
    while True:
        try:
            # Process all available log messages
            messages_to_send = []
            while not log_queue.empty() and len(messages_to_send) < 10:
                try:
                    msg = log_queue.get_nowait()
                    messages_to_send.append(msg)
                except queue.Empty:
                    break
            
            # Send messages to all connected clients
            if messages_to_send and active_connections:
                with connections_lock:
                    disconnected = []
                    for connection in active_connections[:]:  # Work on a copy
                        try:
                            for msg in messages_to_send:
                                await connection.send_text(msg)
                        except Exception as e:
                            # Mark connection for removal
                            disconnected.append(connection)
                            logging.debug(f"WebSocket connection lost: {e}")
                    
                    # Remove disconnected clients
                    for conn in disconnected:
                        if conn in active_connections:
                            active_connections.remove(conn)
                            logging.info(f"Removed disconnected WebSocket client. Active connections: {len(active_connections)}")
            
            # Small delay to prevent CPU spinning
            await asyncio.sleep(0.05)
            
        except Exception as e:
            logging.error(f"Error in log_sender: {e}", exc_info=True)
            await asyncio.sleep(0.1)

# --- App Setup ---
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), 'templates'))
app = FastAPI(title="AI Journalist Bot v2.0 - Digital Newsroom", version="2.0")

# Global flag for style guru update status
style_guru_updating = False

@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup."""
    # Start log sender task
    asyncio.create_task(log_sender())
    logging.info("=" * 70)
    logging.info("APPLICATION STARTUP COMPLETE")
    logging.info("=" * 70)
    logging.info("Server is ready to accept connections")
    
    # Check if style framework exists
    if os.path.exists("intellinews_style_framework.json"):
        logging.info("✅ Style Guru framework detected - iterative mode enabled")
    else:
        logging.warning("⚠️ Style Guru framework not found - run setup or use the UI to create it")

# --- Improved WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    await websocket.accept()
    
    with connections_lock:
        active_connections.append(websocket)
    
    logging.info(f"New WebSocket connection established. Total connections: {len(active_connections)}")
    
    # Send initial message to confirm connection
    try:
        await websocket.send_text("Connected to log stream")
    except Exception as e:
        logging.error(f"Failed to send initial message: {e}")
    
    try:
        # Keep connection alive and handle messages
        while True:
            # Wait for any message from client (ping/pong or actual messages)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Could handle client messages here if needed
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send a ping to check if connection is still alive
                try:
                    await websocket.send_text("ping")
                except:
                    break
                    
    except WebSocketDisconnect:
        logging.info("WebSocket client disconnected normally")
    except Exception as e:
        logging.debug(f"WebSocket error: {e}")
    finally:
        with connections_lock:
            if websocket in active_connections:
                active_connections.remove(websocket)
        logging.info(f"WebSocket connection closed. Active connections: {len(active_connections)}")

# --- Test Logging Endpoint ---
@app.get("/test-logging")
async def test_logging():
    """Test endpoint to verify logging is working."""
    logging.info("=" * 50)
    logging.info("TEST LOG MESSAGE - INFO LEVEL")
    logging.warning("TEST LOG MESSAGE - WARNING LEVEL")
    logging.error("TEST LOG MESSAGE - ERROR LEVEL")
    logging.info("=" * 50)
    
    # Also test module-specific logging
    module_logger = logging.getLogger("my_framework.agents")
    module_logger.info("Test message from my_framework.agents logger")
    
    return JSONResponse({
        "message": "Test log messages sent",
        "active_connections": len(active_connections),
        "queue_size": log_queue.qsize()
    })

# --- Debug Info Endpoint ---
@app.get("/debug-info")
async def debug_info():
    """Get debug information about the logging system."""
    return JSONResponse({
        "active_websocket_connections": len(active_connections),
        "log_queue_size": log_queue.qsize(),
        "root_logger_level": logging.getLevelName(root_logger.level),
        "root_logger_handlers": [type(h).__name__ for h in root_logger.handlers],
        "style_guru_available": STYLE_GURU_AVAILABLE
    })
