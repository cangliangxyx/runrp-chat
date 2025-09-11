document.addEventListener("DOMContentLoaded", () => {
  /*** -------------------- 人物管理 -------------------- ***/
  async function loadPersonas() {
    try {
      const res = await fetch("/personas");
      const data = await res.json();
      const container = document.getElementById("persona-list");
      container.innerHTML = "";
      data.personas.forEach(p => {
        const div = document.createElement("div");
        div.innerHTML = `<label><input type="checkbox" value="${p.name}" ${p.selected ? "checked" : ""}> ${p.name}</label>`;
        container.appendChild(div);
      });
      refreshCurrentPersonas();
    } catch (err) {
      console.error("加载 personas 失败:", err);
    }
  }

  async function updatePersonas() {
    const checkboxes = document.querySelectorAll("#persona-list input[type=checkbox]");
    const selected = Array.from(checkboxes)
      .filter(cb => cb.checked)
      .map(cb => cb.value)
      .join(",");
    const formData = new FormData();
    formData.append("selected", selected);
    await fetch("/personas", { method: "POST", body: formData });
    refreshCurrentPersonas();
  }

  async function refreshCurrentPersonas() {
    try {
      const res = await fetch("/personas");
      const data = await res.json();
      const current = data.personas.filter(p => p.selected).map(p => p.name).join(", ") || "无";
      document.getElementById("current-personas-display").textContent = current;
    } catch {}
  }

  document.getElementById("btn-update-personas").addEventListener("click", updatePersonas);

  /*** -------------------- system_rules 动态加载 -------------------- ***/
  fetch("/system_rules")
    .then(res => res.json())
    .then(data => {
      const select = document.getElementById("system_rules");
      select.innerHTML = "";
      data.rules.forEach(rule => {
        const opt = document.createElement("option");
        opt.value = rule;
        opt.textContent = rule;
        select.appendChild(opt);
      });
      if (data.rules.includes("developer")) select.value = "developer";
    })
    .catch(err => console.error("加载 system_rules 失败:", err));

  /*** -------------------- 会话管理 -------------------- ***/
  const form = document.getElementById("chat-form");
  const modelSel = document.getElementById("model");
  const systemSel = document.getElementById("system_rules");
  const promptEl = document.getElementById("prompt");
  const messagesEl = document.getElementById("messages");
  const sendBtn = form.querySelector('button[type="submit"]');
  const sidebar = document.getElementById("sidebar");
  const btnToggle = document.getElementById("btn-toggle");
  const btnNew = document.getElementById("btn-new");
  const btnClearAll = document.getElementById("btn-clear-all");
  const convList = document.getElementById("conv-list");
  const webInputEl = document.getElementById("web_input");

  const overlay = document.createElement("div");
  overlay.id = "sidebar-overlay";
  overlay.style.cssText = `position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.3);z-index:15;display:none;`;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", closeSidebar);

  const LS_KEY = "runrp_chat_conversations";
  const LS_ACTIVE = "runrp_chat_active";

  const uid = () => Math.random().toString(36).slice(2, 10);
  let conversations = loadConversations();
  let activeId = loadActiveId();

  function loadConversations() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      const data = raw ? JSON.parse(raw) : [];
      return Array.isArray(data) ? data : [];
    } catch { return []; }
  }

  function loadActiveId() { return localStorage.getItem(LS_ACTIVE) || ""; }

  function save() {
    localStorage.setItem(LS_KEY, JSON.stringify(conversations));
    localStorage.setItem(LS_ACTIVE, activeId || "");
  }

  const getActiveConv = () => conversations.find(c => c.id === activeId) || null;

  function renderConvList() {
    convList.innerHTML = "";
    conversations.forEach(conv => {
      const item = document.createElement("div");
      item.className = `conv-item${conv.id === activeId ? " active" : ""}`;
      item.dataset.id = conv.id;

      const title = document.createElement("div");
      title.className = "conv-title";
      title.textContent = conv.title || "未命名会话";
      title.title = "双击编辑标题";
      title.addEventListener("dblclick", () => startEditTitle(conv.id, title));

      const meta = document.createElement("div");
      meta.className = "conv-meta";
      meta.textContent = new Date(conv.updatedAt || Date.now()).toLocaleString();

      const actions = document.createElement("div");
      actions.className = "conv-actions";

      const btnEdit = document.createElement("button");
      btnEdit.className = "btn-icon";
      btnEdit.textContent = "✎";
      btnEdit.addEventListener("click", e => { e.stopPropagation(); startEditTitle(conv.id, title); });

      const btnDel = document.createElement("button");
      btnDel.className = "btn-icon";
      btnDel.textContent = "×";
      btnDel.addEventListener("click", e => {
        e.stopPropagation();
        if (confirm(`确认删除会话「${conv.title || "未命名会话"}」吗？`)) {
          conversations = conversations.filter(c => c.id !== conv.id);
          if (activeId === conv.id) activeId = conversations[0]?.id || "";
          save(); renderConvList(); renderMessages();
          if (!conversations.length) newConversation();
        }
      });

      actions.append(btnEdit, btnDel);
      const wrap = document.createElement("div");
      wrap.append(title, meta, actions);
      item.appendChild(wrap);

      item.addEventListener("click", () => {
        activeId = conv.id; save(); renderConvList(); renderMessages(); closeSidebar();
      });

      convList.appendChild(item);
    });
  }

  function startEditTitle(convId, titleEl) {
    const conv = conversations.find(c => c.id === convId);
    if (!conv) return;
    const oldText = conv.title || "未命名会话";
    const input = document.createElement("input");
    input.type = "text"; input.className = "title-input"; input.value = oldText;
    titleEl.replaceWith(input);
    input.focus(); input.select();
    const finish = saveChange => {
      if (saveChange) conv.title = input.value.trim() || oldText;
      conv.updatedAt = Date.now();
      save();
      renderConvList();
    };
    input.addEventListener("keydown", e => {
      if (e.key === "Enter") finish(true);
      else if (e.key === "Escape") finish(false);
    });
    input.addEventListener("blur", () => finish(true));
  }

  function renderMessages() {
    messagesEl.innerHTML = "";
    const conv = getActiveConv();
    if (!conv) return;
    conv.messages.forEach(msg => {
      const wrap = document.createElement("div");
      wrap.className = `msg ${msg.role}`;
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = msg.content;
      wrap.appendChild(bubble);
      messagesEl.appendChild(wrap);
    });
    scrollToBottom();
  }

  function newConversation(initialText = "") {
    const id = uid();
    const title = (initialText || "新的对话").slice(0, 30);
    const conv = { id, title, messages: [], createdAt: Date.now(), updatedAt: Date.now() };
    conversations.unshift(conv); activeId = id; save(); renderConvList(); renderMessages();
    return conv;
  }

  function appendMessage(role, content) {
    let conv = getActiveConv(); if (!conv) conv = newConversation(content);
    conv.messages.push({ role, content, ts: Date.now() });
    conv.updatedAt = Date.now();
    save();
    const wrap = document.createElement("div");
    wrap.className = `msg ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = content;
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    scrollToBottom();
    return { conv, bubble };
  }

  function ensureAssistantMessage() {
    const conv = getActiveConv(); if (!conv) return appendMessage("assistant", "");
    const last = conv.messages[conv.messages.length - 1];
    if (!last || last.role !== "assistant") return appendMessage("assistant", "");
    const nodes = messagesEl.querySelectorAll(".msg.assistant .bubble");
    return { conv, bubble: nodes[nodes.length - 1] };
  }

  function scrollToBottom() {
    requestAnimationFrame(() => messagesEl.scrollTop = messagesEl.scrollHeight);
  }

  function openSidebar() { sidebar.classList.add("open"); overlay.style.display = "block"; }
  function closeSidebar() { sidebar.classList.remove("open"); overlay.style.display = "none"; }

  btnToggle.addEventListener("click", () => sidebar.classList.contains("open") ? closeSidebar() : openSidebar());
  btnNew.addEventListener("click", () => { newConversation(); openSidebar(); });
  btnClearAll.addEventListener("click", () => {
    if (confirm("确认清空所有历史会话吗？")) { conversations = []; activeId = ""; save(); renderConvList(); renderMessages(); newConversation(); }
  });

  document.getElementById("btn-clear-history").addEventListener("click", () => {
    if (confirm("确定要清空当前对话历史吗？")) {
      const conv = getActiveConv();
      if (conv) conv.messages = [];
      save(); renderMessages();
      fetch("/clear_history", { method: "POST" }).catch(() => {});
    }
  });

  messagesEl.addEventListener("click", e => { if (!e.target.closest(".bubble")) closeSidebar(); });

  promptEl.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });

  // -------------------- 表单提交 --------------------
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const model = modelSel.value;
    const systemRule = systemSel.value;
    const prompt = promptEl.value.trim();
    if (!prompt) return;

    // ✅ 实时读取 NSFW 开关状态
    const nsfw = document.getElementById("nsfw-checkbox").checked ? "true" : "false";
    // console.log("[前端] 当前 nsfw 开关状态:", nsfw);  // 👈 添加这一行

    appendMessage("user", prompt);
    promptEl.value = "";

    const conv = getActiveConv();
    const assistantNode = ensureAssistantMessage();

    const formData = new FormData();
    formData.append("model", model);
    formData.append("system_rule", systemRule);
    formData.append("prompt", prompt);
    formData.append("conversation_id", conv?.id || "");
    formData.append("history", JSON.stringify(conv?.messages || []));
    formData.append("web_input", webInputEl?.value.trim() || "");
    formData.append("nsfw", nsfw);

    sendBtn.disabled = promptEl.disabled = true;

    try {
      const resp = await fetch("/chat", { method: "POST", body: formData });
      if (!resp.ok || !resp.body) throw new Error(`${resp.status} ${resp.statusText}`);
      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let acc = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        acc += decoder.decode(value, { stream: true });
        assistantNode.bubble.textContent = acc;
        const last = conv?.messages[conv.messages.length - 1];
        if (last && last.role === "assistant") { last.content = acc; conv.updatedAt = Date.now(); save(); }
        scrollToBottom();
      }
    } catch (err) {
      assistantNode.bubble.textContent = `请求失败: ${err.message}`;
    } finally {
      sendBtn.disabled = promptEl.disabled = false; promptEl.focus();
    }
  });

  if (!activeId || !getActiveConv()) newConversation();
  else { renderConvList(); renderMessages(); }

  window.addEventListener("resize", () => { if (window.innerWidth > 900) closeSidebar(); });

  loadPersonas();
  refreshCurrentPersonas();
});
