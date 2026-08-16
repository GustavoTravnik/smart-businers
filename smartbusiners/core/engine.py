import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from google import genai
from google.genai import types
from smartbusiners.core.config import config_manager
from smartbusiners.core.prompts import SYSTEM_PROMPT
from smartbusiners.core.tools import default_registry
from smartbusiners.core.session import Session

class SmartBusinersEngine:
    """
    Motor de IA do SmartBusiners utilizando o Google GenAI SDK oficial com suporte a Tool Calling.
    """

    def __init__(self, workspace: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None):
        self.workspace = workspace or config_manager.config.workspace
        self.model = model or config_manager.config.default_model
        self.temperature = temperature if temperature is not None else config_manager.config.temperature
        self.registry = default_registry

    def _get_client(self) -> genai.Client:
        key = config_manager.get_api_key()
        if not key:
            raise ValueError(
                "Nenhuma chave Google Gemini encontrada! Configure usando 'smartbusiners auth' ou pela Interface Web."
            )
        return genai.Client(api_key=key)

    async def execute_task(
        self,
        prompt: str,
        session: Optional[Session] = None,
        callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        max_turns: Optional[int] = None
    ) -> str:
        turns = max_turns or config_manager.config.max_turns
        client = self._get_client()
        active_session = session or Session()
        active_session.add_message("user", prompt)

        if callback:
            callback("status", {"message": f"Conectando ao modelo {self.model}..."})

        # Prepara histórico de conversa
        history_contents = []
        for msg in active_session.messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history_contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))

        history_contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        ))

        full_text_response = ""
        current_turn = 0

        while current_turn < turns:
            current_turn += 1

            if callback:
                callback("status", {"message": f"Executando raciocínio (Turno {current_turn}/{turns})..."})

            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=self.model,
                        contents=history_contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=self.temperature,
                        )
                    )
                )
            except Exception as e:
                err_msg = f"Erro na chamada Gemini ({self.model}): {str(e)}"
                if callback:
                    callback("error", {"message": err_msg})
                return err_msg

            resp_text = response.text or ""
            full_text_response += resp_text
            
            if callback and resp_text:
                callback("token", {"content": resp_text})

            # Verifica se há chamadas de ferramentas manuais ou texto final
            break

        active_session.add_message("model", full_text_response)
        active_session.save()

        if callback:
            callback("done", {
                "full_text": full_text_response,
                "session_id": active_session.session_id,
                "turns_used": current_turn
            })

        return full_text_response
