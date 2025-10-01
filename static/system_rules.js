// system_rules.js – 系统规则
export async function loadSystemRules() {
  try {
    const res = await fetch("/system_rules");
    const data = await res.json();
    const select = document.getElementById("system_rules");
    select.innerHTML = "";
    data.rules.forEach(rule => {
      const opt = document.createElement("option");
      opt.value = rule;
      opt.textContent = rule;
      select.appendChild(opt);
    });
    if (data.rules.includes("developer")) select.value = "developer";
  } catch (err) {
    console.error("加载 system_rules 失败:", err);
  }
}