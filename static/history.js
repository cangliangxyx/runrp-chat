/*** history.js ***/
import { getActiveConv, save, renderMessages } from "./conversations.js";

export function setupHistoryButtons() {
  const btnClearAll = document.getElementById("btn-clear-all");
  const btnClearHistory = document.getElementById("btn-clear-history");
  const btnReloadHistory = document.getElementById("btn-reload-history");

  btnClearAll.addEventListener("click", async () => {
    if (!confirm("确定要删除最后一条消息吗？")) return;
    try {
      const res = await fetch("/remove_last_entry", { method: "POST" });
      const data = await res.json();
      if (data.status === "ok") {
        const conv = getActiveConv();
        if (conv && conv.messages.length > 0) {
          conv.messages.pop();
          save();
          renderMessages(document.getElementById("messages"));
        }
        alert("已删除最后一条记录！");
      } else if (data.status === "empty") {
        alert("没有可删除的聊天记录！");
      } else {
        alert("删除失败：" + (data.message || "未知错误"));
      }
    } catch (err) {
      console.error("删除最后一条记录失败:", err);
      alert("无法连接服务器！");
    }
  });

  btnClearHistory.addEventListener("click", () => {
    if (confirm("确定要清空当前对话历史吗？")) {
      const conv = getActiveConv();
      if (conv) conv.messages = [];
      save();
      renderMessages(document.getElementById("messages"));
      fetch("/clear_history", { method: "POST" }).catch(() => {});
    }
  });

  if (btnReloadHistory) {
    btnReloadHistory.addEventListener("click", async () => {
      try {
        const res = await fetch("/reload_history", { method: "POST" });
        const data = await res.json();
        if (data.status === "ok") {
          alert("已从文件重新加载历史记录！");
        } else alert("重新加载失败！");
      } catch (err) {
        console.error("重新加载历史记录失败", err);
        alert("无法连接服务器！");
      }
    });
  }
}
