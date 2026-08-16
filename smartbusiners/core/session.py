import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from smartbusiners.core.config import SESSIONS_DIR

class SessionMessage:
    def __init__(self, role: str, content: str, thoughts: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None):
        self.role = role
        self.content = content
        self.thoughts = thoughts
        self.tool_calls = tool_calls or []
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "thoughts": self.thoughts,
            "tool_calls": self.tool_calls,
            "timestamp": self.timestamp
        }

class Session:
    def __init__(self, session_id: Optional[str] = None, title: str = "Nova Conversa"):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.title = title
        self.created_at = time.time()
        self.updated_at = time.time()
        self.messages: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str, thoughts: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None):
        msg = SessionMessage(role, content, thoughts, tool_calls)
        self.messages.append(msg.to_dict())
        self.updated_at = time.time()
        if len(self.messages) == 1 and role == "user":
            self.title = (content[:35] + "...") if len(content) > 35 else content

    def save(self):
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        session_file = SESSIONS_DIR / f"{self.session_id}.json"
        data = {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": self.messages
        }
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, session_id: str) -> Optional['Session']:
        session_file = SESSIONS_DIR / f"{session_id}.json"
        if not session_file.exists():
            return None
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            s = cls(session_id=data["session_id"], title=data.get("title", "Conversa"))
            s.created_at = data.get("created_at", time.time())
            s.updated_at = data.get("updated_at", time.time())
            s.messages = data.get("messages", [])
            return s
        except Exception:
            return None

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        results = []
        for file in sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append({
                    "session_id": data.get("session_id", file.stem),
                    "title": data.get("title", "Sem título"),
                    "created_at": data.get("created_at", file.stat().st_ctime),
                    "updated_at": data.get("updated_at", file.stat().st_mtime),
                    "message_count": len(data.get("messages", []))
                })
            except Exception:
                pass
        return results
