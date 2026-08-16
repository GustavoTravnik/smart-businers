import os
import subprocess
import fnmatch
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

class ToolDefinition:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], func: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    def to_gemini_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any]):
        def decorator(func: Callable):
            tool_def = ToolDefinition(name, description, parameters, func)
            self._tools[name] = tool_def
            return func
        return decorator

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def get_all(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def get_declarations(self, enabled_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        declarations = []
        for name, tool in self._tools.items():
            if enabled_names is None or name in enabled_names:
                declarations.append(tool.to_gemini_declaration())
        return declarations

    def execute(self, name: str, args: Dict[str, Any], workspace: Optional[str] = None) -> Dict[str, Any]:
        tool = self.get(name)
        if not tool:
            return {"success": False, "error": f"Ferramenta '{name}' não encontrada."}
        try:
            # Injeta workspace se aplicável
            if "workspace" in tool.func.__code__.co_varnames and "workspace" not in args:
                args["workspace"] = workspace or os.getcwd()
            result = tool.func(**args)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

default_registry = ToolRegistry()

# -------------------------------------------------------------
# Ferramentas Nativas
# -------------------------------------------------------------

@default_registry.register(
    name="run_command",
    description="Executa um comando no terminal (PowerShell no Windows / Bash no Unix) dentro do workspace.",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "O comando de linha de comando a ser executado."
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Tempo limite em segundos para execução (padrão: 60)."
            }
        },
        "required": ["command"]
    }
)
def run_command(command: str, timeout_seconds: int = 60, workspace: Optional[str] = None) -> str:
    cwd = workspace or os.getcwd()
    try:
        is_win = os.name == 'nt'
        shell_cmd = ["powershell", "-NoProfile", "-Command", command] if is_win else command
        process = subprocess.run(
            shell_cmd,
            cwd=cwd,
            shell=not is_win,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            encoding='utf-8',
            errors='replace'
        )
        output = process.stdout
        if process.stderr:
            output += f"\n[STDERR]:\n{process.stderr}"
        if process.returncode != 0:
            output += f"\n[Código de saída: {process.returncode}]"
        return output.strip() if output.strip() else "(Comando executado com sucesso sem saída de texto)"
    except subprocess.TimeoutExpired:
        return f"Erro: O comando atingiu o tempo limite de {timeout_seconds} segundos."
    except Exception as e:
        return f"Erro ao executar comando: {str(e)}"

@default_registry.register(
    name="read_file",
    description="Lê o conteúdo de um arquivo do disco com opção de paginação por linhas.",
    parameters={
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Caminho relativo ao workspace ou caminho absoluto do arquivo."
            },
            "start_line": {
                "type": "integer",
                "description": "Linha inicial para leitura (1-indexada, opcional)."
            },
            "end_line": {
                "type": "integer",
                "description": "Linha final para leitura (opcional)."
            }
        },
        "required": ["filepath"]
    }
)
def read_file(filepath: str, start_line: Optional[int] = None, end_line: Optional[int] = None, workspace: Optional[str] = None) -> str:
    cwd = Path(workspace or os.getcwd())
    p = Path(filepath)
    if not p.is_absolute():
        p = cwd / p

    if not p.exists():
        return f"Erro: O arquivo '{filepath}' não existe."
    if p.is_dir():
        return f"Erro: '{filepath}' é um diretório, use list_directory."

    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        s = (start_line - 1) if start_line and start_line > 0 else 0
        e = end_line if end_line and end_line <= total_lines else total_lines
        
        selected = lines[s:e]
        numbered = [f"{i + s + 1}: {line}" for i, line in enumerate(selected)]
        header = f"--- Arquivo: {p.name} (Linhas {s+1} a {min(e, total_lines)} de {total_lines}) ---\n"
        return header + "".join(numbered)
    except Exception as e:
        return f"Erro ao ler arquivo: {str(e)}"

@default_registry.register(
    name="write_file",
    description="Cria ou sobrescreve um arquivo no disco com o conteúdo fornecido.",
    parameters={
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Caminho relativo ao workspace ou absoluto do arquivo."
            },
            "content": {
                "type": "string",
                "description": "O conteúdo textual a ser gravado no arquivo."
            },
            "overwrite": {
                "type": "boolean",
                "description": "Permitir sobrescrever se o arquivo já existir (padrão: true)."
            }
        },
        "required": ["filepath", "content"]
    }
)
def write_file(filepath: str, content: str, overwrite: bool = True, workspace: Optional[str] = None) -> str:
    cwd = Path(workspace or os.getcwd())
    p = Path(filepath)
    if not p.is_absolute():
        p = cwd / p

    if p.exists() and not overwrite:
        return f"Erro: O arquivo '{filepath}' já existe e overwrite=False."

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Arquivo '{p.name}' gravado com sucesso ({len(content)} caracteres)."
    except Exception as e:
        return f"Erro ao gravar arquivo: {str(e)}"

@default_registry.register(
    name="list_directory",
    description="Lista arquivos e pastas dentro de um diretório.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Caminho da pasta a listar (relativo ao workspace ou absoluto, padrão: '.')."
            },
            "recursive": {
                "type": "boolean",
                "description": "Se deve listar subdiretórios recursivamente (padrão: false)."
            },
            "max_depth": {
                "type": "integer",
                "description": "Profundidade máxima de recursão (padrão: 2)."
            }
        }
    }
)
def list_directory(path: str = ".", recursive: bool = False, max_depth: int = 2, workspace: Optional[str] = None) -> str:
    cwd = Path(workspace or os.getcwd())
    p = Path(path)
    if not p.is_absolute():
        p = cwd / p

    if not p.exists():
        return f"Erro: O diretório '{path}' não existe."
    if not p.is_dir():
        return f"Erro: '{path}' é um arquivo, não um diretório."

    try:
        items = []
        base_depth = len(p.parts)

        if recursive:
            for root, dirs, files in os.walk(p):
                cur_depth = len(Path(root).parts) - base_depth
                if cur_depth >= max_depth:
                    dirs.clear()
                    continue
                # Filtra pastas ocultas / caches
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["__pycache__", "node_modules", "venv", ".venv"]]
                rel_root = Path(root).relative_to(p)
                for d in dirs:
                    items.append(f"[DIR]  {rel_root / d}")
                for f in files:
                    if not f.startswith("."):
                        items.append(f"[FILE] {rel_root / f}")
        else:
            for entry in sorted(p.iterdir()):
                if entry.name.startswith(".") or entry.name in ["__pycache__", "node_modules", "venv", ".venv"]:
                    continue
                kind = "[DIR] " if entry.is_dir() else "[FILE]"
                size_str = f" ({entry.stat().st_size} bytes)" if entry.is_file() else ""
                items.append(f"{kind} {entry.name}{size_str}")

        return f"Conteúdo de '{p}':\n" + ("\n".join(items) if items else "(Diretório vazio)")
    except Exception as e:
        return f"Erro ao listar diretório: {str(e)}"

@default_registry.register(
    name="search_files",
    description="Procura por texto ou padrão regex dentro dos arquivos do workspace.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Texto ou padrão a ser buscado."
            },
            "file_glob": {
                "type": "string",
                "description": "Filtro de arquivos (ex: '*.py', '*.js', padrão: '*')."
            },
            "max_results": {
                "type": "integer",
                "description": "Número máximo de correspondências retornadas (padrão: 30)."
            }
        },
        "required": ["pattern"]
    }
)
def search_files(pattern: str, file_glob: str = "*", max_results: int = 30, workspace: Optional[str] = None) -> str:
    cwd = Path(workspace or os.getcwd())
    matches = []
    
    try:
        for root, dirs, files in os.walk(cwd):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["__pycache__", "node_modules", "venv", ".venv"]]
            for filename in files:
                if fnmatch.fnmatch(filename, file_glob):
                    filepath = Path(root) / filename
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, 1):
                                if pattern.lower() in line.lower():
                                    rel_path = filepath.relative_to(cwd)
                                    matches.append(f"{rel_path}:{line_num}: {line.strip()}")
                                    if len(matches) >= max_results:
                                        return f"Resultados para '{pattern}' (limite de {max_results} atingido):\n" + "\n".join(matches)
                    except Exception:
                        pass
        return f"Resultados para '{pattern}' ({len(matches)} encontrados):\n" + ("\n".join(matches) if matches else "(Nenhum resultado)")
    except Exception as e:
        return f"Erro na busca: {str(e)}"

@default_registry.register(
    name="get_workspace_info",
    description="Obtém informações do sistema operacional, workspace ativo e status do Git.",
    parameters={
        "type": "object",
        "properties": {}
    }
)
def get_workspace_info(workspace: Optional[str] = None) -> str:
    cwd = Path(workspace or os.getcwd())
    info = [
        f"Workspace Path: {cwd}",
        f"Sistema Operacional: {os.name} ({subprocess.os.sys.platform})",
    ]
    git_dir = cwd / ".git"
    if git_dir.exists():
        info.append("Repositório Git: Detectado")
        try:
            branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=cwd, text=True, errors="ignore").strip()
            info.append(f"Git Branch Atual: {branch or 'main'}")
        except Exception:
            pass
    else:
        info.append("Repositório Git: Não inicializado")

    return "\n".join(info)
