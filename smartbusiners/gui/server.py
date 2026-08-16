import os
import json
import asyncio
import webbrowser
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

from smartbusiners.core.config import config_manager, SmartBusinersConfig
from smartbusiners.core.auth import auth_manager
from smartbusiners.core.tools import default_registry
from smartbusiners.core.session import Session
from smartbusiners.core.engine import SmartBusinersEngine

app = FastAPI(title="SmartBusiners AI Dashboard", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

class AuthRequest(BaseModel):
    api_key: str

class ConfigUpdateRequest(BaseModel):
    default_model: Optional[str] = None
    temperature: Optional[float] = None
    workspace: Optional[str] = None
    enabled_tools: Optional[List[str]] = None

@app.get("/api/status")
async def get_status():
    auth_info = auth_manager.get_status()
    cfg = config_manager.config
    return {
        "status": "online",
        "auth": auth_info,
        "config": {
            "model": cfg.default_model,
            "temperature": cfg.temperature,
            "workspace": cfg.workspace,
            "enabled_tools": cfg.enabled_tools,
        }
    }

@app.post("/api/auth")
async def set_auth(data: AuthRequest):
    val = auth_manager.validate_key(data.api_key)
    if val["valid"]:
        config_manager.update_key(data.api_key)
        return {"success": True, "message": "Chave Google validada e salva com sucesso!", "details": val}
    else:
        return JSONResponse(status_code=400, content={"success": False, "error": val["error"], "details": val.get("details")})

@app.get("/api/config")
async def get_config():
    return config_manager.config.model_dump()

@app.post("/api/config")
async def update_config(data: ConfigUpdateRequest):
    cfg = config_manager.config
    if data.default_model is not None:
        cfg.default_model = data.default_model
    if data.temperature is not None:
        cfg.temperature = data.temperature
    if data.workspace is not None:
        cfg.workspace = data.workspace
    if data.enabled_tools is not None:
        cfg.enabled_tools = data.enabled_tools
    config_manager.save_config(cfg)
    return {"success": True, "config": cfg.model_dump()}

@app.get("/api/tools")
async def get_tools():
    tools = default_registry.get_all()
    return [{
        "name": t.name,
        "description": t.description,
        "parameters": t.parameters
    } for t in tools]

@app.get("/api/sessions")
async def list_sessions():
    return Session.list_all()

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    s = Session.load(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return {
        "session_id": s.session_id,
        "title": s.title,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
        "messages": s.messages
    }

@app.get("/api/workspace/files")
async def list_workspace_files(path: str = "."):
    ws = Path(config_manager.config.workspace)
    target = ws / path if not Path(path).is_absolute() else Path(path)
    if not target.exists():
        return {"error": "Caminho não encontrado", "files": []}
    
    items = []
    try:
        for entry in sorted(target.iterdir()):
            if entry.name.startswith(".") or entry.name in ["__pycache__", "node_modules", "venv", ".venv"]:
                continue
            items.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else 0,
                "path": str(entry.relative_to(ws))
            })
    except Exception as e:
        return {"error": str(e), "files": []}
    return {"workspace": str(ws), "files": items}

@app.websocket("/ws/agent")
async def websocket_agent_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            action = data.get("action")

            if action == "run":
                prompt = data.get("prompt", "")
                ws = data.get("workspace") or config_manager.config.workspace
                model = data.get("model") or config_manager.config.default_model
                temp = data.get("temperature", config_manager.config.temperature)
                session_id = data.get("session_id")

                session = Session.load(session_id) if session_id else Session()
                engine = SmartBusinersEngine(workspace=ws, model=model, temperature=temp)

                # Callback para despachar eventos via WebSocket
                def ws_callback(event_type: str, event_data: dict):
                    asyncio.create_task(websocket.send_text(json.dumps({
                        "type": event_type,
                        "data": event_data
                    })))

                try:
                    await websocket.send_text(json.dumps({
                        "type": "start",
                        "data": {"session_id": session.session_id, "prompt": prompt}
                    }))
                    
                    full_res = await engine.execute_task(
                        prompt=prompt,
                        session=session,
                        callback=ws_callback
                    )
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": {"message": str(e)}
                    }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")

# Serve arquivos estáticos
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

def start_gui(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True):
    if open_browser:
        def _open():
            import time
            time.sleep(1.0)
            webbrowser.open(f"http://{host}:{port}")
        import threading
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="info")

def main():
    start_gui()

if __name__ == "__main__":
    main()
