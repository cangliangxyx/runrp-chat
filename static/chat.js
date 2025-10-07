/*** chat.js ***/
import { appendMessage, ensureAssistantMessage, getActiveConv, save } from "./conversations.js";
import { scrollToBottom } from "./ui.js";

export function setupChat() {
  const form = document.getElementById("chat-form");
  const modelSel = document.getElementById("model");
  const systemSel = document.getElementById("system_rules");
  const promptEl = document.getElementById("prompt");
  const messagesEl = document.getElementById("messages");
  const sendBtn = form.querySelector('button[type="submit"]');
  const webInputEl = document.getElementById("web_input");

  promptEl.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const model = modelSel.value;
    const systemRule = systemSel.value;
    const prompt = promptEl.value.trim();
    if (!prompt) return;

    const nsfw = document.getElementById("nsfw-checkbox").checked ? "true" : "false";

    appendMessage("user", prompt, messagesEl);
    promptEl.value = "";

    const conv = getActiveConv();
    const assistantNode = ensureAssistantMessage(messagesEl);

    const formData = new FormData();
    formData.append("model", model);
    formData.append("system_rule", systemRule);
    formData.append("prompt", prompt);
    formData.append("conversation_id", conv?.id || "");
    formData.append("history", JSON.stringify(conv?.messages || []));
    formData.append("web_input", webInputEl?.value.trim() || "");
    formData.append("nsfw", nsfw);

    sendBtn.disabled = promptEl.disabled = true;

    try {
      const resp = await fetch("/chat", { method: "POST", body: formData });
      if (!resp.ok || !resp.body) throw new Error(`${resp.status} ${resp.statusText}`);
      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let acc = "";

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
              assistantNode.bubble.textContent = acc;
              const last = conv?.messages[conv.messages.length - 1];
              if (last && last.role === "assistant") { last.content = acc; conv.updatedAt = Date.now(); save(); }
              scrollToBottom(messagesEl);
            } else if (data.type === "error") {
              assistantNode.bubble.textContent = `[错误] ${data.error}`;
            }
          } catch {
            continue;
          }
        }
      }
    } catch (err) {
      assistantNode.bubble.textContent = `请求失败: ${err.message}`;
    } finally {
      sendBtn.disabled = promptEl.disabled = false;
      promptEl.focus();
    }
  });
}
