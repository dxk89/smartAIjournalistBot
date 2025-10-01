import sys
import os
import threading
import json
import logging
import queue
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# --- Path Setup & Environment Loading ---
# The PYTHONPATH is now correctly set by the 'run_local_server.bat' script.
# This code robustly locates and loads the .env file.
app_dir = os.path.dirname(__file__)
framework_dir = os.path.abspath(os.path.join(app_dir, '..'))
dotenv_path = os.path.join(framework_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Core Imports ---
# These imports will now work correctly thanks to the updated startup script.
from my_framework.models.openai import ChatOpenAI
from my_framework.agents.orchestrator import OrchestratorAgent
from my_framework.style_guru.training import build_dataset, train_model

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

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(log_sender())
    logging.info("Application startup complete.")

# --- Orchestrator Workflow ---
def orchestrator_workflow(config_data: dict):
    logging.info("--- 🚀 Starting Orchestrator Workflow ---")
    llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=config_data.get('openai_api_key'))
    orchestrator = OrchestratorAgent(llm=llm)
    user_goal = config_data.get("user_goal", "No goal provided.")
    initial_context = {**config_data, "input": user_goal}
    try:
        final_result = orchestrator.invoke(initial_context)
        logging.info(f"✅ Final Result: {final_result}")
    except Exception as e:
        logging.error(f"🔥 Orchestrator workflow failed: {e}", exc_info=True)
    logging.info("\n--- ✅✅✅ Orchestrator Workflow Finished ✅✅✅ ---")

@app.post("/invoke", summary="Run the multi-agent journalist workflow")
async def invoke_run(request: dict):
    config_data = request.get("input", {})
    logging.info("API: Received request. Starting orchestrator in a background thread.")
    thread = threading.Thread(target=orchestrator_workflow, args=(config_data,))
    thread.daemon = True
    thread.start()
    return {"output": "Orchestrator process started. Monitor logs for progress."}

# --- Style Guru Endpoint ---
@app.post("/update-style-model")
async def update_style_model():
    """
    Triggers the dataset building and model training process for the Style Guru.
    """
    try:
        logging.info("--- Starting Style Guru Model Update ---")
        build_dataset()
        train_model()
        logging.info("--- Style Guru Model Update Complete ---")
        return {"output": "Style Guru model updated successfully."}
    except Exception as e:
        logging.error(f"--- Style Guru Model Update Failed: {e} ---")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        active_connections.remove(websocket)