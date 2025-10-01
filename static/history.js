// history.js – 历史会话加载与清空
export function setupHistoryButtons({ reloadId, clearId, getActiveConv, saveFn, renderMessages }) {
  const btnReload = document.getElementById(reloadId);
  if (btnReload) {
    btnReload.addEventListener("click", async () => {
      try {
        const res = await fetch("/reload_history", { method: "POST" });
        const data = await res.json();
        if (data.status === "ok") alert("已从文件重新加载历史记录！");
        else alert("重新加载失败！");
      } catch {
        alert("无法连接服务器！");
      }
    });
  }

  const btnClear = document.getElementById(clearId);
  if (btnClear) {
    btnClear.addEventListener("click", () => {
      if (!confirm("确定要清空当前对话历史吗？")) return;
      const conv = getActiveConv();
      if (conv) conv.messages = [];
      saveFn();
      renderMessages();
      fetch("/clear_history", { method: "POST" }).catch(() => {});
    });
  }
}