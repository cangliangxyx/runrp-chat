// chat_form.js – 表单提交、流式输出
export function setupChatForm({ formId, promptId, sendBtnId, messagesId, webInputId }) {
  const form = document.getElementById(formId);
  const promptEl = document.getElementById(promptId);
  const messagesEl = document.getElementById(messagesId);
  const sendBtn = document.getElementById(sendBtnId);
  const webInputEl = document.getElementById(webInputId);

  // 消息滚动到底部
  const scrollToBottom = () => requestAnimationFrame(() => messagesEl.scrollTop = messagesEl.scrollHeight);

  // 新消息追加
  const appendMessage = (conv, role, content, saveFn) => {
    conv.messages.push({ role, content, ts: Date.now() });
    conv.updatedAt = Date.now();
    saveFn();
    const wrap = document.createElement("div");
    wrap.className = `msg ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = content;
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    scrollToBottom();
    return { conv, bubble };
  };

  // 表单提交
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const model = document.getElementById("model").value;
    const systemRule = document.getElementById("system_rules").value;
    const prompt = promptEl.value.trim();
    if (!prompt) return;

    const nsfw = document.getElementById("nsfw-checkbox").checked ? "true" : "false";
    promptEl.value = "";

    sendBtn.disabled = promptEl.disabled = true;

    try {
      const formData = new FormData();
      formData.append("model", model);
      formData.append("system_rule", systemRule);
      formData.append("prompt", prompt);
      formData.append("web_input", webInputEl?.value.trim() || "");
      formData.append("nsfw", nsfw);

      const resp = await fetch("/chat", { method: "POST", body: formData });
      if (!resp.ok || !resp.body) throw new Error(`${resp.status} ${resp.statusText}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "", acc = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let lines = buffer.split(/\r?\n/);
        buffer = lines.pop() || "";

        for (let line of lines) {
          line = line.trim();
          if (!line || line === "[DONE]") continue;
          try {
            const data = JSON.parse(line);
            if (data.type === "chunk" && data.content) {
              acc += data.content;
              messagesEl.lastChild.querySelector(".bubble").textContent = acc;
              scrollToBottom();
            }
          } catch {}
        }
      }
    } catch (err) {
      messagesEl.lastChild.querySelector(".bubble").textContent = `请求失败: ${err.message}`;
    } finally {
      sendBtn.disabled = promptEl.disabled = false;
      promptEl.focus();
    }
  });

  promptEl.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
}