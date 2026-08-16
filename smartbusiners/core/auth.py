import requests
from typing import Dict, Any, Optional
from smartbusiners.core.config import config_manager

class AuthManager:
    """Gerencia validação de contas Google e chaves de API (BYOK - Bring Your Own Key)."""

    AVAILABLE_MODELS = [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "description": "Ultrarrápido, ideal para código e automação ágil", "recommended": True},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "description": "Raciocínio complexo e engenharia de software avançada", "recommended": False},
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "description": "Alta performance e latência reduzida", "recommended": False},
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

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "").replace("models/", "") for m in data.get("models", [])]
                return {
                    "valid": True,
                    "message": "Conexão com a Google API efetuada com sucesso!",
                    "models_count": len(models),
                    "sample_models": models[:6]
                }
            elif resp.status_code == 400:
                return {
                    "valid": False,
                    "error": "Chave inválida ou malformada.",
                    "details": resp.json().get("error", {}).get("message", "API Key inválida.")
                }
            elif resp.status_code == 403:
                return {
                    "valid": False,
                    "error": "Permissão negada ou cota excedida na conta Google.",
                    "details": resp.json().get("error", {}).get("message", "Verifique o plano ou cota no Google Cloud Console.")
                }
            else:
                return {
                    "valid": False,
                    "error": f"Erro HTTP {resp.status_code} ao consultar Google API.",
                    "details": resp.text
                }
        except requests.exceptions.RequestException as e:
            return {
                "valid": False,
                "error": "Falha de conexão com os servidores da Google.",
                "details": str(e)
            }

auth_manager = AuthManager()
