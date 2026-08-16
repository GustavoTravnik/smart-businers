/**
 * SmartBusiners AI Engine - Web Dashboard Frontend
 */

let ws = null;
let currentSessionId = null;
let isExecuting = false;

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initWebSocket();
  loadStatus();
  loadSessions();
  loadTools();
  loadWorkspaceFiles();
});

// -------------------------------------------------------------
// Tabs Navigation
// -------------------------------------------------------------
function initTabs() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      const tabId = btn.getAttribute("data-tab");
      document.getElementById(tabId).classList.add("active");
    });
  });
}

// -------------------------------------------------------------
// WebSocket Stream
// -------------------------------------------------------------
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/agent`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    appendTerminalLine("[SISTEMA] Conexão WebSocket estabelecida com sucesso.", "success");
    setAgentStatus("Pronto", "green");
  };

  ws.onclose = () => {
    appendTerminalLine("[SISTEMA] Conexão WebSocket encerrada. Tentando reconectar...", "error");
    setAgentStatus("Desconectado", "red");
    setTimeout(initWebSocket, 3000);
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleAgentEvent(msg.type, msg.data);
    } catch (e) {
      console.error("Erro ao processar mensagem:", e);
    }
  };
}

function handleAgentEvent(type, data) {
  if (type === "start") {
    currentSessionId = data.session_id;
    appendTerminalLine(`[INÍCIO] Sessão ${data.session_id} iniciada.`, "info");
    setAgentStatus("Pensando...", "yellow");
  } else if (type === "token") {
    appendAgentToken(data.content);
  } else if (type === "tool_call") {
    appendTerminalLine(`[FERRAMENTA] Executando: ${data.tool} (${JSON.stringify(data.args)})`, "tool");
    appendToolCallCard(data.tool, data.args);
  } else if (type === "tool_result") {
    appendTerminalLine(`[RESULTADO] ${data.tool} concluído: ${data.output.slice(0, 100)}...`, "success");
    updateToolResult(data.tool, data.output);
  } else if (type === "error") {
    appendTerminalLine(`[ERRO] ${data.message}`, "error");
    appendErrorMessage(data.message);
    setAgentStatus("Erro", "red");
    isExecuting = false;
    toggleSendBtn(true);
  } else if (type === "done") {
    appendTerminalLine(`[SUCESSO] Tarefa concluída em ${data.turns_used} turnos.`, "success");
    setAgentStatus("Pronto", "green");
    isExecuting = false;
    toggleSendBtn(true);
    loadSessions();
    loadWorkspaceFiles();
  }
}

// -------------------------------------------------------------
// Chat & Message Rendering
// -------------------------------------------------------------
function handleSendPrompt(e) {
  if (e) e.preventDefault();
  const input = document.getElementById("promptInput");
  const prompt = input.value.trim();
  if (!prompt || isExecuting) return;

  // Renderiza mensagem do usuário
  appendUserMessage(prompt);
  input.value = "";

  // Prepara container da resposta do agente
  createAgentMessageContainer();

  isExecuting = true;
  toggleSendBtn(false);

  const payload = {
    action: "run",
    prompt: prompt,
    session_id: currentSessionId,
    model: document.getElementById("modelSelect").value,
    temperature: parseFloat(document.getElementById("tempSlider").value),
  };

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  } else {
    appendErrorMessage("WebSocket desconectado. Aguarde reconexão.");
    toggleSendBtn(true);
  }
}

function handleKeyDown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSendPrompt();
  }
}

function appendUserMessage(text) {
  const chat = document.getElementById("chatHistory");
  const msgDiv = document.createElement("div");
  msgDiv.className = "message user";
  msgDiv.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
  chat.appendChild(msgDiv);
  chat.scrollTop = chat.scrollHeight;
}

let activeAgentMessageBubble = null;

function createAgentMessageContainer() {
  const chat = document.getElementById("chatHistory");
  const msgDiv = document.createElement("div");
  msgDiv.className = "message agent";
  activeAgentMessageBubble = document.createElement("div");
  activeAgentMessageBubble.className = "message-bubble";
  activeAgentMessageBubble.innerHTML = "<span class='typing'>Pensando...</span>";
  msgDiv.appendChild(activeAgentMessageBubble);
  chat.appendChild(msgDiv);
  chat.scrollTop = chat.scrollHeight;
}

function appendAgentToken(token) {
  if (!activeAgentMessageBubble) return;
  const typing = activeAgentMessageBubble.querySelector(".typing");
  if (typing) typing.remove();
  activeAgentMessageBubble.innerHTML += escapeHtml(token).replace(/\n/g, "<br>");
  document.getElementById("chatHistory").scrollTop = document.getElementById("chatHistory").scrollHeight;
}

function appendToolCallCard(toolName, args) {
  if (!activeAgentMessageBubble) return;
  const card = document.createElement("div");
  card.className = "tool-card";
  card.id = `tool-${toolName}-${Date.now()}`;
  card.innerHTML = `
    <div class="tool-card-header">⚡ Executando ferramenta: <strong>${escapeHtml(toolName)}</strong></div>
    <div class="tool-card-args">${escapeHtml(JSON.stringify(args))}</div>
    <div class="tool-card-result">Aguardando resultado...</div>
  `;
  activeAgentMessageBubble.appendChild(card);
  document.getElementById("chatHistory").scrollTop = document.getElementById("chatHistory").scrollHeight;
}

function updateToolResult(toolName, output) {
  const cards = document.querySelectorAll(".tool-card");
  if (cards.length > 0) {
    const lastCard = cards[cards.length - 1];
    const resDiv = lastCard.querySelector(".tool-card-result");
    if (resDiv) {
      resDiv.innerText = output.slice(0, 500) + (output.length > 500 ? "..." : "");
    }
  }
}

function appendErrorMessage(msg) {
  if (activeAgentMessageBubble) {
    activeAgentMessageBubble.innerHTML += `<div class="alert-box error" style="margin-top:8px;">❌ ${escapeHtml(msg)}</div>`;
  }
}

// -------------------------------------------------------------
// Terminal View
// -------------------------------------------------------------
function appendTerminalLine(text, type = "") {
  const term = document.getElementById("terminalOutput");
  const line = document.createElement("div");
  line.className = `term-line ${type}`;
  line.innerText = text;
  term.appendChild(line);
  term.scrollTop = term.scrollHeight;
}

function clearTerminal() {
  document.getElementById("terminalOutput").innerHTML = "";
}

// -------------------------------------------------------------
// Data Loaders & Modals
// -------------------------------------------------------------
async function loadStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    
    // Atualiza status de autenticação
    const authBadge = document.getElementById("authBadge");
    const authText = document.getElementById("authStatusText");
    const dot = authBadge.querySelector(".dot");

    if (data.auth.authenticated) {
      dot.className = "dot green";
      authText.innerText = `Google API: ${data.auth.masked_key}`;
    } else {
      dot.className = "dot yellow";
      authText.innerText = "Configurar Google API";
    }

    // Atualiza workspace
    document.getElementById("activeWorkspace").innerText = data.config.workspace;
    document.getElementById("cfgWorkspace").value = data.config.workspace;

    if (data.config.model) {
      document.getElementById("modelSelect").value = data.config.model;
    }
  } catch (e) {
    console.error("Erro ao obter status:", e);
  }
}

async function loadSessions() {
  try {
    const res = await fetch("/api/sessions");
    const sessions = await res.json();
    const container = document.getElementById("sessionList");
    container.innerHTML = "";
    sessions.forEach(s => {
      const item = document.createElement("div");
      item.className = `session-item ${s.session_id === currentSessionId ? "active" : ""}`;
      item.innerText = s.title;
      item.title = `ID: ${s.session_id} (${s.message_count} mensagens)`;
      item.onclick = () => loadSessionHistory(s.session_id);
      container.appendChild(item);
    });
  } catch (e) {
    console.error("Erro ao listar sessões:", e);
  }
}

async function loadSessionHistory(sessionId) {
  try {
    const res = await fetch(`/api/sessions/${sessionId}`);
    const data = await res.json();
    currentSessionId = data.session_id;
    const chat = document.getElementById("chatHistory");
    chat.innerHTML = "";
    
    data.messages.forEach(msg => {
      const msgDiv = document.createElement("div");
      msgDiv.className = `message ${msg.role === "user" ? "user" : "agent"}`;
      msgDiv.innerHTML = `<div class="message-bubble">${escapeHtml(msg.content).replace(/\n/g, "<br>")}</div>`;
      chat.appendChild(msgDiv);
    });
    loadSessions();
  } catch (e) {
    console.error("Erro ao carregar sessão:", e);
  }
}

function startNewSession() {
  currentSessionId = null;
  document.getElementById("chatHistory").innerHTML = `
    <div class="welcome-card">
      <div class="welcome-icon">🚀</div>
      <h2>Nova Conversa Iniciada</h2>
      <p>Pronto para receber instruções e automatizar tarefas no seu workspace.</p>
    </div>
  `;
  loadSessions();
}

async function loadTools() {
  try {
    const res = await fetch("/api/tools");
    const tools = await res.json();
    const container = document.getElementById("toolsList");
    container.innerHTML = "";
    tools.forEach(t => {
      const tag = document.createElement("span");
      tag.className = "tool-tag";
      tag.innerText = t.name;
      tag.title = t.description;
      container.appendChild(tag);
    });
  } catch (e) {
    console.error("Erro ao carregar ferramentas:", e);
  }
}

async function loadWorkspaceFiles() {
  try {
    const res = await fetch("/api/workspace/files");
    const data = await res.json();
    const tree = document.getElementById("fileTree");
    tree.innerHTML = "";
    if (data.files) {
      data.files.forEach(f => {
        const item = document.createElement("div");
        item.className = "file-item";
        item.innerHTML = `${f.is_dir ? "📁" : "📄"} ${escapeHtml(f.name)}`;
        tree.appendChild(item);
      });
    }
  } catch (e) {
    console.error("Erro ao listar arquivos:", e);
  }
}

// -------------------------------------------------------------
// Auth & Modals
// -------------------------------------------------------------
function openAuthModal() { document.getElementById("authModal").classList.add("active"); }
function closeAuthModal() { document.getElementById("authModal").classList.remove("active"); }

function openCliModal() { document.getElementById("cliModal").classList.add("active"); }
function closeCliModal() { document.getElementById("cliModal").classList.remove("active"); }

function openSettingsModal() { document.getElementById("settingsModal").classList.add("active"); }
function closeSettingsModal() { document.getElementById("settingsModal").classList.remove("active"); }

async function saveApiKey() {
  const key = document.getElementById("apiKeyInput").value.trim();
  const alertBox = document.getElementById("authResultBox");
  if (!key) return;

  alertBox.style.display = "block";
  alertBox.className = "alert-box";
  alertBox.innerText = "Validando chave junto aos servidores da Google...";

  try {
    const res = await fetch("/api/auth", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({api_key: key})
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alertBox.className = "alert-box success";
      alertBox.innerText = "Chave validada e salva com sucesso!";
      setTimeout(() => {
        closeAuthModal();
        loadStatus();
      }, 1200);
    } else {
      alertBox.className = "alert-box error";
      alertBox.innerText = data.error || "Falha ao validar chave Google.";
    }
  } catch (e) {
    alertBox.className = "alert-box error";
    alertBox.innerText = "Erro ao conectar com servidor local.";
  }
}

async function saveSettings() {
  const wsPath = document.getElementById("cfgWorkspace").value.trim();
  try {
    await fetch("/api/config", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({workspace: wsPath})
    });
    closeSettingsModal();
    loadStatus();
    loadWorkspaceFiles();
  } catch (e) {
    alert("Erro ao salvar configurações.");
  }
}

function usePreset(text) {
  document.getElementById("promptInput").value = text;
  handleSendPrompt();
}

function setAgentStatus(text, color) {
  const el = document.getElementById("agentStatus");
  el.innerHTML = `<span class="dot ${color}"></span> ${text}`;
}

function toggleSendBtn(enabled) {
  const btn = document.getElementById("btnSend");
  btn.disabled = !enabled;
  btn.style.opacity = enabled ? "1" : "0.6";
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
