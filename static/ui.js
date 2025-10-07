/*** ui.js ***/
export function scrollToBottom(messagesEl) {
  requestAnimationFrame(() => messagesEl.scrollTop = messagesEl.scrollHeight);
}

export function createSidebarOverlay() {
  const overlay = document.createElement("div");
  overlay.id = "sidebar-overlay";
  overlay.style.cssText = `position:fixed;top:0;left:0;width:100%;height:100%;
    background:rgba(0,0,0,.3);z-index:15;display:none;`;
  document.body.appendChild(overlay);
  return overlay;
}

export function openSidebar(sidebar, overlay) {
  sidebar.classList.add("open");
  overlay.style.display = "block";
}

export function closeSidebar(sidebar, overlay) {
  sidebar.classList.remove("open");
  overlay.style.display = "none";
}
