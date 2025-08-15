(function () {
  // DOM
  const form = document.getElementById("chat-form");
  const modelSel = document.getElementById("model");
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

  function uid() { return Math.random().toString(36).slice(2, 10); }
  function save() {
    localStorage.setItem(LS_KEY, JSON.stringify(conversations));
    localStorage.setItem(LS_ACTIVE, activeId || "");
  }
  function loadConversations() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      const data = raw ? JSON.parse(raw) : [];
      return Array.isArray(data) ? data : [];
    } catch { return []; }
  }
  function loadActiveId() { return localStorage.getItem(LS_ACTIVE) || ""; }
  function getActiveConv() { return conversations.find(c => c.id === activeId) || null; }

  function renderConvList() {
    convList.innerHTML = "";
    conversations.forEach(conv => {
      const item = document.createElement("div");
      item.className = "conv-item" + (conv.id === activeId ? " active" : "");
      item.dataset.id = conv.id;

      const titleWrap = document.createElement("div");
      titleWrap.style.display = "flex";
      titleWrap.style.flexDirection = "column";
      titleWrap.style.minWidth = 0;

      const title = document.createElement("div");
      title.className = "conv-title";
      title.textContent = conv.title || "未命名会话";
      title.title = "双击编辑标题";
      title.addEventListener("dblclick", (e) => { e.stopPropagation(); startEditTitle(conv.id, title); });

      const meta = document.createElement("div");
      meta.className = "conv-meta";
      meta.textContent = new Date(conv.updatedAt || Date.now()).toLocaleString();

      titleWrap.appendChild(title);
      titleWrap.appendChild(meta);

      const actions = document.createElement("div");
      actions.className = "conv-actions";

      const btnEdit = document.createElement("button");
      btnEdit.className = "btn-icon";
      btnEdit.title = "修改标题";
      btnEdit.textContent = "✎";
      btnEdit.addEventListener("click", (ev) => { ev.stopPropagation(); startEditTitle(conv.id, title); });

      const btnDel = document.createElement("button");
      btnDel.className = "btn-icon";
      btnDel.title = "删除此会话";
      btnDel.textContent = "×";
      btnDel.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const ok = confirm(`确认删除会话「${conv.title || "未命名会话"}」吗？`);
        if (!ok) return;
        const idx = conversations.findIndex(c => c.id === conv.id);
        if (idx >= 0) conversations.splice(idx, 1);
        if (activeId === conv.id) activeId = conversations[0]?.id || "";
        save(); renderConvList(); renderMessages();
        if (!conversations.length) newConversation();
      });

      actions.appendChild(btnEdit);
      actions.appendChild(btnDel);

      item.addEventListener("click", () => {
        activeId = conv.id;
        save(); renderConvList(); renderMessages(); closeSidebarOnMobile();
      });

      item.appendChild(titleWrap);
      item.appendChild(actions);
      convList.appendChild(item);
    });
  }

  function startEditTitle(convId, titleEl) {
    const conv = conversations.find(c => c.id === convId);
    if (!conv) return;
    const oldText = conv.title || "未命名会话";
    const input = document.createElement("input");
    input.type = "text";
    input.className = "title-input";
    input.value = oldText;
    input.maxLength = 100;
    input.placeholder = "请输入标题";
    titleEl.replaceWith(input);
    input.focus(); input.select();
    const finish = (saveChange) => {
      const text = input.value.trim();
      if (saveChange && text && text !== oldText) {
        conv.title = text; conv.updatedAt = Date.now(); save();
      }
      renderConvList();
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); finish(true); }
      else if (e.key === "Escape") { e.preventDefault(); finish(false); }
    });
    input.addEventListener("blur", () => finish(true));
  }

  function renderMessages() {
    messagesEl.innerHTML = "";
    const conv = getActiveConv();
    if (!conv || !Array.isArray(conv.messages)) return;
    conv.messages.forEach(msg => {
      const wrap = document.createElement("div");
      wrap.className = `msg ${msg.role}`;
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = msg.content || "";
      wrap.appendChild(bubble);
      messagesEl.appendChild(wrap);
    });
    scrollToBottom();
  }

  function newConversation(initialUserText = "") {
    const id = uid();
    const title = (initialUserText || "新的对话").slice(0, 30);
    const conv = { id, title, messages: [], createdAt: Date.now(), updatedAt: Date.now() };
    conversations.unshift(conv); activeId = id; save(); renderConvList(); renderMessages();
    return conv;
  }

  function updateTitleIfNeeded(conv) {
    const firstUser = conv.messages.find(m => m.role === "user");
    if (firstUser) conv.title = firstUser.content.slice(0, 30);
  }

  function appendMessage(role, content) {
    let conv = getActiveConv(); if (!conv) conv = newConversation(content);
    conv.messages.push({ role, content, ts: Date.now() });
    conv.updatedAt = Date.now(); updateTitleIfNeeded(conv); save();
    const wrap = document.createElement("div"); wrap.className = `msg ${role}`;
    const bubble = document.createElement("div"); bubble.className = "bubble"; bubble.textContent = content;
    wrap.appendChild(bubble); messagesEl.appendChild(wrap); scrollToBottom();
    return { conv, wrap, bubble };
  }

  function ensureAssistantMessage() {
    const conv = getActiveConv(); if (!conv) return appendMessage("assistant", "");
    const last = conv.messages[conv.messages.length - 1];
    if (!last || last.role !== "assistant") return appendMessage("assistant", "");
    const nodes = messagesEl.querySelectorAll(".msg.assistant .bubble");
    if (nodes.length) return { conv, wrap: nodes[nodes.length - 1].parentElement, bubble: nodes[nodes.length - 1] };
    return appendMessage("assistant", "");
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      const ctn = document.scrollingElement || document.documentElement;
      messagesEl.scrollTop = messagesEl.scrollHeight;
      window.scrollTo({ top: ctn.scrollHeight, behavior: "smooth" });
    });
  }

  function openSidebar() { sidebar.classList.add("open"); }
  function closeSidebarOnMobile() { sidebar.classList.remove("open"); }
  document.getElementById("btn-toggle")?.addEventListener("click", () => {
    if (sidebar.classList.contains("open")) closeSidebarOnMobile(); else openSidebar();
  });
  btnNew?.addEventListener("click", () => { newConversation(); openSidebar(); });
  btnClearAll?.addEventListener("click", () => {
    const ok = confirm("确认清空所有历史会话吗？此操作不可撤销。");
    if (!ok) return;
    conversations = []; activeId = ""; save(); renderConvList(); renderMessages(); newConversation();
  });

  // 发送逻辑（流式）+ 携带历史与会话ID
  promptEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    const model = modelSel.value;
    const prompt = promptEl.value.trim();
    if (!prompt) return;

    appendMessage("user", prompt);
    promptEl.value = "";

    let conv = getActiveConv();
    const assistantNode = ensureAssistantMessage();

    const formData = new FormData();
    formData.append("model", model);
    formData.append("prompt", prompt);
    formData.append("conversation_id", conv?.id || "");
    // 携带完整历史，由后端做“摘要+滑窗”装配
    formData.append("history", JSON.stringify(conv?.messages || []));
    // 如有自定义世界状态/记忆，可按需扩展
    // formData.append("world_state", JSON.stringify(conv?.world_state || {}));
    // formData.append("memory", conv?.memory || "");

    sendBtn.disabled = true; promptEl.disabled = true;

    try {
      const resp = await fetch("/chat", { method: "POST", body: formData });
      if (!resp.ok || !resp.body) {
        const err = `错误: ${resp.status} ${resp.statusText}`;
        assistantNode.bubble.textContent = err;
        conv = getActiveConv();
        if (conv) {
          const last = conv.messages[conv.messages.length - 1];
          if (last && last.role === "assistant") { last.content = err; conv.updatedAt = Date.now(); save(); renderConvList(); }
        }
        scrollToBottom(); return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let acc = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        acc += chunk;
        assistantNode.bubble.textContent = acc;

        conv = getActiveConv();
        if (conv) {
          const last = conv.messages[conv.messages.length - 1];
          if (last && last.role === "assistant") {
            last.content = acc; conv.updatedAt = Date.now(); save();
          }
        }
        scrollToBottom();
      }

      conv = getActiveConv();
      if (conv) { conv.updatedAt = Date.now(); save(); renderConvList(); }
    } catch (error) {
      const failMsg = `请求失败: ${error.message}`;
      assistantNode.bubble.textContent = failMsg;
      conv = getActiveConv();
      if (conv) {
        const last = conv.messages[conv.messages.length - 1];
        if (last && last.role === "assistant") { last.content = failMsg; conv.updatedAt = Date.now(); save(); renderConvList(); }
      }
      scrollToBottom();
    } finally {
      sendBtn.disabled = false; promptEl.disabled = false; promptEl.focus();
    }
  });

  // 初始化
  if (!activeId || !getActiveConv()) { newConversation(); }
  else { renderConvList(); renderMessages(); }
})();
