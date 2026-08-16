import requests
from typing import Dict, Any, Optional
from smartbusiners.core.config import config_manager
from google import genai

class AuthManager:
    """Gerencia validação de contas Google e chaves de API (BYOK)."""

    AVAILABLE_MODELS = [
        {"id": "gemini-3.7-flash", "name": "Gemini 3.7 Flash", "description": "Modelo de última geração com alta velocidade e raciocínio avançado", "recommended": True},
        {"id": "gemini-3.5-flash", "name": "Gemini 3.5 Flash", "description": "Alta performance para tarefas de codificação e automação", "recommended": False},
        {"id": "gemini-flash-latest", "name": "Gemini Flash Latest", "description": "Aponta sempre para a versão estável mais recente do Gemini Flash", "recommended": False},
        {"id": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro Preview", "description": "Raciocínio analítico e arquitetural profundo", "recommended": False},
    ]

    def get_status(self) -> Dict[str, Any]:
        api_key = config_manager.get_api_key()
        if not api_key:
            return {
                "authenticated": False,
                "message": "Nenhuma chave Google Gemini configurada. Obtenha uma no Google AI Studio (https://aistudio.google.com/).",
                "masked_key": None,
                "models": self.AVAILABLE_MODELS
            }
        
        masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
        return {
            "authenticated": True,
            "message": "Chave Google configurada e pronta para uso.",
            "masked_key": masked,
            "models": self.AVAILABLE_MODELS
        }

    def validate_key(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        key = api_key or config_manager.get_api_key()
        if not key:
            return {
                "valid": False,
                "error": "Chave não fornecida.",
                "details": "Você precisa de uma chave Google Gemini para conectar o SmartBusiners."
            }

        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-3.7-flash",
                contents="ping"
            )
            return {
                "valid": True,
                "message": "Conexão com a Google Gemini API validada com sucesso!",
                "models": [m["id"] for m in self.AVAILABLE_MODELS],
                "sample_output": response.text.strip()
            }
        except Exception as e:
            # Fallback para verificar endpoint REST de modelos
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    return {
                        "valid": True,
                        "message": "Chave Google ativa!",
                        "models": [m["id"] for m in self.AVAILABLE_MODELS]
                    }
                else:
                    return {
                        "valid": False,
                        "error": "Chave inválida ou cota excedida na conta Google.",
                        "details": resp.text
                    }
            except Exception as ex:
                return {
                    "valid": False,
                    "error": "Falha de conexão com os servidores da Google.",
                    "details": str(e)
                }

auth_manager = AuthManager()
