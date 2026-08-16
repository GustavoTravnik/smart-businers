import asyncio
import os
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

# Garante UTF-8 no Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ["PYTHONIOENCODING"] = "utf-8"

from smartbusiners.core.config import config_manager
from smartbusiners.core.auth import auth_manager
from smartbusiners.core.tools import default_registry
from smartbusiners.core.engine import SmartBusinersEngine
from smartbusiners.core.session import Session
from smartbusiners.utils.formatters import format_banner, format_tools_table
from smartbusiners.utils.logger import log_info, log_success, log_warning, log_error

app = typer.Typer(
    name="smartbusiners",
    help="SmartBusiners - Sistema de IA CLI & Web Dashboard baseado em Google Gemini e Antigravity",
    add_completion=False
)
console = Console(legacy_windows=False)

@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(format_banner())
        console.print("[yellow]Utilize [bold]smartbusiners --help[/bold] para visualizar todos os comandos disponíveis.[/yellow]")
        console.print("[dim]Exemplos rápidos:[/dim]")
        console.print("  [cyan]smartbusiners chat[/cyan]          -> Inicia chat interativo no terminal")
        console.print("  [cyan]smartbusiners run \"prompt\"[/cyan]   -> Executa uma instrução autônoma")
        console.print("  [cyan]smartbusiners gui[/cyan]           -> Inicia a interface gráfica web")
        console.print("  [cyan]smartbusiners auth[/cyan]          -> Configura sua chave Google Gemini")

@app.command(name="chat", help="Inicia uma sessão interativa de chat e automação no terminal.")
def chat(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Modelo Gemini a ser usado"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Diretório de trabalho")
):
    console.print(format_banner())
    
    # Verifica chave Google
    auth_status = auth_manager.get_status()
    if not auth_status["authenticated"]:
        log_warning("Nenhuma chave Google configurada.")
        if Confirm.ask("Deseja inserir sua chave Google Gemini agora?"):
            key = Prompt.ask("[bold cyan]Cole sua API Key do Google AI Studio[/bold cyan]", password=True)
            if key:
                config_manager.update_key(key)
                log_success("Chave salva com sucesso!")
        else:
            log_error("Não é possível continuar sem chave Google.")
            raise typer.Exit(code=1)

    ws = workspace or config_manager.config.workspace
    mdl = model or config_manager.config.default_model

    console.print(Panel(
        f"[bold]Workspace:[/bold] [green]{ws}[/green]\n"
        f"[bold]Modelo:[/bold] [cyan]{mdl}[/cyan]\n"
        f"[dim]Digite 'sair' ou 'exit' para encerrar. Digite 'clear' para limpar a tela.[/dim]",
        title="Sessão Interativa Iniciada",
        border_style="cyan"
    ))

    engine = SmartBusinersEngine(workspace=ws, model=mdl)
    session = Session()

    def stream_callback(event_type: str, data: dict):
        if event_type == "tool_call":
            console.print(f"\n[bold yellow]Executando Ferramenta:[/bold yellow] [bold cyan]{data['tool']}[/bold cyan]")
            console.print(f"[dim]Argumentos: {data['args']}[/dim]")
        elif event_type == "tool_result":
            out_preview = str(data['output'])
            if len(out_preview) > 300:
                out_preview = out_preview[:300] + "... [truncado]"
            console.print(f"[bold green]Resultado:[/bold green] [dim]{out_preview}[/dim]\n")
        elif event_type == "error":
            console.print(f"[bold red]Erro:[/bold red] {data['message']}")

    while True:
        try:
            user_input = Prompt.ask(f"\n[bold green]SmartBusiners[/bold green] [dim]({Path(ws).name})[/dim] >")
            if not user_input.strip():
                continue
            if user_input.strip().lower() in ["sair", "exit", "quit"]:
                console.print("[cyan]Sessão encerrada. Até logo![/cyan]")
                break
            if user_input.strip().lower() == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                continue

            with console.status("[bold cyan]SmartBusiners pensando e executando...[/bold cyan]", spinner="dots"):
                response_text = asyncio.run(engine.execute_task(user_input, session=session, callback=stream_callback))

            console.print("\n[bold cyan]Resposta:[/bold cyan]")
            console.print(Markdown(response_text))

        except KeyboardInterrupt:
            console.print("\n[yellow]Operação cancelada pelo usuário.[/yellow]")
            break
        except Exception as e:
            log_error(f"Erro na execução: {e}")

@app.command(name="run", help="Executa uma instrução autônoma diretamente no terminal.")
def run_task(
    prompt: str = typer.Argument(..., help="Instrução para o SmartBusiners executar"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Diretório de trabalho"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Modelo Gemini a ser usado")
):
    ws = workspace or config_manager.config.workspace
    mdl = model or config_manager.config.default_model

    engine = SmartBusinersEngine(workspace=ws, model=mdl)
    
    def cli_callback(event_type: str, data: dict):
        if event_type == "tool_call":
            console.print(f"[yellow][Tool][/yellow] [cyan]{data['tool']}[/cyan] -> [dim]{data['args']}[/dim]")
        elif event_type == "tool_result":
            console.print(f"[green][Result][/green] [dim]{str(data['output'])[:150]}[/dim]")
        elif event_type == "error":
            console.print(f"[red][Error][/red] {data['message']}")

    with console.status("[bold cyan]Processando tarefa autônoma...[/bold cyan]", spinner="bouncingBar"):
        result = asyncio.run(engine.execute_task(prompt, callback=cli_callback))

    console.print("\n" + "="*60)
    console.print(Markdown(result))
    console.print("="*60)

@app.command(name="auth", help="Configura e valida a chave de API da Google (BYOK).")
def auth(
    test: bool = typer.Option(False, "--test", "-t", help="Testar a chave atual"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="Definir nova API Key")
):
    console.print(format_banner())
    if key:
        config_manager.update_key(key)
        log_success("Chave de API salva com sucesso.")
        test = True

    if test or not key:
        status = auth_manager.get_status()
        if not status["authenticated"]:
            log_warning("Nenhuma chave Google configurada.")
            new_key = Prompt.ask("[bold cyan]Cole sua API Key do Google AI Studio[/bold cyan]", password=True)
            if new_key:
                config_manager.update_key(new_key)
                status = auth_manager.get_status()
            else:
                return

        console.print(f"[bold]Chave Atual:[/bold] [cyan]{status['masked_key']}[/cyan]")
        with console.status("[bold cyan]Validando chave junto à Google API...[/bold cyan]", spinner="dots"):
            val = auth_manager.validate_key()

        if val["valid"]:
            log_success(f"{val['message']} ({val['models_count']} modelos disponíveis)")
        else:
            log_error(f"{val['error']} - {val.get('details', '')}")

@app.command(name="gui", help="Inicia o servidor da Interface Gráfica Web.")
def gui(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host do servidor"),
    port: int = typer.Option(8080, "--port", "-p", help="Porta do servidor"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Não abrir o navegador automaticamente")
):
    console.print(format_banner())
    log_info(f"Iniciando SmartBusiners Web GUI em [bold cyan]http://{host}:{port}[/bold cyan]...")
    from smartbusiners.gui.server import start_gui
    start_gui(host=host, port=port, open_browser=not no_browser)

@app.command(name="serve", help="Alias para o comando gui.")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host do servidor"),
    port: int = typer.Option(8080, "--port", "-p", help="Porta do servidor")
):
    gui(host=host, port=port, no_browser=False)

@app.command(name="tools", help="Lista todas as ferramentas ativas no motor de IA.")
def list_tools():
    console.print(format_banner())
    tools = default_registry.get_all()
    console.print(format_tools_table(tools))

@app.command(name="version", help="Exibe a versão do SmartBusiners.")
def version():
    from smartbusiners import __version__
    console.print(f"[bold cyan]SmartBusiners AI Engine[/bold cyan] v[bold green]{__version__}[/bold green]")
