/**
 * SmartBusiners AI Engine - Coia Skeleton Frontend
 */

let currentTab = 'home';
let activeExecutionId = null;
let logPollInterval = null;

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadStatus();
  loadCommands();
  loadPrompts();
  loadSprints();
  loadExecutions();
  loadWorkspaceFiles();
  loadCostSummary();
});

// -------------------------------------------------------------
// Tabs Navigation
// -------------------------------------------------------------
function showTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-tab') === tabName);
  });
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === `tab-${tabName}`);
  });
  currentTab = tabName;
  if (tabName === 'executions') loadExecutions();
  if (tabName === 'sprints') loadSprints();
}

// -------------------------------------------------------------
// Theme Toggle
// -------------------------------------------------------------
function initTheme() {
  const saved = localStorage.getItem('sb-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeIcon(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('sb-theme', next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const btn = document.getElementById('btn-theme-toggle');
  if (btn) btn.innerText = theme === 'dark' ? '🌙' : '☀️';
}

// -------------------------------------------------------------
// Toast Notifications
// -------------------------------------------------------------
function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('active');
  setTimeout(() => toast.classList.remove('active'), 3000);
}

// -------------------------------------------------------------
// Status & Global Config
// -------------------------------------------------------------
async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    const pill = document.getElementById('homeApiStatus');
    const text = document.getElementById('homeApiText');
    const dot = pill.querySelector('.dot');

    if (data.auth && data.auth.authenticated) {
      dot.className = 'dot green';
      text.innerText = `Google Gemini: ${data.auth.masked_key}`;
    } else {
      dot.className = 'dot yellow';
      text.innerText = 'Configurar Chave Google (BYOK)';
    }

    document.getElementById('homeWsText').innerText = data.config.workspace || 'N/A';
    document.getElementById('cfgWorkspaceInput').value = data.config.workspace || '';
    if (data.config.default_model) {
      document.getElementById('homeModelSelect').value = data.config.default_model;
    }
    if (data.config.temperature) {
      document.getElementById('homeTempSlider').value = data.config.temperature;
      document.getElementById('homeTempVal').innerText = data.config.temperature;
    }
    if (data.config.action_mode) {
      selectActionMode(data.config.action_mode, false);
    }
  } catch (e) {
    console.error('Erro ao carregar status:', e);
  }
}

async function saveActiveModel(model) {
  await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ default_model: model })
  });
  showToast(`Modelo ativo alterado para ${model}`);
}

async function saveActiveTemp(temp) {
  await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ temperature: parseFloat(temp) })
  });
}

function selectActionMode(mode, notify = true) {
  document.querySelectorAll('.mode-card').forEach(c => {
    c.classList.toggle('active', c.getAttribute('data-mode') === mode);
  });
  if (notify) {
    fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action_mode: mode })
    });
    showToast(`Modo alterado para ${mode}`);
  }
}

// -------------------------------------------------------------
// Terminal Opener & Executions
// -------------------------------------------------------------
async function openTerminalDirectly(cmd) {
  try {
    const res = await fetch('/api/terminal/open', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Janela de terminal aberta: ${cmd}`);
    } else {
      showToast('Falha ao abrir terminal.');
    }
  } catch (e) {
    showToast('Erro de conexão ao abrir terminal.');
  }
}

async function executeQuickRun() {
  const prompt = document.getElementById('quickRunInput').value.trim();
  if (!prompt) return;
  document.getElementById('quickRunInput').value = '';
  startWebExecution(prompt);
}

async function executeQuickRunInTerminal() {
  const prompt = document.getElementById('quickRunInput').value.trim();
  if (!prompt) return;
  document.getElementById('quickRunInput').value = '';
  openTerminalDirectly(`smartbusiners run "${prompt}"`);
}

async function startWebExecution(prompt, title = null) {
  showTab('executions');
  try {
    const res = await fetch('/api/executions/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: prompt, title: title })
    });
    const data = await res.json();
    if (data.success) {
      activeExecutionId = data.execution_id;
      loadExecutions();
      watchExecutionLogs(data.execution_id, prompt);
    }
  } catch (e) {
    showToast('Erro ao iniciar execução.');
  }
}

async function loadExecutions() {
  try {
    const res = await fetch('/api/executions');
    const list = await res.json();
    const tbody = document.getElementById('executions-table-body');
    tbody.innerHTML = '';
    list.forEach(item => {
      const tr = document.createElement('tr');
      tr.style.cursor = 'pointer';
      tr.onclick = () => watchExecutionLogs(item.id, item.title);
      tr.innerHTML = `
        <td><code>${item.id}</code></td>
        <td><strong>${escapeHtml(item.title)}</strong></td>
        <td><span class="dot ${item.status === 'running' ? 'yellow' : (item.status === 'done' ? 'green' : 'red')}"></span> ${item.status}</td>
        <td><small style="color:var(--text-dim)">${item.created_at.slice(0, 16).replace('T', ' ')}</small></td>
        <td>
          <button class="btn-xs btn-secondary" onclick="event.stopPropagation(); openTerminalDirectly('${escapeHtml(item.command)}')">💻 Terminal</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error('Erro ao listar execuções:', e);
  }
}

function watchExecutionLogs(execId, title) {
  activeExecutionId = execId;
  document.getElementById('activeExecTitle').innerText = `${title || execId} (${execId})`;
  document.getElementById('btnStopExec').style.display = 'inline-flex';
  
  if (logPollInterval) clearInterval(logPollInterval);

  const fetchLogs = async () => {
    try {
      const res = await fetch(`/api/executions/${execId}/logs`);
      const data = await res.json();
      const body = document.getElementById('liveTerminalOutput');
      body.innerHTML = '';
      data.logs.forEach(l => {
        const div = document.createElement('div');
        div.className = `term-line ${l.includes('[ERRO]') || l.includes('Error') ? 'error' : (l.includes('[INFO]') ? 'info' : '')}`;
        div.innerText = l;
        body.appendChild(div);
      });
      body.scrollTop = body.scrollHeight;

      if (data.status !== 'running') {
        document.getElementById('btnStopExec').style.display = 'none';
        clearInterval(logPollInterval);
      }
    } catch (e) {}
  };

  fetchLogs();
  logPollInterval = setInterval(fetchLogs, 1500);
}

async function stopCurrentExecution() {
  if (!activeExecutionId) return;
  await fetch(`/api/executions/${activeExecutionId}/stop`, { method: 'POST' });
  showToast('Sinal de interrupção enviado.');
}

function clearActiveTerminal() {
  document.getElementById('liveTerminalOutput').innerHTML = '';
}

// -------------------------------------------------------------
// Commands
// -------------------------------------------------------------
async function loadCommands() {
  try {
    const res = await fetch('/api/commands');
    const cmds = await res.json();
    const grid = document.getElementById('commands-list');
    grid.innerHTML = '';
    cmds.forEach(c => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px">
          <strong>⚡ ${escapeHtml(c.name)}</strong>
          <button class="btn-xs btn-outline" onclick="deleteCommand('${c.id}')">✕</button>
        </div>
        <p style="font-size:0.8rem; color:var(--text-dim); margin-bottom:12px">${escapeHtml(c.desc || '')}</p>
        <code style="display:block; background:var(--surface2); padding:6px; border-radius:4px; font-size:0.75rem; margin-bottom:12px; overflow-x:auto">${escapeHtml(c.cmd)}</code>
        <div style="display:flex; gap:8px">
          <button class="btn btn-primary btn-xs" onclick="startWebExecution('${escapeHtml(c.cmd)}', '${escapeHtml(c.name)}')">⚡ Executar Web</button>
          <button class="btn btn-secondary btn-xs" onclick="openTerminalDirectly('${escapeHtml(c.cmd)}')">💻 Terminal</button>
        </div>
      `;
      grid.appendChild(card);
    });
  } catch (e) {
    console.error(e);
  }
}

function openNewCommandModal() {
  document.getElementById('modalCmdId').value = '';
  document.getElementById('modalCmdName').value = '';
  document.getElementById('modalCmdDesc').value = '';
  document.getElementById('modalCmdCli').value = '';
  openModal('modal-command');
}

async function saveCommandForm() {
  const name = document.getElementById('modalCmdName').value.trim();
  const desc = document.getElementById('modalCmdDesc').value.trim();
  const cmd = document.getElementById('modalCmdCli').value.trim();
  const id = document.getElementById('modalCmdId').value.trim();
  if (!name || !cmd) return;

  await fetch('/api/commands', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, name, desc, cmd })
  });
  closeModal('modal-command');
  loadCommands();
  showToast('Comando salvo com sucesso!');
}

async function deleteCommand(id) {
  if (!confirm('Deseja excluir este comando?')) return;
  await fetch(`/api/commands/${id}`, { method: 'DELETE' });
  loadCommands();
}

// -------------------------------------------------------------
// Prompts
// -------------------------------------------------------------
async function loadPrompts() {
  try {
    const res = await fetch('/api/prompts');
    const list = await res.json();
    const grid = document.getElementById('prompts-list');
    grid.innerHTML = '';
    list.forEach(p => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px">
          <strong>💬 ${escapeHtml(p.name)}</strong>
          <button class="btn-xs btn-outline" onclick="deletePrompt('${p.id}')">✕</button>
        </div>
        <p style="font-size:0.8rem; color:var(--text-dim); margin-bottom:12px">${escapeHtml(p.desc || '')}</p>
        <div style="background:var(--surface2); padding:10px; border-radius:6px; font-size:0.75rem; max-height:100px; overflow-y:auto; margin-bottom:12px">
          ${escapeHtml(p.template)}
        </div>
        <button class="btn btn-primary btn-xs" onclick="usePromptTemplate('${escapeHtml(p.template)}')">Usar Prompt ⚡</button>
      `;
      grid.appendChild(card);
    });
  } catch (e) {
    console.error(e);
  }
}

function openNewPromptModal() {
  document.getElementById('modalPromptId').value = '';
  document.getElementById('modalPromptName').value = '';
  document.getElementById('modalPromptDesc').value = '';
  document.getElementById('modalPromptTemplate').value = '';
  openModal('modal-prompt');
}

async function savePromptForm() {
  const name = document.getElementById('modalPromptName').value.trim();
  const desc = document.getElementById('modalPromptDesc').value.trim();
  const template = document.getElementById('modalPromptTemplate').value.trim();
  const id = document.getElementById('modalPromptId').value.trim();
  if (!name || !template) return;

  await fetch('/api/prompts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, name, desc, template })
  });
  closeModal('modal-prompt');
  loadPrompts();
  showToast('Template de prompt salvo!');
}

async function deletePrompt(id) {
  if (!confirm('Deseja excluir este template?')) return;
  await fetch(`/api/prompts/${id}`, { method: 'DELETE' });
  loadPrompts();
}

function usePromptTemplate(tpl) {
  showTab('home');
  document.getElementById('quickRunInput').value = tpl;
  document.getElementById('quickRunInput').focus();
}

// -------------------------------------------------------------
// Sprints / Kanban Board
// -------------------------------------------------------------
async function loadSprints() {
  try {
    const res = await fetch('/api/sprints');
    const tasks = await res.json();

    const cols = { open: document.getElementById('cards-open'), in_progress: document.getElementById('cards-in_progress'), done: document.getElementById('cards-done') };
    const counts = { open: 0, in_progress: 0, done: 0 };
    Object.values(cols).forEach(c => c.innerHTML = '');

    tasks.forEach(t => {
      const status = t.status || 'open';
      if (cols[status]) {
        counts[status]++;
        const card = document.createElement('div');
        card.className = 'kanban-card';
        card.onclick = () => openEditTaskModal(t);
        card.innerHTML = `
          <div class="kanban-card-title">${escapeHtml(t.title)}</div>
          <div class="kanban-card-desc">${escapeHtml(t.desc || '')}</div>
          <div class="kanban-card-footer">
            <span class="priority-tag ${t.priority || 'normal'}">${t.priority || 'normal'}</span>
            <button class="btn-xs btn-primary" onclick="event.stopPropagation(); executeTaskDirectly('${escapeHtml(t.title)}')">⚡ Executar</button>
          </div>
        `;
        cols[status].appendChild(card);
      }
    });

    document.getElementById('count-open').innerText = counts.open;
    document.getElementById('count-in_progress').innerText = counts.in_progress;
    document.getElementById('count-done').innerText = counts.done;
  } catch (e) {
    console.error(e);
  }
}

function executeTaskDirectly(title) {
  startWebExecution(`Execute a seguinte tarefa: ${title}`, title);
}

function openNewTaskModal() {
  document.getElementById('modalTaskId').value = '';
  document.getElementById('modalTaskTitleInput').value = '';
  document.getElementById('modalTaskDescInput').value = '';
  document.getElementById('modalTaskStatus').value = 'open';
  document.getElementById('modalTaskPriority').value = 'normal';
  document.getElementById('btnDeleteTask').style.display = 'none';
  openModal('modal-task');
}

function openEditTaskModal(task) {
  document.getElementById('modalTaskId').value = task.id;
  document.getElementById('modalTaskTitleInput').value = task.title;
  document.getElementById('modalTaskDescInput').value = task.desc || '';
  document.getElementById('modalTaskStatus').value = task.status || 'open';
  document.getElementById('modalTaskPriority').value = task.priority || 'normal';
  document.getElementById('btnDeleteTask').style.display = 'inline-flex';
  openModal('modal-task');
}

async function saveTaskForm() {
  const id = document.getElementById('modalTaskId').value;
  const title = document.getElementById('modalTaskTitleInput').value.trim();
  const desc = document.getElementById('modalTaskDescInput').value.trim();
  const status = document.getElementById('modalTaskStatus').value;
  const priority = document.getElementById('modalTaskPriority').value;
  if (!title) return;

  await fetch('/api/sprints', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, title, desc, status, priority })
  });
  closeModal('modal-task');
  loadSprints();
  showToast('Tarefa atualizada no Kanban!');
}

async function deleteTaskForm() {
  const id = document.getElementById('modalTaskId').value;
  if (!id) return;
  await fetch(`/api/sprints/${id}`, { method: 'DELETE' });
  closeModal('modal-task');
  loadSprints();
  showToast('Tarefa removida.');
}

// -------------------------------------------------------------
// Workspace Files
// -------------------------------------------------------------
async function loadWorkspaceFiles() {
  try {
    const res = await fetch('/api/workspace/files');
    const data = await res.json();
    const grid = document.getElementById('workspaceFilesGrid');
    grid.innerHTML = '';
    if (data.files) {
      data.files.forEach(f => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `${f.is_dir ? '📁' : '📄'} <strong>${escapeHtml(f.name)}</strong>`;
        grid.appendChild(item);
      });
    }
  } catch (e) {
    console.error(e);
  }
}

// -------------------------------------------------------------
// Cost Summary
// -------------------------------------------------------------
async function loadCostSummary() {
  try {
    const res = await fetch('/api/cost/summary');
    const data = await res.json();
    document.getElementById('cost-today-req').innerText = data.today_requests || 0;
    document.getElementById('cost-today-tokens').innerText = (data.today_tokens || 0).toLocaleString();
    document.getElementById('cost-today-usd').innerText = `$${(data.today_estimated_cost_usd || 0).toFixed(4)}`;
    document.getElementById('cost-quota-status').innerText = data.quota_status || 'OK';
  } catch (e) {}
}

// -------------------------------------------------------------
// Settings / Auth
// -------------------------------------------------------------
async function saveSettingsAuth() {
  const key = document.getElementById('cfgApiKeyInput').value.trim();
  if (!key) return;
  try {
    const res = await fetch('/api/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: key })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast('Chave Google validada e salva!');
      loadStatus();
    } else {
      alert(data.error || 'Erro ao validar chave Google.');
    }
  } catch (e) {
    alert('Erro de conexão ao salvar chave.');
  }
}

async function saveSettingsWorkspace() {
  const ws = document.getElementById('cfgWorkspaceInput').value.trim();
  await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace: ws })
  });
  showToast('Workspace atualizado com sucesso!');
  loadStatus();
  loadWorkspaceFiles();
}

// -------------------------------------------------------------
// Modals Generic
// -------------------------------------------------------------
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }

function openRunModal() {
  document.getElementById('modalRunPrompt').value = '';
  openModal('modal-run');
}

function submitModalRun(inTerminal) {
  const prompt = document.getElementById('modalRunPrompt').value.trim();
  if (!prompt) return;
  closeModal('modal-run');
  if (inTerminal) {
    openTerminalDirectly(`smartbusiners run "${prompt}"`);
  } else {
    startWebExecution(prompt);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
