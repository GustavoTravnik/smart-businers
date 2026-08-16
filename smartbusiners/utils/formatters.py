from rich.table import Table
from rich.panel import Panel

def format_banner() -> Panel:
    banner_text = """
[bold cyan]* SMARTBUSINERS AI ENGINE *[/bold cyan]
[dim]Plataforma Comercial de Agentes de IA em Python & Google Gemini[/dim]
    """
    return Panel(banner_text.strip(), border_style="cyan", expand=False)

def format_tools_table(tools_list) -> Table:
    table = Table(title="Ferramentas Integradas do Agente", border_style="blue")
    table.add_column("Nome", style="cyan bold", no_wrap=True)
    table.add_column("Descrição", style="white")
    table.add_column("Parâmetros Requeridos", style="magenta")

    for tool in tools_list:
        req = tool.parameters.get("required", [])
        req_str = ", ".join(req) if req else "Nenhum"
        table.add_row(tool.name, tool.description, req_str)
    return table
