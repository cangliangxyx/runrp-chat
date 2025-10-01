// sidebar.js – 侧边栏操作
export function setupSidebar(sidebarId, btnToggleId) {
  const sidebar = document.getElementById(sidebarId);
  const overlay = document.createElement("div");
  overlay.id = "sidebar-overlay";
  overlay.style.cssText = `position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.3);z-index:15;display:none;`;
  document.body.appendChild(overlay);

  function openSidebar() { sidebar.classList.add("open"); overlay.style.display = "block"; }
  function closeSidebar() { sidebar.classList.remove("open"); overlay.style.display = "none"; }
  overlay.addEventListener("click", closeSidebar);

  const btnToggle = document.getElementById(btnToggleId);
  btnToggle.addEventListener("click", () => sidebar.classList.contains("open") ? closeSidebar() : openSidebar());

  return { openSidebar, closeSidebar };
}