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

# Try to import style guru components (they might not exist yet)
try:
    from my_framework.style_guru.training import build_dataset, train_model
    from my_framework.style_guru.deep_analyzer import deep_style_analysis
    STYLE_GURU_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Style Guru components not available: {e}")
    STYLE_GURU_AVAILABLE = False

# --- Logging Setup ---
class QueueLogHandler(logging.Handler):
    def __init__(self, q):
        super().__init__()
        self.queue = q

    def emit(self, record):
        self.queue.put(self.format(record))

log_queue = queue.Queue()
log_handler = QueueLogHandler(log_queue)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

active_connections: list[WebSocket] = []

async def log_sender():
    while True:
        try:
            log_entry = log_queue.get_nowait()
            for connection in active_connections:
                await connection.send_text(log_entry)
        except queue.Empty:
            await asyncio.sleep(0.1)

# --- App Setup ---
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), 'templates'))
app = FastAPI(title="AI Journalist Bot v2.0 - Digital Newsroom", version="2.0")

# Global flag for style guru update status
style_guru_updating = False

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(log_sender())
    logging.info("Application startup complete.")
    
    # Check if style framework exists
    if os.path.exists("intellinews_style_framework.json"):
        logging.info("✅ Style Guru framework detected - iterative mode enabled")
    else:
        logging.warning("⚠️ Style Guru framework not found - run setup or use the UI to create it")

# --- Orchestrator Workflow ---
def orchestrator_workflow(config_data: dict):
    logging.info("=" * 70)
    logging.info("🚀 ORCHESTRATOR WORKFLOW STARTING")
    logging.info("=" * 70)
    logging.info(f"User Goal: {config_data.get('user_goal', 'N/A')}")
    logging.info(f"Source URL: {config_data.get('source_url', 'N/A')}")
    logging.info(f"Username: {config_data.get('username', 'N/A')}")
    logging.info("=" * 70)
    
    llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=config_data.get('openai_api_key'))
    
    # Check if user wants to disable style guru for this run
    use_style_guru = config_data.get('use_style_guru', True)
    
    orchestrator = OrchestratorAgent(llm=llm, use_style_guru=use_style_guru)
    user_goal = config_data.get("user_goal", "No goal provided.")
    initial_context = {**config_data, "input": user_goal}
    
    try:
        final_result = orchestrator.invoke(initial_context)
        logging.info("=" * 70)
        logging.info(f"✅ WORKFLOW COMPLETE")
        logging.info("=" * 70)
    except Exception as e:
        logging.error(f"🔥 Orchestrator workflow failed: {e}", exc_info=True)

@app.post("/invoke", summary="Run the multi-agent journalist workflow")
async def invoke_run(request: dict):
    config_data = request.get("input", {})
    
    # Log what we received
    logging.info("=" * 70)
    logging.info("API REQUEST RECEIVED")
    logging.info("=" * 70)
    logging.info(f"Full request data: {json.dumps(config_data, indent=2)}")
    logging.info("=" * 70)
    
    thread = threading.Thread(target=orchestrator_workflow, args=(config_data,))
    thread.daemon = True
    thread.start()
    
    return {"output": "Orchestrator process started. Monitor logs for progress."}

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
    return """<!DOCTYPE html>
<html>
<head>
    <title>Simple Test</title>
    <style>
        body { font-family: Arial; padding: 20px; background: #1a1a1a; color: white; }
        button { padding: 10px 20px; font-size: 16px; margin: 10px; cursor: pointer; }
        #output { background: #2a2a2a; padding: 20px; margin-top: 20px; border: 1px solid #444; max-height: 400px; overflow-y: auto; }
        .success { color: #0f0; }
        .error { color: #f00; }
    </style>
</head>
<body>
    <h1>System Test Page</h1>
    <p><a href="/" style="color: #4a9eff;">← Back to Main</a></p>
    
    <h2>1. Test WebSocket</h2>
    <button onclick="testWebSocket()">Test WebSocket Connection</button>
    <div id="ws-status"></div>
    
    <h2>2. Test API Status</h2>
    <button onclick="testStatus()">Check Status</button>
    <div id="status-result"></div>
    
    <h2>Live Logs</h2>
    <div id="output"></div>
    
    <script>
        let ws = null;
        
        function log(message, isError = false) {
            const output = document.getElementById('output');
            const div = document.createElement('div');
            div.className = isError ? 'error' : 'success';
            div.textContent = new Date().toLocaleTimeString() + ' - ' + message;
            output.appendChild(div);
            output.scrollTop = output.scrollHeight;
        }
        
        function testWebSocket() {
            const statusDiv = document.getElementById('ws-status');
            statusDiv.innerHTML = 'Connecting...';
            
            try {
                ws = new WebSocket('ws://' + window.location.host + '/ws');
                
                ws.onopen = () => {
                    statusDiv.innerHTML = '<span class="success">✓ WebSocket CONNECTED!</span>';
                    log('WebSocket connected successfully');
                };
                
                ws.onerror = (error) => {
                    statusDiv.innerHTML = '<span class="error">✗ WebSocket ERROR</span>';
                    log('WebSocket error: ' + error, true);
                };
                
                ws.onmessage = (event) => {
                    log('Received: ' + event.data);
                };
                
                ws.onclose = () => {
                    log('WebSocket closed');
                };
            } catch (error) {
                statusDiv.innerHTML = '<span class="error">✗ Exception: ' + error.message + '</span>';
                log('Exception: ' + error.message, true);
            }
        }
        
        async function testStatus() {
            const statusDiv = document.getElementById('status-result');
            statusDiv.innerHTML = 'Checking...';
            
            try {
                const response = await fetch('/style-guru-status');
                const data = await response.json();
                statusDiv.innerHTML = '<pre class="success">' + JSON.stringify(data, null, 2) + '</pre>';
                log('Status check successful');
            } catch (error) {
                statusDiv.innerHTML = '<span class="error">✗ Error: ' + error.message + '</span>';
                log('Status check failed: ' + error.message, true);
            }
        }
        
        window.onload = () => {
            log('Page loaded. Click "Test WebSocket" to start.');
        };
    </script>
</body>
</html>"""

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        active_connections.remove(websocket)