
// conversations.js – 会话管理
export const LS_KEY = "runrp_chat_conversations";
export const LS_ACTIVE = "runrp_chat_active";

export const uid = () => Math.random().toString(36).slice(2, 10);

export function loadConversations() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    const data = raw ? JSON.parse(raw) : [];
    return Array.isArray(data) ? data : [];
  } catch { return []; }
}

export function loadActiveId() { return localStorage.getItem(LS_ACTIVE) || ""; }

export function saveConversations(conversations, activeId) {
  localStorage.setItem(LS_KEY, JSON.stringify(conversations));
  localStorage.setItem(LS_ACTIVE, activeId || "");
}

export function getActiveConv(conversations, activeId) {
  return conversations.find(c => c.id === activeId) || null;
}