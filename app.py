# app.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
import json
import uvicorn

from config.models import list_model_ids
from chat_service import stream_chat

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 在模块加载时设置基础日志（避免只在 __main__ 下配置）
root_logger = logging.getLogger()
if not root_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    model_ids = list_model_ids()
    return templates.TemplateResponse("index.html", {"request": request, "models": model_ids})


@app.post("/chat")
async def chat(
    model: str = Form(...),
    prompt: str = Form(...),
    history: str | None = Form(default=None),
    memory: str | None = Form(default=None),
    world_state: str | None = Form(default=None),
    conversation_id: str | None = Form(default=None),
):
    logging.getLogger(__name__).info(f"[route] 收到 /chat | model={model} | prompt_preview={prompt[:50]}")
    print(f"接收到聊天请求: model={model}, prompt={prompt[:50]}...")

    parsed_history = None
    parsed_memory = None
    parsed_world_state = None

    try:
        if history:
            parsed_history = json.loads(history)
        if memory:
            parsed_memory = json.loads(memory) if memory.strip().startswith("{") or memory.strip().startswith("[") else memory
        if world_state:
            parsed_world_state = json.loads(world_state)
    except Exception as e:
        logging.getLogger(__name__).warning(f"[route] 解析上下文失败: {e}")
        print(f"解析上下文失败: {e}")

    try:
        generator = stream_chat(
            model=model,
            prompt=prompt,
            history=parsed_history,
            memory=parsed_memory if isinstance(parsed_memory, str) else None,
            world_state=parsed_world_state,
            conversation_id=conversation_id,
        )
        print("创建了流式生成器")
        return StreamingResponse(
            generator,
            media_type="text/plain; charset=utf-8"
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"[route] 创建流式响应时出错: {e}")
        print(f"创建流式响应时出错: {e}")
        raise


if __name__ == "__main__":
    # 通过 uvicorn.run 指定 log_level，确保子进程也是 INFO
    print("启动服务：http://localhost:8080")
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True, log_level="info")