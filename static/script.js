document.getElementById("chat-form").addEventListener("submit", async function (e) {
  e.preventDefault();
  const model = document.getElementById("model").value;
  const prompt = document.getElementById("prompt").value;
  const responseEl = document.getElementById("response");
  responseEl.textContent = "";

  const formData = new FormData();
  formData.append("model", model);
  formData.append("prompt", prompt);

  try {
    const resp = await fetch("/chat", {
      method: "POST",
      body: formData
    });

    if (!resp.ok) {
      responseEl.textContent = `错误: ${resp.status} ${resp.statusText}`;
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      // 直接解码文本内容，不需要解析 JSON
      const chunk = decoder.decode(value, { stream: true });
      responseEl.textContent += chunk;
    }
  } catch (error) {
    responseEl.textContent = `请求失败: ${error.message}`;
  }
});
