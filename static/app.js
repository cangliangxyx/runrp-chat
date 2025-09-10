// /static/app.js

document.addEventListener("DOMContentLoaded", () => {
  /*** -------------------- 人物管理 -------------------- ***/
  // 加载可用的人物 (personas)，并渲染到页面复选框列表
  async function loadPersonas() {
    try {
      const res = await fetch("/personas");          // 请求后端获取人物列表
      const data = await res.json();
      const container = document.getElementById("persona-list");
      container.innerHTML = "";                      // 清空旧列表
      data.personas.forEach(p => {
        // 为每个人物生成一个复选框
        const div = document.createElement("div");
        div.innerHTML = `<label><input type="checkbox" value="${p.name}" ${p.selected ? "checked" : ""}> ${p.name}</label>`;
        container.appendChild(div);
      });
      refreshCurrentPersonas();                      // 刷新当前已选中的人物显示
    } catch (err) {
      console.error("加载 personas 失败:", err);
    }
  }

  // 将用户勾选的人物状态提交到后端
  async function updatePersonas() {
    const checkboxes = document.querySelectorAll("#persona-list input[type=checkbox]");
    const selected = Array.from(checkboxes)
      .filter(cb => cb.checked)
      .map(cb => cb.value)
      .join(",");
    const formData = new FormData();
    formData.append("selected", selected);
    await fetch("/personas", { method: "POST", body: formData }); // 提交更新
    refreshCurrentPersonas(); // 更新当前显示
  }

  // 刷新当前已选中的人物显示区域
  async function refreshCurrentPersonas() {
    try {
      const res = await fetch("/personas");
      const data = await res.json();
      // 过滤出选中的人物并拼接成字符串显示，否则显示“无”
      const current = data.personas.filter(p => p.selected).map(p => p.name).join(", ") || "无";
      document.getElementById("current-personas-display").textContent = current;
    } catch {}
  }

  document.getElementById("btn-update-personas").addEventListener("click", updatePersonas);

  /*** -------------------- system_rules 动态加载 -------------------- ***/
  // 从后端获取 system_rules 规则列表，动态填充下拉菜单
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
      // 如果有 developer 规则，默认选中
      if (data.rules.includes("developer")) select.value = "developer";
    })
    .catch(err => console.error("加载 system_rules 失败:", err));

  /*** -------------------- 会话管理 -------------------- ***/
  // 获取 DOM 元素引用
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

  // 侧边栏遮罩层，用于点击空白区域关闭侧边栏
  const overlay = document.createElement("div");
  overlay.id = "sidebar-overlay";
  overlay.style.cssText = `position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.3);z-index:15;display:none;`;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", closeSidebar);

  // LocalStorage key 常量
  const LS_KEY = "runrp_chat_conversations"; // 用于存储会话列表
  const LS_ACTIVE = "runrp_chat_active";     // 用于存储当前激活会话 ID

  const uid = () => Math.random().toString(36).slice(2, 10); // 简单生成随机 ID
  let conversations = loadConversations();  // 从本地加载历史会话
  let activeId = loadActiveId();            // 加载当前激活会话 ID

  // 从 localStorage 读取会话列表
  function loadConversations() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      const data = raw ? JSON.parse(raw) : [];
      return Array.isArray(data) ? data : [];
    } catch { return []; }
  }

  // 从 localStorage 读取当前激活会话 ID
  function loadActiveId() { return localStorage.getItem(LS_ACTIVE) || ""; }

  // 保存当前会话和激活 ID 到 localStorage
  function save() {
    localStorage.setItem(LS_KEY, JSON.stringify(conversations));
    localStorage.setItem(LS_ACTIVE, activeId || "");
  }

  const getActiveConv = () => conversations.find(c => c.id === activeId) || null;

  // 渲染会话列表到侧边栏
  function renderConvList() {
    convList.innerHTML = "";
    conversations.forEach(conv => {
      const item = document.createElement("div");
      item.className = `conv-item${conv.id === activeId ? " active" : ""}`;
      item.dataset.id = conv.id;

      // 标题显示
      const title = document.createElement("div");
      title.className = "conv-title";
      title.textContent = conv.title || "未命名会话";
      title.title = "双击编辑标题";
      title.addEventListener("dblclick", () => startEditTitle(conv.id, title));

      // 会话更新时间
      const meta = document.createElement("div");
      meta.className = "conv-meta";
      meta.textContent = new Date(conv.updatedAt || Date.now()).toLocaleString();

      // 编辑 / 删除按钮区域
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
          // 删除该会话
          conversations = conversations.filter(c => c.id !== conv.id);
          if (activeId === conv.id) activeId = conversations[0]?.id || "";
          save(); renderConvList(); renderMessages();
          if (!conversations.length) newConversation(); // 没有会话时新建一个
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

  // 开启标题编辑模式
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

  // 渲染当前会话的所有消息到聊天区
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

  // 新建一个会话
  function newConversation(initialText = "") {
    const id = uid();
    const title = (initialText || "新的对话").slice(0, 30);
    const conv = { id, title, messages: [], createdAt: Date.now(), updatedAt: Date.now() };
    conversations.unshift(conv); activeId = id; save(); renderConvList(); renderMessages();
    return conv;
  }

  // 添加一条新消息到当前会话
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

  // 确保有一个助手的气泡可写入，用于流式响应
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

  // 打开/关闭侧边栏
  function openSidebar() { sidebar.classList.add("open"); overlay.style.display = "block"; }
  function closeSidebar() { sidebar.classList.remove("open"); overlay.style.display = "none"; }

  // 侧边栏按钮绑定
  btnToggle.addEventListener("click", () => sidebar.classList.contains("open") ? closeSidebar() : openSidebar());
  btnNew.addEventListener("click", () => { newConversation(); openSidebar(); });
  btnClearAll.addEventListener("click", () => {
    if (confirm("确认清空所有历史会话吗？")) { conversations = []; activeId = ""; save(); renderConvList(); renderMessages(); newConversation(); }
  });

  // 清空当前会话的聊天记录
  document.getElementById("btn-clear-history").addEventListener("click", () => {
    if (confirm("确定要清空当前对话历史吗？")) {
      const conv = getActiveConv();
      if (conv) conv.messages = [];
      save(); renderMessages();
      fetch("/clear_history", { method: "POST" }).catch(() => {});
    }
  });

  // 点击聊天区空白处关闭侧边栏
  messagesEl.addEventListener("click", e => { if (!e.target.closest(".bubble")) closeSidebar(); });

  // 输入框支持按回车发送（Shift+Enter 换行）
  promptEl.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });

  // 表单提交事件，向后端发送 prompt
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const model = modelSel.value;
    const systemRule = systemSel.value;
    const prompt = promptEl.value.trim();
    if (!prompt) return;

    appendMessage("user", prompt);   // 显示用户消息
    promptEl.value = "";

    const conv = getActiveConv();
    const assistantNode = ensureAssistantMessage(); // 创建助手回复占位气泡

    // 构建请求数据
    const formData = new FormData();
    formData.append("model", model);
    formData.append("system_rule", systemRule);
    formData.append("prompt", prompt);
    formData.append("conversation_id", conv?.id || "");
    formData.append("history", JSON.stringify(conv?.messages || []));
    formData.append("web_input", webInputEl?.value.trim() || "");

    sendBtn.disabled = promptEl.disabled = true; // 禁用输入避免重复发送

    try {
      // 向 /chat 发起 POST 请求，并逐块读取响应实现流式更新
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

  // 如果没有会话，自动新建一个
  if (!activeId || !getActiveConv()) newConversation();
  else { renderConvList(); renderMessages(); }

  // 大屏幕时关闭侧边栏
  window.addEventListener("resize", () => { if (window.innerWidth > 900) closeSidebar(); });

  // 初始化人物和显示
  loadPersonas();
  refreshCurrentPersonas();
});
