# utils/app.py
import logging
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config.models import list_model_ids
from utils.stream_chat import execute_model
from prompt.get_system_prompt import get_system_prompt
from utils.persona_loader import list_personas, get_default_personas
from utils.stream_chat import chat_history

# -----------------------------
# 日志配置
# -----------------------------
logger = logging.getLogger("chat_app")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(handler)

# -----------------------------
# FastAPI app 初始化
# -----------------------------
app = FastAPI(title="Stream Chat API")

# 静态文件 & 模板目录
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -----------------------------
# 全局变量：当前出场人物
# -----------------------------
current_personas = get_default_personas()  # 默认玩家主角 + 刘焕琴

# -----------------------------
# 首页路由
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    首页：返回模型列表，并渲染模板
    """
    model_ids = list_model_ids()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "models": model_ids}
    )

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
    聊天接口：流式返回模型生成内容
    - model: 模型 ID
    - prompt: 用户输入
    - system_rule: 系统规则
    """
    if model not in list_model_ids():
        raise HTTPException(status_code=400, detail=f"模型 '{model}' 不存在")

    try:
        system_prompt = get_system_prompt(system_rule)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"system_rule '{system_rule}' 不存在")

    try:
        return StreamingResponse(
            execute_model(
                model_name=model,
                user_input=prompt,
                system_instructions=system_prompt,
                personas = current_personas
            ),
            media_type="text/plain; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"[chat] 流式响应出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器处理请求时出错")

# -----------------------------
# 获取人物列表
# -----------------------------
@app.get("/personas")
async def get_persona_list():
    """
    返回可选出场人物列表，并标记当前出场人物
    - selected: True 表示已被选中
    """
    all_personas = list_personas()
    result = [{"name": name, "selected": name in current_personas} for name in all_personas]
    return {"personas": result}

# -----------------------------
# 更新当前出场人物
# -----------------------------
@app.post("/personas")
async def update_personas(selected: str = Form(...)):
    """
    更新当前出场人物
    - selected: 逗号分隔的出场人物名称
    """
    global current_personas
    names = [name.strip() for name in selected.split(",") if name.strip()]
    available = set(list_personas())
    current_personas = [name for name in names if name in available]
    logger.info(f"[人物更新] 当前出场人物: {current_personas}")
    return {"status": "ok", "current_personas": current_personas}

# -----------------------------
# 清除历史事件
# -----------------------------
@app.post("/clear_history")
async def clear_history():
    chat_history.clear_history()
    logger.info("[操作] 历史记录已清空 (来自 Web)")
    return {"status": "ok"}

# -----------------------------
# 启动服务
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
