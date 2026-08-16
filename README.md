# ⚡ SmartBusiners AI Engine & Web Dashboard

> **Sistema Comercial de IA em Python com CLI Profissional e Interface Web em Tempo Real**  
> Powered by **Google Gemini API** & **Antigravity Agentic Architecture** (BYOK - Bring Your Own Key).

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Commercial-green.svg)](#)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini%202.5-orange.svg)](https://aistudio.google.com/)

---

## 🇧🇷 Visão Geral (Português)

O **SmartBusiners** é uma solução completa de inteligência artificial autônoma para desenvolvedores, empresas e consultorias. Ele foi projetado para distribuição comercial no modelo **BYOK (Bring Your Own Key)**: o seu cliente conecta diretamente a conta ou chave da Google (Google AI Studio / Gemini API / Google Cloud Vertex AI), garantindo controle total de custos e cotas.

### 🌟 Destaques Principais

1. **CLI Poderoso no Terminal**:
   - Invoque `smartbusiners chat` para uma experiência interativa contínua com renderização Rich (markdown, syntax highlight, spinners).
   - Invoque `smartbusiners run "<instrução>"` para tarefas autônomas de codificação, geração de testes e refatoração.
2. **Interface Gráfica Web Integrada**:
   - Invoque `smartbusiners gui` para abrir um dashboard moderno com **Dark Glassmorphism**.
   - Monitoramento em tempo real do raciocínio da IA (*thought trace*), execução de ferramentas (*tool calling*) e stream de console.
   - Controle dinâmico de parâmetros (Workspace, Modelo Gemini 2.5 Flash / Pro, Temperatura, Ferramentas).
3. **Ferramentas Nativas do Agente**:
   - Execução segura de comandos no terminal (`run_command`).
   - Leitura, edição e gravação de arquivos (`read_file`, `write_file`).
   - Navegação de diretórios e busca textual (`list_directory`, `search_files`).
   - Inspeção de contexto do workspace e Git (`get_workspace_info`).

---

## 🚀 Instalação Rápida

### 1. Pré-requisitos
- Python 3.10 ou superior
- Uma chave de API da Google ([Google AI Studio](https://aistudio.google.com/))

### 2. Instalação do Pacote

```bash
# Clone ou acesse a pasta do projeto
cd R:\Github\SmartBusiners

# Instale as dependências
pip install -r requirements.txt

# Instale o CLI globalmente em modo editável
pip install -e .
```

---

## 🔑 Configuração da Chave Google (BYOK)

Você pode configurar a chave de API da Google através de 3 métodos:

1. **Pelo Terminal**:
   ```bash
   smartbusiners auth --key "SUA_CHAVE_GEMINI_AQUI"
   ```
2. **Pela Interface Web**:
   Inicie a interface (`smartbusiners gui`), clique no indicador de status no canto superior direito e insira sua chave.
3. **Por Variável de Ambiente (`.env`)**:
   ```bash
   cp .env.example .env
   # Adicione GEMINI_API_KEY=sua_chave no arquivo .env
   ```

---

## 💻 Guia de Uso do CLI

### Modo Chat Interativo
```bash
smartbusiners chat
```
*Inicia uma sessão interativa no terminal onde o SmartBusiners responde dúvidas, inspeciona arquivos e executa tarefas com você.*

### Execução de Tarefa Autônoma
```bash
smartbusiners run "Crie uma API REST em FastAPI para cadastro de clientes com SQLite"
```

### Iniciar a Interface Gráfica Web
```bash
smartbusiners gui
# ou
smartbusiners serve --port 8080
```

### Validar e Testar Chave Google
```bash
smartbusiners auth --test
```

### Listar Ferramentas Disponíveis
```bash
smartbusiners tools
```

---

## 🌐 Interface Gráfica Web (Dashboard)

A interface gráfica foi construída em **Python (FastAPI + WebSockets)** com frontend nativo e responsivo.

- **URL Padrão**: `http://127.0.0.1:8080`
- **Recursos**:
  - **Canvas do Agente**: Conversas com renderização de código e botões de presets rápidos.
  - **Terminal em Tempo Real**: Visualize cada comando executado e saída de processos.
  - **Explorador de Arquivos**: Árvore de arquivos do workspace atualizado dinamicamente.
  - **Histórico de Sessões**: Retome conversas e execuções anteriores a qualquer momento.

---

## 🏗 Arquitetura do Projeto

```text
SmartBusiners/
├── smartbusiners/
│   ├── cli.py               # Entrypoint do CLI (Typer & Rich)
│   ├── core/
│   │   ├── config.py        # Gerenciador de configurações (~/.smartbusiners)
│   │   ├── auth.py          # Validador de contas Google (BYOK)
│   │   ├── engine.py        # Motor do Agente com Tool Calling & Streaming
│   │   ├── session.py       # Histórico de sessões e persistência
│   │   ├── tools.py         # Ferramentas nativas do sistema
│   │   └── prompts.py       # Prompts de sistema e personas
│   ├── gui/
│   │   ├── server.py        # Servidor FastAPI com WebSockets
│   │   └── static/          # Dashboard Web moderno (HTML, CSS, JS)
│   └── utils/
│       ├── logger.py        # Logs formatados com Rich
│       └── formatters.py    # Formatação de tabelas e banners
├── pyproject.toml           # Metadados e dependências do pacote
├── setup.py                 # Instalador pip
├── requirements.txt         # Dependências do projeto
├── run_cli.py               # Launcher rápido do CLI
├── run_gui.py               # Launcher rápido da Web GUI
└── README.md                # Documentação do projeto
```

---

## 📄 Licença e Distribuição Comercial

Este software é fornecido sob licença comercial para o ecossistema **SmartBusiners**.
