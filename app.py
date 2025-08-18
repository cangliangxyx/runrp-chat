# app_bak.py
import logging, json, uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config.models import list_model_ids
from utils.test import test

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
async def chat(model: str = Form(...), prompt: str = Form(...)):
    try:
        return StreamingResponse(
            test(model=model, prompt=prompt),  # 传入异步生成器
            media_type="text/plain; charset=utf-8"
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"[route] 创建流式响应时出错: {e}")
        raise


if __name__ == "__main__":
    # 通过 uvicorn.run 指定 log_level，确保子进程也是 INFO
    print("启动服务：http://localhost:8080")
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True, log_level="info")