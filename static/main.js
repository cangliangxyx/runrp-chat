/*** main.js ***/
import { loadPersonas, updatePersonas, refreshCurrentPersonas } from "./personas.js";
import { loadSystemRules } from "./systemRules.js";
import { conversations, activeId, renderConvList, renderMessages, newConversation } from "./conversations.js";
import { setupChat } from "./chat.js";
import { setupHistoryButtons } from "./history.js";
import { createSidebarOverlay, openSidebar, closeSidebar } from "./ui.js";

document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const convList = document.getElementById("conv-list");
  const messagesEl = document.getElementById("messages");
  const btnToggle = document.getElementById("btn-toggle");
  const btnNew = document.getElementById("btn-new");

  const overlay = createSidebarOverlay();
  overlay.addEventListener("click", () => closeSidebar(sidebar, overlay));

  btnToggle.addEventListener("click", () =>
    sidebar.classList.contains("open") ? closeSidebar(sidebar, overlay) : openSidebar(sidebar, overlay)
  );
  btnNew.addEventListener("click", () => { newConversation("", convList, messagesEl); openSidebar(sidebar, overlay); });

  if (!activeId || !conversations.find(c => c.id === activeId)) newConversation("", convList, messagesEl);
  else { renderConvList(convList, messagesEl); renderMessages(messagesEl); }

  loadPersonas();
  loadSystemRules();
  setupChat();
  setupHistoryButtons();

  document.getElementById("btn-update-personas").addEventListener("click", updatePersonas);
  window.addEventListener("resize", () => { if (window.innerWidth > 900) closeSidebar(sidebar, overlay); });
  refreshCurrentPersonas();
});
