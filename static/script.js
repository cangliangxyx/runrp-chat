(() => {
  // DOM
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

  // 本地存储键
  const LS_KEY = "runrp_chat_conversations";
  const LS_ACTIVE = "runrp_chat_active";

  let conversations = loadConversations();
  let activeId = loadActiveId();

  // 工具函数
  const uid = () => Math.random().toString(36).slice(2, 10);
  const save = () => {
    localStorage.setItem(LS_KEY, JSON.stringify(conversations));
    localStorage.setItem(LS_ACTIVE, activeId || "");
  };
  function loadConversations() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      const data = raw ? JSON.parse(raw) : [];
      return Array.isArray(data) ? data : [];
    } catch { return []; }
  }
  function loadActiveId() { return localStorage.getItem(LS_ACTIVE) || ""; }
  const getActiveConv = () => conversations.find(c => c.id === activeId) || null;

  // 渲染侧边栏
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
      btnEdit.className = "btn-icon"; btnEdit.textContent = "✎";
      btnEdit.title = "修改标题";
      btnEdit.addEventListener("click", e => { e.stopPropagation(); startEditTitle(conv.id, title); });

      const btnDel = document.createElement("button");
      btnDel.className = "btn-icon"; btnDel.textContent = "×";
      btnDel.title = "删除会话";
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

      item.addEventListener("click", () => { activeId = conv.id; save(); renderConvList(); renderMessages(); closeSidebar(); });

      convList.appendChild(item);
    });
  }

  // 编辑标题
  function startEditTitle(convId, titleEl) {
    const conv = conversations.find(c => c.id === convId);
    if (!conv) return;
    const oldText = conv.title || "未命名会话";
    const input = document.createElement("input");
    input.type = "text"; input.className = "title-input"; input.value = oldText;
    titleEl.replaceWith(input);
    input.focus(); input.select();
    const finish = saveChange => {
      const text = input.value.trim();
      if (saveChange && text) { conv.title = text; conv.updatedAt = Date.now(); save(); }
      renderConvList();
    };
    input.addEventListener("keydown", e => {
      if (e.key === "Enter") { e.preventDefault(); finish(true); }
      else if (e.key === "Escape") { e.preventDefault(); finish(false); }
    });
    input.addEventListener("blur", () => finish(true));
  }

  // 渲染消息
  function renderMessages() {
    messagesEl.innerHTML = "";
    const conv = getActiveConv();
    if (!conv) return;
    conv.messages.forEach(msg => {
      const wrap = document.createElement("div"); wrap.className = `msg ${msg.role}`;
      const bubble = document.createElement("div"); bubble.className = "bubble"; bubble.textContent = msg.content;
      wrap.appendChild(bubble); messagesEl.appendChild(wrap);
    });
    scrollToBottom();
  }

  // 新会话
  function newConversation(initialText = "") {
    const id = uid();
    const title = (initialText || "新的对话").slice(0, 30);
    const conv = { id, title, messages: [], createdAt: Date.now(), updatedAt: Date.now() };
    conversations.unshift(conv); activeId = id; save(); renderConvList(); renderMessages();
    return conv;
  }

  // 添加消息
  function appendMessage(role, content) {
    let conv = getActiveConv(); if (!conv) conv = newConversation(content);
    conv.messages.push({ role, content, ts: Date.now() });
    conv.updatedAt = Date.now();
    save();
    const wrap = document.createElement("div"); wrap.className = `msg ${role}`;
    const bubble = document.createElement("div"); bubble.className = "bubble"; bubble.textContent = content;
    wrap.appendChild(bubble); messagesEl.appendChild(wrap);
    scrollToBottom();
    return { conv, bubble };
  }

  // 确保有 assistant 消息节点
  function ensureAssistantMessage() {
    const conv = getActiveConv(); if (!conv) return appendMessage("assistant", "");
    const last = conv.messages[conv.messages.length - 1];
    if (!last || last.role !== "assistant") return appendMessage("assistant", "");
    const nodes = messagesEl.querySelectorAll(".msg.assistant .bubble");
    return { conv, bubble: nodes[nodes.length - 1] };
  }

  function scrollToBottom() { requestAnimationFrame(() => messagesEl.scrollTop = messagesEl.scrollHeight); }

  // 侧栏控制
  const openSidebar = () => sidebar.classList.add("open");
  const closeSidebar = () => sidebar.classList.remove("open");
  btnToggle?.addEventListener("click", () => sidebar.classList.toggle("open"));
  btnNew?.addEventListener("click", () => { newConversation(); openSidebar(); });
  btnClearAll?.addEventListener("click", () => {
    if (confirm("确认清空所有历史会话吗？")) { conversations = []; activeId = ""; save(); renderConvList(); renderMessages(); newConversation(); }
  });

  // 回车发送
  promptEl.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });

  // 表单提交（流式聊天）
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const model = modelSel.value;
    const systemRule = systemSel.value;
    const prompt = promptEl.value.trim();
    if (!prompt) return;

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

  // 初始化
  if (!activeId || !getActiveConv()) newConversation();
  else { renderConvList(); renderMessages(); }
})();
