import os
import sys
import shutil
import json
import uuid
import time
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

from smartbusiners.core.config import (
    config_manager, SmartBusinersConfig, 
    CONFIG_DIR, COMMANDS_FILE, PROMPTS_FILE, SPRINTS_FILE, COST_FILE, EXECUTIONS_DIR
)
from smartbusiners.core.auth import auth_manager
from smartbusiners.core.tools import default_registry
from smartbusiners.core.session import Session
from smartbusiners.core.engine import SmartBusinersEngine

app = FastAPI(title="SmartBusiners AI Panel", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# Cross-Platform Native Terminal Launcher
# -------------------------------------------------------------
def open_native_terminal(shell_cmd: str, cwd: Optional[str] = None) -> bool:
    """Abre uma nova janela de terminal nativa rodando o comando especificado."""
    work_dir = cwd or config_manager.config.workspace
    
    if sys.platform == "win32":
        # Windows: Windows Terminal ou CMD
        pause_cmd = f'{shell_cmd} & echo. & pause'
        wt = shutil.which("wt") or shutil.which("wt.exe")
        try:
            if wt:
                subprocess.Popen(
                    [wt, "-d", work_dir, "cmd.exe", "/k", pause_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                subprocess.Popen(
                    ["cmd.exe", "/k", pause_cmd],
                    cwd=work_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            return True
        except Exception as e:
            print(f"Erro ao abrir terminal Windows: {e}")
            return False

    elif sys.platform == "darwin":
        # macOS: Terminal.app
        escaped = shell_cmd.replace("\\", "\\\\").replace('"', '\\"')
        try:
            subprocess.Popen(
                ["osascript", "-e", f'tell application "Terminal" to do script "cd {work_dir} && {escaped}"'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            print(f"Erro ao abrir terminal macOS: {e}")
            return False

    else:
        # Linux: gnome-terminal ou xterm
        wrapped = f'cd {work_dir} && {shell_cmd}; echo ""; echo "Pressione qualquer tecla para fechar..."; read -n1'
        gnome = shutil.which("gnome-terminal")
        if gnome:
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", wrapped], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        xterm = shutil.which("xterm")
        if xterm:
            subprocess.Popen(["xterm", "-e", f"bash -c '{wrapped}'"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        return False

# -------------------------------------------------------------
# Background Process / Executions Manager
# -------------------------------------------------------------
class ExecutionProcess:
    def __init__(self, exec_id: str, title: str, command: str, prompt: str):
        self.exec_id = exec_id
        self.title = title
        self.command = command
        self.prompt = prompt
        self.status = "running" # running, done, error, stopped
        self.created_at = datetime.now().isoformat()
        self.finished_at = None
        self.logs: List[str] = []
        self.process: Optional[subprocess.Popen] = None

    def add_log(self, text: str):
        self.logs.append(text)
        # Salva log em disco
        log_file = EXECUTIONS_DIR / f"{self.exec_id}.log"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception:
            pass

active_executions: Dict[str, ExecutionProcess] = {}

# -------------------------------------------------------------
# Data Persistence Helpers
# -------------------------------------------------------------
def load_json_file(path: Path, default_data):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_data
    return default_data

def save_json_file(path: Path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------
@app.get("/api/status")
async def get_status():
    auth_info = auth_manager.get_status()
    cfg = config_manager.config
    return {
        "status": "online",
        "auth": auth_info,
        "config": cfg.model_dump(),
        "available_models": auth_manager.AVAILABLE_MODELS
    }

@app.post("/api/auth")
async def set_auth(data: Dict[str, Any]):
    api_key = data.get("api_key", "").strip()
    val = auth_manager.validate_key(api_key)
    if val["valid"]:
        config_manager.update_key(api_key)
        return {"success": True, "message": "Chave Google validada e salva!", "details": val}
    else:
        return JSONResponse(status_code=400, content={"success": False, "error": val.get("error"), "details": val.get("details")})

@app.get("/api/config")
async def get_config():
    return config_manager.config.model_dump()

@app.post("/api/config")
async def update_config(data: Dict[str, Any]):
    cfg = config_manager.config
    if "default_model" in data: cfg.default_model = data["default_model"]
    if "temperature" in data: cfg.temperature = float(data["temperature"])
    if "action_mode" in data: cfg.action_mode = data["action_mode"]
    if "workspace" in data: cfg.workspace = data["workspace"]
    if "enabled_tools" in data: cfg.enabled_tools = data["enabled_tools"]
    config_manager.save_config(cfg)
    return {"success": True, "config": cfg.model_dump()}

# Terminal Launcher Endpoint
@app.post("/api/terminal/open")
async def api_open_terminal(data: Dict[str, Any]):
    cmd = data.get("command", "smartbusiners chat")
    cwd = data.get("workspace") or config_manager.config.workspace
    success = open_native_terminal(cmd, cwd=cwd)
    return {"success": success, "command": cmd, "workspace": cwd}

# Commands Endpoints
@app.get("/api/commands")
async def get_commands():
    default_commands = [
        {"id": "cmd-audit", "name": "Auditoria de Código", "desc": "Analisa o código em busca de bugs e segurança", "cmd": 'smartbusiners run "Faça uma auditoria de código detalhada no projeto"'},
        {"id": "cmd-tests", "name": "Gerar Testes Unitários", "desc": "Cria testes automatizados para os módulos", "cmd": 'smartbusiners run "Crie testes unitários abrangentes para o projeto"'},
        {"id": "cmd-chat", "name": "Iniciar Chat no Terminal", "desc": "Abre o terminal interativo no workspace", "cmd": "smartbusiners chat"},
        {"id": "cmd-arch", "name": "Mapear Arquitetura", "desc": "Gera documentação técnica e diagrama da estrutura", "cmd": 'smartbusiners run "Mapeie a arquitetura do projeto e crie um resumo técnico"'},
    ]
    return load_json_file(COMMANDS_FILE, default_commands)

@app.post("/api/commands")
async def save_command(data: Dict[str, Any]):
    cmds = load_json_file(COMMANDS_FILE, [])
    if "id" not in data or not data["id"]:
        data["id"] = f"cmd-{str(uuid.uuid4())[:6]}"
    # Atualiza ou adiciona
    cmds = [c for c in cmds if c.get("id") != data["id"]]
    cmds.append(data)
    save_json_file(COMMANDS_FILE, cmds)
    return {"success": True, "commands": cmds}

@app.delete("/api/commands/{cmd_id}")
async def delete_command(cmd_id: str):
    cmds = load_json_file(COMMANDS_FILE, [])
    cmds = [c for c in cmds if c.get("id") != cmd_id]
    save_json_file(COMMANDS_FILE, cmds)
    return {"success": True}

# Prompts Endpoints
@app.get("/api/prompts")
async def get_prompts():
    default_prompts = [
        {"id": "p-senior-dev", "name": "Desenvolvedor Sênior Fullstack", "desc": "Foco em código limpo, arquitetura sólida e testes", "template": "Atue como um Engenheiro de Software Sênior. Priorize boas práticas, type hints e código modular."},
        {"id": "p-code-reviewer", "name": "Revisor de Código & Segurança", "desc": "Auditoria estrita de vulnerabilidades e performance", "template": "Revise o código identificando falhas de segurança OWASP, gargalos de memória e melhorias de legibilidade."},
        {"id": "p-biz-analyst", "name": "Arquiteto de Soluções & Negócios", "desc": "Planejamento estratégico e modelagem de sistemas", "template": "Atue como Arquiteto de Negócios e Soluções. Estruture o plano passo a passo com critérios de aceite."},
    ]
    return load_json_file(PROMPTS_FILE, default_prompts)

@app.post("/api/prompts")
async def save_prompt(data: Dict[str, Any]):
    prompts = load_json_file(PROMPTS_FILE, [])
    if "id" not in data or not data["id"]:
        data["id"] = f"p-{str(uuid.uuid4())[:6]}"
    prompts = [p for p in prompts if p.get("id") != data["id"]]
    prompts.append(data)
    save_json_file(PROMPTS_FILE, prompts)
    return {"success": True, "prompts": prompts}

@app.delete("/api/prompts/{p_id}")
async def delete_prompt(p_id: str):
    prompts = load_json_file(PROMPTS_FILE, [])
    prompts = [p for p in prompts if p.get("id") != p_id]
    save_json_file(PROMPTS_FILE, prompts)
    return {"success": True}

# Sprints / Kanban Tasks Endpoints
@app.get("/api/sprints")
async def get_sprints():
    default_sprints = [
        {"id": "task-1", "title": "[SETUP] Configurar Chave Google", "desc": "Adicionar API Key do Google AI Studio para ativar o motor", "status": "done", "priority": "high"},
        {"id": "task-2", "title": "[DEV] Integrar CLI com Interface Web", "desc": "Permitir execução e monitoramento de comandos em tempo real", "status": "in_progress", "priority": "high"},
        {"id": "task-3", "title": "[TEST] Validar Execução Autônoma", "desc": "Testar tool calling e criação de arquivos no workspace", "status": "open", "priority": "normal"},
    ]
    return load_json_file(SPRINTS_FILE, default_sprints)

@app.post("/api/sprints")
async def save_sprint_task(data: Dict[str, Any]):
    tasks = load_json_file(SPRINTS_FILE, [])
    if "id" not in data or not data["id"]:
        data["id"] = f"task-{str(uuid.uuid4())[:6]}"
    tasks = [t for t in tasks if t.get("id") != data["id"]]
    tasks.append(data)
    save_json_file(SPRINTS_FILE, tasks)
    return {"success": True, "tasks": tasks}

@app.delete("/api/sprints/{task_id}")
async def delete_sprint_task(task_id: str):
    tasks = load_json_file(SPRINTS_FILE, [])
    tasks = [t for t in tasks if t.get("id") != task_id]
    save_json_file(SPRINTS_FILE, tasks)
    return {"success": True}

# Executions Endpoints
@app.get("/api/executions")
async def get_executions():
    exec_list = []
    # Carrega ativas
    for e in active_executions.values():
        exec_list.append({
            "id": e.exec_id,
            "title": e.title,
            "command": e.command,
            "prompt": e.prompt,
            "status": e.status,
            "created_at": e.created_at,
            "finished_at": e.finished_at
        })
    # Carrega históricas salvas em disco
    for log_file in EXECUTIONS_DIR.glob("*.json"):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                if not any(x["id"] == d.get("id") for x in exec_list):
                    exec_list.append(d)
        except Exception:
            pass
    return sorted(exec_list, key=lambda x: x.get("created_at", ""), reverse=True)

@app.get("/api/executions/{exec_id}/logs")
async def get_execution_logs(exec_id: str):
    if exec_id in active_executions:
        return {"id": exec_id, "logs": active_executions[exec_id].logs, "status": active_executions[exec_id].status}
    log_file = EXECUTIONS_DIR / f"{exec_id}.log"
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines()]
        return {"id": exec_id, "logs": lines, "status": "done"}
    return {"id": exec_id, "logs": [], "status": "not_found"}

@app.post("/api/executions/start")
async def start_execution(data: Dict[str, Any]):
    prompt = data.get("prompt", "").strip()
    cmd = data.get("command") or f'smartbusiners run "{prompt}"'
    exec_id = f"exec-{str(uuid.uuid4())[:8]}"
    title = data.get("title") or (prompt[:30] + "..." if len(prompt) > 30 else prompt) or "Execução de Comando"

    ep = ExecutionProcess(exec_id=exec_id, title=title, command=cmd, prompt=prompt)
    active_executions[exec_id] = ep

    # Dispara em background via SmartBusinersEngine ou subprocess
    def _run_bg():
        ep.add_log(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando execução: {cmd}")
        try:
            cwd = data.get("workspace") or config_manager.config.workspace
            # Executa com Python
            proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", cmd] if os.name == 'nt' else ["bash", "-c", cmd],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )
            ep.process = proc
            for line in iter(proc.stdout.readline, ""):
                if line:
                    ep.add_log(line.strip())
            proc.stdout.close()
            proc.wait()
            ep.status = "done" if proc.returncode == 0 else "error"
            ep.add_log(f"[{datetime.now().strftime('%H:%M:%S')}] Processo finalizado com código {proc.returncode}")
        except Exception as err:
            ep.status = "error"
            ep.add_log(f"Erro na execução: {err}")
        finally:
            ep.finished_at = datetime.now().isoformat()
            # Salva metadados
            save_json_file(EXECUTIONS_DIR / f"{exec_id}.json", {
                "id": exec_id, "title": ep.title, "command": ep.command,
                "prompt": ep.prompt, "status": ep.status,
                "created_at": ep.created_at, "finished_at": ep.finished_at
            })

    threading.Thread(target=_run_bg, daemon=True).start()
    return {"success": True, "execution_id": exec_id}

@app.post("/api/executions/{exec_id}/stop")
async def stop_execution(exec_id: str):
    if exec_id in active_executions:
        ep = active_executions[exec_id]
        if ep.process and ep.process.poll() is None:
            ep.process.terminate()
            ep.status = "stopped"
            ep.add_log(f"[{datetime.now().strftime('%H:%M:%S')}] Execução interrompida pelo usuário.")
            return {"success": True, "message": "Execução interrompida."}
    return {"success": False, "message": "Execução não está em andamento."}

# Context Store & Workspace Files
@app.get("/api/workspace/files")
async def get_workspace_files(path: str = "."):
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

# Cost / Quota Monitor
@app.get("/api/cost/summary")
async def get_cost_summary():
    default_cost = {
        "today_requests": 14,
        "today_tokens": 28400,
        "today_estimated_cost_usd": 0.0042,
        "month_requests": 182,
        "month_tokens": 420500,
        "month_estimated_cost_usd": 0.063,
        "quota_status": "OK (Google AI Studio Free Tier / Pay-as-you-go)",
        "models_usage": [
            {"model": "gemini-3.7-flash", "requests": 12, "tokens": 24200, "cost": 0.0036},
            {"model": "gemini-3.5-flash", "requests": 2, "tokens": 4200, "cost": 0.0006},
        ]
    }
    return load_json_file(COST_FILE, default_cost)

# WebSocket Realtime Agent Endpoint
@app.websocket("/ws/agent")
async def websocket_agent_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            action = data.get("action")

            if action == "run":
                prompt = data.get("prompt", "")
                ws = data.get("workspace") or config_manager.config.workspace
                model = data.get("model") or config_manager.config.default_model
                temp = data.get("temperature", config_manager.config.temperature)
                session_id = data.get("session_id")

                session = Session.load(session_id) if session_id else Session()
                engine = SmartBusinersEngine(workspace=ws, model=model, temperature=temp)

                def ws_cb(ev_type: str, ev_data: dict):
                    asyncio.create_task(websocket.send_text(json.dumps({
                        "type": ev_type, "data": ev_data
                    })))

                try:
                    await websocket.send_text(json.dumps({
                        "type": "start",
                        "data": {"session_id": session.session_id, "prompt": prompt}
                    }))
                    await engine.execute_task(prompt=prompt, session=session, callback=ws_cb)
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": {"message": str(e)}
                    }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error: {e}")

# Mount Static Files
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

def start_gui(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True):
    if open_browser:
        def _open():
            time.sleep(1.0)
            import webbrowser
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="info")

def main():
    start_gui()

if __name__ == "__main__":
    main()
