import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Carrega variáveis de ambiente de um arquivo .env se existir
load_dotenv()

CONFIG_DIR = Path.home() / ".smartbusiners"
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSIONS_DIR = CONFIG_DIR / "sessions"

class SmartBusinersConfig(BaseModel):
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API Key")
    google_cloud_project: Optional[str] = Field(default=None, description="Google Cloud Project ID")
    default_model: str = Field(default="gemini-2.5-flash", description="Default Gemini Model")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Model Temperature")
    max_turns: int = Field(default=15, ge=1, le=50, description="Max agent turns per run")
    workspace: str = Field(default_factory=lambda: str(Path.cwd()), description="Active workspace path")
    enabled_tools: List[str] = Field(
        default=["run_command", "read_file", "write_file", "list_directory", "search_files", "get_workspace_info"],
        description="Active agent tools"
    )
    auto_approve_tools: bool = Field(default=False, description="Auto-approve safe tool executions")
    gui_host: str = Field(default="127.0.0.1", description="GUI Host")
    gui_port: int = Field(default=8080, description="GUI Port")

class ConfigManager:
    """Gerencia configurações persistentes do SmartBusiners em ~/.smartbusiners/config.json."""

    def __init__(self):
        self._ensure_dirs()
        self.config = self.load_config()

    def _ensure_dirs(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> SmartBusinersConfig:
        data: Dict[str, Any] = {}
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        # Prioridade para variáveis de ambiente
        env_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if env_key:
            data["gemini_api_key"] = env_key

        if os.getenv("SMARTBUSINERS_DEFAULT_MODEL"):
            data["default_model"] = os.getenv("SMARTBUSINERS_DEFAULT_MODEL")

        if os.getenv("SMARTBUSINERS_WORKSPACE"):
            data["workspace"] = os.getenv("SMARTBUSINERS_WORKSPACE")

        if os.getenv("SMARTBUSINERS_HOST"):
            data["gui_host"] = os.getenv("SMARTBUSINERS_HOST")

        if os.getenv("SMARTBUSINERS_PORT"):
            try:
                data["gui_port"] = int(os.getenv("SMARTBUSINERS_PORT"))
            except ValueError:
                pass

        try:
            return SmartBusinersConfig(**data)
        except Exception:
            return SmartBusinersConfig()

    def save_config(self, config: Optional[SmartBusinersConfig] = None) -> bool:
        if config:
            self.config = config
        self._ensure_dirs()
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config.model_dump(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erro ao salvar configuração: {e}")
            return False

    def update_key(self, api_key: str) -> bool:
        self.config.gemini_api_key = api_key.strip()
        return self.save_config()

    def get_api_key(self) -> Optional[str]:
        return self.config.gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

config_manager = ConfigManager()
