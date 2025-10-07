/*** conversations.js ***/
import { scrollToBottom } from "./ui.js";

const LS_KEY = "runrp_chat_conversations";
const LS_ACTIVE = "runrp_chat_active";

export let conversations = loadConversations();
export let activeId = loadActiveId();

function loadConversations() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    const data = raw ? JSON.parse(raw) : [];
    return Array.isArray(data) ? data : [];
  } catch { return []; }
}

function loadActiveId() { return localStorage.getItem(LS_ACTIVE) || ""; }

export function save() {
  localStorage.setItem(LS_KEY, JSON.stringify(conversations));
  localStorage.setItem(LS_ACTIVE, activeId || "");
}

export const getActiveConv = () => conversations.find(c => c.id === activeId) || null;

const uid = () => Math.random().toString(36).slice(2, 10);

export function newConversation(initialText = "", convList, messagesEl) {
  const id = uid();
  const title = (initialText || "新的对话").slice(0, 30);
  const conv = { id, title, messages: [], createdAt: Date.now(), updatedAt: Date.now() };
  conversations.unshift(conv);
  activeId = id;
  save();
  renderConvList(convList, messagesEl);
  renderMessages(messagesEl);
  return conv;
}

export function renderConvList(convList, messagesEl, closeSidebarFn) {
  convList.innerHTML = "";
  conversations.forEach(conv => {
    const item = document.createElement("div");
    item.className = `conv-item${conv.id === activeId ? " active" : ""}`;
    item.dataset.id = conv.id;

    const title = document.createElement("div");
    title.className = "conv-title";
    title.textContent = conv.title || "未命名会话";
    title.title = "双击编辑标题";
    title.addEventListener("dblclick", () => startEditTitle(conv.id, title, convList, messagesEl));

    const meta = document.createElement("div");
    meta.className = "conv-meta";
    meta.textContent = new Date(conv.updatedAt || Date.now()).toLocaleString();

    const actions = document.createElement("div");
    actions.className = "conv-actions";

    const btnEdit = document.createElement("button");
    btnEdit.className = "btn-icon";
    btnEdit.textContent = "✎";
    btnEdit.addEventListener("click", e => {
      e.stopPropagation();
      startEditTitle(conv.id, title, convList, messagesEl);
    });

    const btnDel = document.createElement("button");
    btnDel.className = "btn-icon";
    btnDel.textContent = "×";
    btnDel.addEventListener("click", e => {
      e.stopPropagation();
      if (confirm(`确认删除会话「${conv.title || "未命名会话"}」吗？`)) {
        conversations = conversations.filter(c => c.id !== conv.id);
        if (activeId === conv.id) activeId = conversations[0]?.id || "";
        save(); renderConvList(convList, messagesEl, closeSidebarFn); renderMessages(messagesEl);
        if (!conversations.length) newConversation("", convList, messagesEl);
      }
    });

    actions.append(btnEdit, btnDel);
    const wrap = document.createElement("div");
    wrap.append(title, meta, actions);
    item.appendChild(wrap);

    item.addEventListener("click", () => {
      activeId = conv.id;
      save();
      renderConvList(convList, messagesEl, closeSidebarFn);
      renderMessages(messagesEl);
      if (closeSidebarFn) closeSidebarFn();
    });

    convList.appendChild(item);
  });
}

export function startEditTitle(convId, titleEl, convList, messagesEl) {
  const conv = conversations.find(c => c.id === convId);
  if (!conv) return;
  const oldText = conv.title || "未命名会话";
  const input = document.createElement("input");
  input.type = "text";
  input.className = "title-input";
  input.value = oldText;
  titleEl.replaceWith(input);
  input.focus(); input.select();
  const finish = saveChange => {
    if (saveChange) conv.title = input.value.trim() || oldText;
    conv.updatedAt = Date.now();
    save();
    renderConvList(convList, messagesEl);
  };
  input.addEventListener("keydown", e => {
    if (e.key === "Enter") finish(true);
    else if (e.key === "Escape") finish(false);
  });
  input.addEventListener("blur", () => finish(true));
}

export function renderMessages(messagesEl) {
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
  scrollToBottom(messagesEl);
}

export function appendMessage(role, content, messagesEl) {
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
  scrollToBottom(messagesEl);
  return { conv, bubble };
}

export function ensureAssistantMessage(messagesEl) {
  const conv = getActiveConv();
  if (!conv) return appendMessage("assistant", "", messagesEl);
  const last = conv.messages[conv.messages.length - 1];
  if (!last || last.role !== "assistant") return appendMessage("assistant", "", messagesEl);
  const nodes = messagesEl.querySelectorAll(".msg.assistant .bubble");
  return { conv, bubble: nodes[nodes.length - 1] };
}
