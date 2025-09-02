import logging
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config.models import list_model_ids
from utils.stream_chat import execute_model
from prompt.get_system_prompt import get_system_prompt

# -----------------------------
# 日志配置
# -----------------------------
logger = logging.getLogger("chat_app")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)

# -----------------------------
# FastAPI app 初始化
# -----------------------------
app = FastAPI(title="Stream Chat API")

# 静态文件 & 模板目录
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# -----------------------------
# 首页路由
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页：展示可用模型列表"""
    model_ids = list_model_ids()
    return templates.TemplateResponse("index.html", {"request": request, "models": model_ids})


# -----------------------------
# 聊天接口
# -----------------------------
@app.post("/chat")
async def chat(
    model: str = Form(...),
    prompt: str = Form(...),
    system_rule: str = Form("default")
):
    """
    聊天接口：流式返回模型输出
    - model: 模型 ID
    - prompt: 用户输入内容
    - system_rule: 系统规则标识
    """
    # 参数校验
    if model not in list_model_ids():
        raise HTTPException(status_code=400, detail=f"模型 '{model}' 不存在")

    try:
        system_prompt = get_system_prompt(system_rule)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"system_rule '{system_rule}' 不存在")

    # 流式返回生成内容
    try:
        return StreamingResponse(
            execute_model(model_name=model, user_input=prompt, system_instructions=system_prompt),
            media_type="text/plain; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"[chat] 流式响应出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器处理请求时出错")


# -----------------------------
# 启动服务（仅在直接运行 app.py 时）
# -----------------------------
if __name__ == "__main__":
    import uvicorn

    logger.info("启动服务：http://localhost:8080")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
