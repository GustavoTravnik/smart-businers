import os
import json
import asyncio
import requests
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
from smartbusiners.core.config import config_manager
from smartbusiners.core.prompts import SYSTEM_PROMPT
from smartbusiners.core.tools import default_registry
from smartbusiners.core.session import Session

class SmartBusinersEngine:
    """
    Motor de IA Agentic do SmartBusiners.
    Conecta diretamente com a API do Google Gemini (REST / GenAI SDK) com streaming,
    gerenciamento de ferramentas (Tool Calling) e suporte multi-turn autônomo.
    """

    def __init__(self, workspace: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None):
        self.workspace = workspace or config_manager.config.workspace
        self.model = model or config_manager.config.default_model
        self.temperature = temperature if temperature is not None else config_manager.config.temperature
        self.registry = default_registry

    def _get_api_key(self) -> str:
        key = config_manager.get_api_key()
        if not key:
            raise ValueError(
                "Nenhuma chave Google Gemini encontrada! Configure usando 'smartbusiners auth' ou pela Interface Web."
            )
        return key

    async def execute_task(
        self,
        prompt: str,
        session: Optional[Session] = None,
        callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        max_turns: Optional[int] = None
    ) -> str:
        """
        Executa uma tarefa autônoma com tool calling loop e streaming de eventos.
        Emite eventos: 'thought', 'tool_call', 'tool_result', 'token', 'done', 'error'.
        """
        turns = max_turns or config_manager.config.max_turns
        api_key = self._get_api_key()
        active_session = session or Session()
        
        # Constrói histórico de mensagens para a API Gemini
        contents: List[Dict[str, Any]] = []
        
        for msg in active_session.messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        # Adiciona mensagem do usuário atual
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })
        active_session.add_message("user", prompt)

        # Prepara ferramentas habilitadas
        enabled_tools = config_manager.config.enabled_tools
        tool_declarations = self.registry.get_declarations(enabled_tools)
        tools_payload = [{"function_declarations": tool_declarations}] if tool_declarations else []

        full_text_response = ""
        current_thought = ""
        current_turn = 0

        while current_turn < turns:
            current_turn += 1
            
            payload = {
                "contents": contents,
                "system_instruction": {
                    "parts": [{"text": SYSTEM_PROMPT}]
                },
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": 8192
                }
            }
            if tools_payload:
                payload["tools"] = tools_payload

            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={api_key}"
            
            if callback:
                callback("status", {"message": f"Consultando {self.model} (Turno {current_turn}/{turns})..."})

            # Chamada assíncrona HTTP
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=120)
                )
            except Exception as e:
                err_msg = f"Erro de conexão com Google Gemini: {str(e)}"
                if callback:
                    callback("error", {"message": err_msg})
                return err_msg

            if response.status_code != 200:
                err_text = response.text
                err_msg = f"Google API Error ({response.status_code}): {err_text}"
                if callback:
                    callback("error", {"message": err_msg})
                return err_msg

            res_json = response.json()
            candidates = res_json.get("candidates", [])
            if not candidates:
                err_msg = "Google Gemini retornou resposta vazia."
                if callback:
                    callback("error", {"message": err_msg})
                return err_msg

            candidate = candidates[0]
            content_obj = candidate.get("content", {})
            parts = content_obj.get("parts", [])

            # Análise das partes (texto ou chamadas de função)
            tool_calls_to_execute = []
            turn_text = ""

            for part in parts:
                if "text" in part:
                    text_chunk = part["text"]
                    turn_text += text_chunk
                    full_text_response += text_chunk
                    if callback:
                        callback("token", {"content": text_chunk})
                
                if "functionCall" in part:
                    fn_call = part["functionCall"]
                    fn_name = fn_call.get("name")
                    fn_args = fn_call.get("args", {})
                    tool_calls_to_execute.append((fn_name, fn_args))

            # Adiciona resposta do modelo ao histórico
            contents.append(content_obj)

            # Se não houver chamadas de função, terminamos a execução
            if not tool_calls_to_execute:
                break

            # Executa ferramentas
            function_response_parts = []
            for fn_name, fn_args in tool_calls_to_execute:
                if callback:
                    callback("tool_call", {"tool": fn_name, "args": fn_args})

                # Execução no workspace
                exec_result = self.registry.execute(fn_name, fn_args, workspace=self.workspace)
                res_output = exec_result.get("result") if exec_result.get("success") else f"Erro: {exec_result.get('error')}"

                if callback:
                    callback("tool_result", {"tool": fn_name, "output": str(res_output)[:2000]})

                function_response_parts.append({
                    "functionResponse": {
                        "name": fn_name,
                        "response": {
                            "name": fn_name,
                            "content": res_output
                        }
                    }
                })

            # Adiciona retorno das funções ao contexto para o próximo turno
            contents.append({
                "role": "user",
                "parts": function_response_parts
            })

        active_session.add_message("model", full_text_response)
        active_session.save()

        if callback:
            callback("done", {
                "full_text": full_text_response,
                "session_id": active_session.session_id,
                "turns_used": current_turn
            })

        return full_text_response
