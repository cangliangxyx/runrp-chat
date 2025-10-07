/*** personas.js ***/
export async function loadPersonas() {
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

export async function updatePersonas() {
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

export async function refreshCurrentPersonas() {
  try {
    const res = await fetch("/personas");
    const data = await res.json();
    const current = data.personas.filter(p => p.selected).map(p => p.name).join(", ") || "无";
    document.getElementById("current-personas-display").textContent = current;
  } catch {}
}
