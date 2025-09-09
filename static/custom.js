// 加载可选人物列表
async function loadPersonas() {
  const res = await fetch("/personas");
  const data = await res.json();
  const container = document.getElementById("persona-list");
  container.innerHTML = "";
  data.personas.forEach(p => {
    const div = document.createElement("div");
    div.innerHTML = `<label><input type="checkbox" value="${p.name}" ${p.selected ? "checked" : ""}> ${p.name}</label>`;
    container.appendChild(div);
  });
}

// 更新选中人物
async function updatePersonas() {
  const checkboxes = document.querySelectorAll("#persona-list input[type=checkbox]");
  const selected = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value).join(",");
  const formData = new FormData();
  formData.append("selected", selected);
  await fetch("/personas", { method: "POST", body: formData });
  await refreshCurrentPersonas();
}

// 刷新当前出场人物显示
async function refreshCurrentPersonas() {
  const res = await fetch("/personas");
  const data = await res.json();
  const current = data.personas.filter(p => p.selected).map(p => p.name).join(", ") || "无";
  document.getElementById("current-personas-display").textContent = current;
}

// 清空历史按钮事件
function setupClearHistory() {
  document.getElementById("btn-clear-history").addEventListener("click", () => {
    if (confirm("确定要清空当前对话历史吗？")) {
      localStorage.removeItem("chat_history");
      fetch("/clear_history", { method: "POST" }).catch(() => {});
      document.getElementById("messages").innerHTML = "";
    }
  });
}

// 页面初始化
document.addEventListener("DOMContentLoaded", () => {
  loadPersonas();
  refreshCurrentPersonas();
  document.getElementById("btn-update-personas").addEventListener("click", updatePersonas);
  setupClearHistory();
  setInterval(refreshCurrentPersonas, 50000000);
});

// 动态加载 system_rules
document.addEventListener("DOMContentLoaded", () => {
  fetch("/system_rules")
    .then((res) => res.json())
    .then((data) => {
      const select = document.getElementById("system_rules");
      select.innerHTML = ""; // 清空原本的静态选项
      data.rules.forEach((rule) => {
        const opt = document.createElement("option");
        opt.value = rule;
        opt.textContent = rule;
        select.appendChild(opt);
      });
      // 默认选中 developer（如果存在）
      if (data.rules.includes("developer")) {
        select.value = "developer";
      }
    })
    .catch((err) => console.error("加载 system_rules 失败:", err));
});



