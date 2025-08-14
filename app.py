# app.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
import uvicorn

from config.models import model_registry, list_model_ids
from chat_service import stream_chat

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 确保获取正确的 logger
logger = logging.getLogger(__name__)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    model_ids = list_model_ids()
    return templates.TemplateResponse("index.html", {"request": request, "models": model_ids})


@app.post("/chat")
async def chat(model: str = Form(...), prompt: str = Form(...)):
    print(f"接收到聊天请求: model={model}, prompt={prompt[:50]}...")
    # 使用 StreamingResponse 包装异步生成器
    try:
        generator = stream_chat(model, prompt)
        print("创建了流式生成器")
        return StreamingResponse(
            generator,
            media_type="text/plain; charset=utf-8"
        )
    except Exception as e:
        print(f"创建流式响应时出错: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    print("启动服务：http://localhost:8080")
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
