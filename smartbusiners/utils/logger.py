import sys
from rich.console import Console

console = Console()
error_console = Console(stderr=True)

def log_info(msg: str):
    console.print(f"[bold cyan]ℹ [INFO][/bold cyan] {msg}")

def log_success(msg: str):
    console.print(f"[bold green]✔ [SUCCESS][/bold green] {msg}")

def log_warning(msg: str):
    console.print(f"[bold yellow]⚠ [WARN][/bold yellow] {msg}")

def log_error(msg: str):
    error_console.print(f"[bold red]✖ [ERROR][/bold red] {msg}")
