const streamCheckbox = document.getElementById('stream-checkbox');
const chatForm = document.getElementById('chat-form');
const promptBox = document.getElementById('prompt');

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const promptText = promptBox.value;
  const model = document.getElementById('model').value;
  const systemRule = document.getElementById('system_rules').value;
  const webInput = document.getElementById('web_input').value;
  const nsfw = document.getElementById('nsfw-checkbox').checked ? "true" : "false";
  const stream = streamCheckbox.checked ? "true" : "false"; // ✅ 转为字符串

  const formData = new FormData();
  formData.append('model', model);
  formData.append('prompt', promptText);
  formData.append('system_rule', systemRule);
  formData.append('web_input', webInput);
  formData.append('nsfw', nsfw);
  formData.append('stream', stream); // ✅ 字符串形式发送

  const response = await fetch('/chat', {
    method: 'POST',
    body: formData
  });

  if (stream === "true") {
    // 流式解析
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        const data = JSON.parse(line);
        if (data.type === 'chunk') {
          appendMessage('assistant', data.content);
        } else if (data.type === 'end') {
          appendMessage('assistant', '\n[END]');
        }
      }
    }
  } else {
    // 非流式一次性返回
    const text = await response.text();
    try {
      const parsed = JSON.parse(text.trim());
      if (parsed.type === 'end' || parsed.full) {
        appendMessage('assistant', parsed.full || '');
      }
    } catch (err) {
      appendMessage('assistant', '[解析失败]');
    }
  }
});
