(function () {
  const form = document.getElementById("chat-form");
  const modelSel = document.getElementById("model");
  const promptEl = document.getElementById("prompt");
  const messagesEl = document.getElementById("messages");
  const sendBtn = form.querySelector('button[type="submit"]');

  // 创建一条消息气泡（不显示 AI/你 文本，不显示头像）
  function createMessage(role, text = "") {
    const wrap = document.createElement("div");
    wrap.className = `msg ${role}`;

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text || "";

    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    return { wrap, bubble };
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      messagesEl.scrollTop = messagesEl.scrollHeight;
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    });
  }

  // Enter 发送 / Shift+Enter 换行
  promptEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const model = modelSel.value;
    const prompt = promptEl.value.trim();
    if (!prompt) return;

    // 1) 渲染用户气泡，清空输入框
    createMessage("user", prompt);
    scrollToBottom();
    promptEl.value = "";

    // 2) 预创建助手气泡，流式写入
    const assistant = createMessage("assistant", "");
    scrollToBottom();

    // 3) 发送请求
    const formData = new FormData();
    formData.append("model", model);
    formData.append("prompt", prompt);

    sendBtn.disabled = true;
    promptEl.disabled = true;

    try {
      const resp = await fetch("/chat", { method: "POST", body: formData });

      if (!resp.ok || !resp.body) {
        assistant.bubble.textContent = `错误: ${resp.status} ${resp.statusText}`;
        scrollToBottom();
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        assistant.bubble.textContent += chunk;
        scrollToBottom();
      }
    } catch (error) {
      assistant.bubble.textContent = `请求失败: ${error.message}`;
      scrollToBottom();
    } finally {
      sendBtn.disabled = false;
      promptEl.disabled = false;
      promptEl.focus();
    }
  });
})();
