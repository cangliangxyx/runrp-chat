document.addEventListener("DOMContentLoaded", () => {
  /*** =====================
   * 人物管理
   * ===================== */
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

  /*** =====================
   * system_rules 动态加载
   * ===================== */
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

  /*** =====================
   * 会话管理
   * ===================== */
  const form = document.getElementById("chat-form");
  const modelSel = document.getElementById("model");
  const systemSel = document.getElementById("system_rules");
  const promptEl = document.getElementById("prompt");
  const messagesEl = document.getElementById("messages");
  const sendBtn = form.querySelector('button[type="submit"]');
  const convList = document.getElementById("conv-list");
  const webInputEl = document.getElementById("web_input");

  const LS_KEY = "runrp_chat_conversations";
  const LS_ACTIVE = "runrp_chat_active";

  // 生成随机 ID
  const uid = () => Math.random().toString(36).slice(2, 10);

  // 读取本地存储
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

  /** 渲染会话列表 */
  function renderConvList() {
    convList.innerHTML = "";
    conversations.forEach(conv => {
      const item = document.createElement("div");
      item.className = `conv-item${conv.id === activeId ? " active" : ""}`;
      item.dataset.id = conv.id;

      // 会话标题
      const title = document.createElement("div");
      title.className = "conv-title";
      title.textContent = conv.title || "未命名会话";
      title.title = "双击编辑标题";

      // 更新时间
      const meta = document.createElement("div");
      meta.className = "conv-meta";
      meta.textContent = new Date(conv.updatedAt || Date.now()).toLocaleString();

      // 删除按钮
      const actions = document.createElement("div");
      actions.className = "conv-actions";
      const btnDel = document.createElement("button");
      btnDel.className = "btn-icon"; btnDel.textContent = "×";
      btnDel.addEventListener("click", e => {
        e.stopPropagation();
        if (confirm(`确认删除会话「${conv.title || "未命名会话"}」吗？`)) {
          conversations = conversations.filter(c => c.id !== conv.id);
          if (activeId === conv.id) activeId = conversations[0]?.id || "";
          save(); renderConvList(); renderMessages();
          if (!conversations.length) newConversation();
        }
      });
      actions.appendChild(btnDel);

      // 组合会话项
      const wrap = document.createElement("div");
      wrap.append(title, meta, actions);
      item.appendChild(wrap);

      // 点击切换会话
      item.addEventListener("click", () => {
        activeId = conv.id; save(); renderConvList(); renderMessages();
      });

      convList.appendChild(item);
    });
  }

  /** 新建会话 */
  function newConversation(initialText = "") {
    const id = uid();
    const title = (initialText || "新的对话").slice(0, 30);
    const conv = { id, title, messages: [], createdAt: Date.now(), updatedAt: Date.now() };
    conversations.unshift(conv);
    activeId = id;
    save();
    renderConvList();
    renderMessages();
    return conv;
  }

  /** 渲染消息 */
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

  /** 追加消息 */
  function appendMessage(role, content) {
    let conv = getActiveConv();
    if (!conv) conv = newConversation(content);
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

  /** 保证有 AI 消息节点用于流式更新 */
  function ensureAssistantMessage() {
    const conv = getActiveConv();
    if (!conv) return appendMessage("assistant", "");
    const last = conv.messages[conv.messages.length - 1];
    if (!last || last.role !== "assistant") return appendMessage("assistant", "");
    const nodes = messagesEl.querySelectorAll(".msg.assistant .bubble");
    return { conv, bubble: nodes[nodes.length - 1] };
  }

  /** 滚动到底部 */
  function scrollToBottom() {
    requestAnimationFrame(() => messagesEl.scrollTop = messagesEl.scrollHeight);
  }

  /** 发送消息 */
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const prompt = promptEl.value.trim();
    if (!prompt) return;

    appendMessage("user", prompt);
    promptEl.value = "";

    const conv = getActiveConv();
    const assistantNode = ensureAssistantMessage();

    const formData = new FormData();
    formData.append("model", modelSel.value);
    formData.append("system_rule", systemSel.value);
    formData.append("prompt", prompt);
    formData.append("conversation_id", conv?.id || "");
    formData.append("history", JSON.stringify(conv?.messages || []));
    formData.append("web_input", webInputEl?.value.trim() || "");
    formData.append("nsfw", document.getElementById("nsfw-checkbox").checked ? "true" : "false");

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

        // 实时保存
        const last = conv?.messages[conv.messages.length - 1];
        if (last && last.role === "assistant") {
          last.content = acc;
          conv.updatedAt = Date.now();
          save();
        }
        scrollToBottom();
      }
    } catch (err) {
      assistantNode.bubble.textContent = `请求失败: ${err.message}`;
    } finally {
      sendBtn.disabled = promptEl.disabled = false;
      promptEl.focus();
    }
  });

  /** 初始化：如果没有会话则创建新会话 */
  if (!activeId || !getActiveConv()) newConversation();
  else { renderConvList(); renderMessages(); }

  /** 快捷键：Enter 发送消息，Shift+Enter 换行 */
  promptEl.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  /** 清空当前对话历史 */
  document.getElementById("btn-clear-history").addEventListener("click", () => {
    if (confirm("确定要清空当前对话历史吗？")) {
      const conv = getActiveConv();
      if (conv) conv.messages = [];
      save();
      renderMessages();
      fetch("/clear_history", { method: "POST" }).catch(() => {});
    }
  });

  /** 页面加载时初始化人物 */
  loadPersonas();
  refreshCurrentPersonas();
});
