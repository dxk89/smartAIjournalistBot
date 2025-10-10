# File: my_framework/app/server.py

import sys
import os
import threading
import json
import asyncio
import queue
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
from my_framework.agents.loggerbot import LoggerBot, log_queue

# --- Style Guru Imports ---
style_guru_import_error = None
try:
    from my_framework.style_guru.training import build_dataset, train_model
    STYLE_GURU_AVAILABLE = True
except ImportError as e:
    STYLE_GURU_AVAILABLE = False
    style_guru_import_error = e


logger = LoggerBot.get_logger()
active_connections: list[WebSocket] = []
style_guru_updating = False

async def log_sender():
    """Monitors the log queue and sends new logs to all connected WebSockets."""
    while True:
        try:
            log_entry = await asyncio.to_thread(log_queue.get)
            for connection in active_connections:
                await connection.send_text(log_entry)
            log_queue.task_done()
        except queue.Empty:
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in log_sender: {e}")

# --- App Setup ---
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), 'templates'))
app = FastAPI(title="AI Journalist Bot v2.0 - Digital Newsroom", version="2.0")

# --- Orchestrator Workflow ---
def orchestrator_workflow(config_data: dict):
    """
    This function runs in a separate thread and executes the main agent workflow.
    """
    try:
        logger.info("=" * 70)
        logger.info("🚀 ORCHESTRATOR WORKFLOW THREAD STARTING")
        logger.info(f"User Goal: {config_data.get('user_goal', 'N/A')}")
        logger.info(f"Source URL: {config_data.get('source_url', 'N/A')}")
        # FIX: Log the received username to verify it's coming from the UI
        logger.info(f"CMS Username received: '{config_data.get('username', 'NOT PROVIDED')}'")


        llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=config_data.get('openai_api_key'))
        
        use_style_guru = config_data.get('use_style_guru', True)
        orchestrator = OrchestratorAgent(llm=llm, use_style_guru=use_style_guru, logger=logger)
        
        # Prepare the initial context for the orchestrator
        user_goal = config_data.get("user_goal", "No goal provided.")
        initial_context = {
            "input": user_goal,
            "source_url": config_data.get("source_url"),
            "source_content": config_data.get("source_content"),
            "username": config_data.get("username"),
            "password": config_data.get("password"),
            "cms_login_url": config_data.get("cms_login_url"),
            "cms_create_article_url": config_data.get("cms_create_article_url"),
            "publication_ids": config_data.get("publication_ids", [])
        }
        
        final_result = orchestrator.invoke(initial_context)
        
        logger.info("=" * 70)
        logger.info(f"✅ WORKFLOW COMPLETE. Final Result: {final_result}")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.critical(f"🔥 Orchestrator workflow failed: {e}", exc_info=True)

@app.post("/invoke", summary="Run the multi-agent journalist workflow")
async def invoke_run(request: dict):
    config_data = request.get("input", {})
    
    logger.info("=" * 70)
    logger.info("API /invoke REQUEST RECEIVED")
    logger.info(f"Payload: {json.dumps(config_data, indent=2)}")
    
    thread = threading.Thread(target=orchestrator_workflow, args=(config_data,))
    thread.daemon = True
    thread.name = f"Orchestrator-{config_data.get('username', 'user')}"
    thread.start()
    
    logger.info(f"Started orchestrator in background thread: {thread.name}")
    logger.info("=" * 70)
    
    return {"output": "Orchestrator process started. Monitor the UI or console for live logs."}


# --- NEW: Rewrite Endpoint ---
@app.post("/rewrite", summary="Rewrite an article from a URL")
async def rewrite_article(request: dict):
    """
    This endpoint handles rewriting an article from a URL without publishing.
    """
    config_data = request.get("input", {})
    source_url = config_data.get("source_url")
    api_key = config_data.get("openai_api_key")

    if not source_url or not api_key:
        raise HTTPException(status_code=400, detail="Source URL and OpenAI API key are required.")

    logger.info("=" * 70)
    logger.info("API /rewrite REQUEST RECEIVED")
    logger.info(f"Source URL: {source_url}")
    logger.info("=" * 70)

    try:
        # Since rewrite_only is synchronous, we run it in a thread
        def run_rewrite():
            llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=api_key)
            orchestrator = OrchestratorAgent(llm=llm, use_style_guru=True, logger=logger)
            return orchestrator.rewrite_only({"source_url": source_url})

        result = await asyncio.to_thread(run_rewrite)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
            
        return result

    except Exception as e:
        logger.critical(f"🔥 Rewrite workflow failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
        
# --- FastAPI Event Handlers & Other Routes ---

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(log_sender())
    logger.info("Application startup complete. WebSocket log sender is running.")
    if os.path.exists("intellinews_style_framework.json"):
        logger.info("✅ Style Guru framework detected.")
    else:
        logger.warning("⚠️ Style Guru framework not found.")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"New WebSocket connection from: {websocket.client.host}")
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        logger.info(f"WebSocket connection closed for: {websocket.client.host}")
        active_connections.remove(websocket)

# --- Style Guru Update Endpoint ---
def update_style_guru_background(num_articles: int = 100):
    """Background task to update the style guru framework."""
    global style_guru_updating
    style_guru_updating = True
    
    try:
        from my_framework.style_guru.deep_analyzer import deep_style_analysis
        
        logger.info(f"🎨 Starting Style Guru update with {num_articles} articles...")
        
        logger.info("[1/3] Running deep analysis...")
        framework = deep_style_analysis(max_articles=num_articles)
        
        if not framework:
            logger.error("❌ Deep analysis failed!")
            style_guru_updating = False
            return
        
        logger.info("✅ Deep analysis complete!")
        
        logger.info("[2/3] Building training dataset...")
        build_dataset(limit=num_articles)
        logger.info("✅ Dataset built!")
        
        logger.info("[3/3] Training neural scorer...")
        train_model()
        logger.info("✅ Model trained!")
        
        logger.info("🎉 Style Guru update complete! Framework is now active.")
        
    except ImportError as e:
        logger.critical(f"🔥 Style Guru update failed on import: {e}", exc_info=True)
    except Exception as e:
        logger.critical(f"🔥 Style Guru update failed: {e}", exc_info=True)
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
        logger.error(f"Style Guru components not installed. Import error: {style_guru_import_error}")
        raise HTTPException(status_code=501, detail=f"Style Guru components not installed. Import error: {style_guru_import_error}")

    if style_guru_updating:
        raise HTTPException(status_code=409, detail="Style Guru update already in progress")
    
    logger.info(f"🎨 Style Guru update requested with {num_articles} articles")
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
            with open(framework_path, "r", encoding="utf-8") as f:
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
            with open(framework_path, "r", encoding="utf-8") as f:
                framework = json.load(f)
                framework_info["articles_analyzed"] = framework.get("articles_analyzed", "unknown")
                framework_info["version"] = framework.get("version", "unknown")
            
            import datetime
            mtime = os.path.getmtime(framework_path)
            framework_info["last_updated"] = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(f"Error reading framework: {e}")
    
    return templates.TemplateResponse("style-guru.html", {
        "request": request,
        "framework_info": framework_info,
        "updating": style_guru_updating
    })

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "framework_info": {},
        "updating": False
    })

@app.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    """Simple test page to debug issues"""
    return templates.TemplateResponse("test.html", {"request": request})

@app.get("/websocket-test", response_class=HTMLResponse)
async def websocket_test_page(request: Request):
    """Serves the new websocket test page"""
    return templates.TemplateResponse("websocket-test.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)