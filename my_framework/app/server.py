# File: my_framework/app/server.py

import sys
import os
import threading
import json
import logging
import queue
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, Request, BackgroundTasks
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

# Try to import style guru components
try:
    from my_framework.style_guru.training import build_dataset, train_model
    from my_framework.style_guru.deep_analyzer import deep_style_analysis
    STYLE_GURU_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Style Guru components not available: {e}")
    STYLE_GURU_AVAILABLE = False

# --- Logging Setup ---
# This queue will hold all log messages
log_queue = queue.Queue()

class QueueLogHandler(logging.Handler):
    """A custom logging handler that puts logs into a queue."""
    def __init__(self, q):
        super().__init__()
        self.queue = q

    def emit(self, record):
        # We format the record here before putting it in the queue
        self.queue.put(self.format(record))

# Configure the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Clear existing handlers to prevent duplicate logs
if logger.hasHandlers():
    logger.handlers.clear()

# Add a console handler to see logs in the terminal
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Add our custom queue handler
queue_handler = QueueLogHandler(log_queue)
queue_handler.setFormatter(formatter)
logger.addHandler(queue_handler)

active_connections: list[WebSocket] = []

async def log_sender():
    """Monitors the log queue and sends new logs to all connected WebSockets."""
    while True:
        try:
            # Use asyncio.to_thread to safely get from the blocking queue
            log_entry = await asyncio.to_thread(log_queue.get)
            # Send the log to all connected clients
            for connection in active_connections:
                await connection.send_text(log_entry)
            log_queue.task_done()
        except queue.Empty:
            await asyncio.sleep(0.1) # Wait a bit if the queue is empty
        except Exception as e:
            # Use the root logger to log errors in the sender itself
            logging.error(f"Error in log_sender: {e}")

# --- App Setup ---
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), 'templates'))
app = FastAPI(title="AI Journalist Bot v2.0 - Digital Newsroom", version="2.0")

# --- Orchestrator Workflow ---
def orchestrator_workflow(config_data: dict):
    """
    This function runs in a separate thread and executes the main agent workflow.
    Crucially, it uses the globally configured logger.
    """
    try:
        logging.info("=" * 70)
        logging.info("🚀 ORCHESTRATOR WORKFLOW THREAD STARTING")
        logging.info(f"User Goal: {config_data.get('user_goal', 'N/A')}")
        logging.info(f"Source URL: {config_data.get('source_url', 'N/A')}")
        
        llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=config_data.get('openai_api_key'))
        
        use_style_guru = config_data.get('use_style_guru', True)
        orchestrator = OrchestratorAgent(llm=llm, use_style_guru=use_style_guru)
        
        user_goal = config_data.get("user_goal", "No goal provided.")
        initial_context = {**config_data, "input": user_goal}
        
        final_result = orchestrator.invoke(initial_context)
        
        logging.info("=" * 70)
        logging.info(f"✅ WORKFLOW COMPLETE. Final Result: {final_result}")
        logging.info("=" * 70)
        
    except Exception as e:
        logging.error(f"🔥 Orchestrator workflow failed: {e}", exc_info=True)

@app.post("/invoke", summary="Run the multi-agent journalist workflow")
async def invoke_run(request: dict):
    config_data = request.get("input", {})
    
    logging.info("=" * 70)
    logging.info("API /invoke REQUEST RECEIVED")
    logging.info(f"Payload: {json.dumps(config_data, indent=2)}")
    
    # The key is that the new thread will use the same logger configuration
    thread = threading.Thread(target=orchestrator_workflow, args=(config_data,))
    thread.daemon = True
    thread.name = f"Orchestrator-{config_data.get('username', 'user')}"
    thread.start()
    
    logging.info(f"Started orchestrator in background thread: {thread.name}")
    logging.info("=" * 70)
    
    return {"output": "Orchestrator process started. Monitor the UI or console for live logs."}


# --- FastAPI Event Handlers & Other Routes ---

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(log_sender())
    logging.info("Application startup complete. WebSocket log sender is running.")
    if os.path.exists("intellinews_style_framework.json"):
        logging.info("✅ Style Guru framework detected.")
    else:
        logging.warning("⚠️ Style Guru framework not found.")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logging.info(f"New WebSocket connection from: {websocket.client.host}")
    try:
        while True:
            # This loop keeps the connection alive
            await websocket.receive_text()
    except Exception:
        logging.info(f"WebSocket connection closed for: {websocket.client.host}")
        active_connections.remove(websocket)

# [ ... All your other endpoints like /rewrite, /update-style-guru, etc., remain unchanged ... ]
# --- Style Guru Update Endpoint ---
def update_style_guru_background(num_articles: int = 100):
    """Background task to update the style guru framework."""
    global style_guru_updating
    style_guru_updating = True
    
    if not STYLE_GURU_AVAILABLE:
        logging.error("❌ Style Guru components not available!")
        style_guru_updating = False
        return
    
    try:
        logging.info(f"🎨 Starting Style Guru update with {num_articles} articles...")
        
        # Step 1: Deep analysis
        logging.info("[1/3] Running deep analysis...")
        framework = deep_style_analysis(max_articles=num_articles)
        
        if not framework:
            logging.error("❌ Deep analysis failed!")
            style_guru_updating = False
            return
        
        logging.info("✅ Deep analysis complete!")
        
        # Step 2: Build dataset
        logging.info("[2/3] Building training dataset...")
        build_dataset(limit=num_articles)
        logging.info("✅ Dataset built!")
        
        # Step 3: Train model
        logging.info("[3/3] Training neural scorer...")
        train_model()
        logging.info("✅ Model trained!")
        
        logging.info("🎉 Style Guru update complete! Framework is now active.")
        
    except Exception as e:
        logging.error(f"🔥 Style Guru update failed: {e}", exc_info=True)
    finally:
        style_guru_updating = False

@app.post("/update-style-guru")
async def update_style_guru(background_tasks: BackgroundTasks, num_articles: int = 100):
    """
    Triggers the Style Guru framework update.
    This will analyze articles and train the scorer.
    """
    global style_guru_updating
    
    if not STYLE_GURU_AVAILABLE:
        raise HTTPException(status_code=501, detail="Style Guru components not installed")
    
    if style_guru_updating:
        raise HTTPException(status_code=409, detail="Style Guru update already in progress")
    
    logging.info(f"🎨 Style Guru update requested with {num_articles} articles")
    background_tasks.add_task(update_style_guru_background, num_articles)
    
    return JSONResponse({
        "output": f"Style Guru update started with {num_articles} articles. This will take 15-30 minutes. Monitor logs for progress.",
        "status": "started"
    })

@app.get("/style-guru-status")
async def style_guru_status():
    """Check the status of the Style Guru system."""
    framework_path = os.path.join(framework_dir, "intellinews_style_framework.json")
    framework_exists = os.path.exists(framework_path)
    
    status = {
        "framework_exists": framework_exists,
        "updating": style_guru_updating,
        "status": "updating" if style_guru_updating else ("active" if framework_exists else "not_configured"),
        "style_guru_available": STYLE_GURU_AVAILABLE
    }
    
    if framework_exists:
        try:
            with open(framework_path, "r") as f:
                framework = json.load(f)
                status["articles_analyzed"] = framework.get("articles_analyzed", "unknown")
                status["version"] = framework.get("version", "unknown")
        except:
            pass
    
    return JSONResponse(status)

# --- Style Guru Admin Endpoint ---
@app.get("/style-guru", response_class=HTMLResponse)
async def style_guru_admin(request: Request):
    """Admin page for Style Guru management."""
    framework_path = os.path.join(framework_dir, "intellinews_style_framework.json")
    framework_exists = os.path.exists(framework_path)
    
    framework_info = {
        "exists": framework_exists,
        "articles_analyzed": "N/A",
        "version": "N/A",
        "last_updated": "Never"
    }
    
    if framework_exists:
        try:
            with open(framework_path, "r") as f:
                framework = json.load(f)
                framework_info["articles_analyzed"] = framework.get("articles_analyzed", "unknown")
                framework_info["version"] = framework.get("version", "unknown")
            
            # Get file modification time
            import datetime
            mtime = os.path.getmtime(framework_path)
            framework_info["last_updated"] = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logging.error(f"Error reading framework: {e}")
    
    return templates.TemplateResponse("styleguru.html", {
        "request": request,
        "framework_info": framework_info,
        "updating": style_guru_updating
    })

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    """Simple test page to debug issues"""
    return templates.TemplateResponse("test.html", {"request": request})

@app.get("/websocket-test", response_class=HTMLResponse)
async def websocket_test_page(request: Request):
    """Serves the new websocket test page"""
    return templates.TemplateResponse("websocket_test.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    # Use reload=True for easier development
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)