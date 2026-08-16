import sys
import os
from rich.console import Console

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console(legacy_windows=False)
error_console = Console(stderr=True, legacy_windows=False)

def log_info(msg: str):
    console.print(f"[bold cyan][INFO][/bold cyan] {msg}")

def log_success(msg: str):
    console.print(f"[bold green][SUCCESS][/bold green] {msg}")

def log_warning(msg: str):
    console.print(f"[bold yellow][WARN][/bold yellow] {msg}")

def log_error(msg: str):
    error_console.print(f"[bold red][ERROR][/bold red] {msg}")
