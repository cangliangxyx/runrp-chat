import logging
import uvicorn
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config.models import list_model_ids
from utils.stream_chat import run_model
from prompt.get_system_prompt import get_system_prompt

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 模块级日志器
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页：展示模型列表"""
    model_ids = list_model_ids()
    return templates.TemplateResponse("index.html", {"request": request, "models": model_ids})


@app.post("/chat")
async def chat(
    model: str = Form(...),
    prompt: str = Form(...),
    system_rule: str = Form("default"),
):
    """聊天接口：调用模型并流式返回响应"""
    try:
        system_prompt = get_system_prompt(system_rule)
        return StreamingResponse(
            run_model(model=model, user_prompt=prompt, system_prompt=system_prompt),
            media_type="text/plain; charset=utf-8",
        )
    except Exception as e:
        logger.error(f"[route] 创建流式响应时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器处理请求时出错")


if __name__ == "__main__":
    print("启动服务：http://localhost:8080")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )
