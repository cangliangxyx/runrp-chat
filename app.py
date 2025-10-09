# app.py
import logging, json
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config.models import list_model_ids
from prompt.get_system_prompt import get_system_prompt
from utils.persona_loader import list_personas, get_default_personas
from utils.stream_chat_app import execute_model_for_app, chat_history
from prompt.get_system_prompt import PROMPT_FILES

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
# FastAPI 初始化
# -----------------------------
app = FastAPI(title="Stream Chat API")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -----------------------------
# 全局变量
# -----------------------------
current_personas = get_default_personas()

# -----------------------------
# 首页
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页：渲染模板，返回可选模型列表"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "models": list_model_ids()}
    )

# -----------------------------
# 聊天接口
# -----------------------------
@app.post("/chat")
async def chat(
    model: str = Form(...),
    prompt: str = Form(...),
    system_rule: str = Form("default"),
    web_input: str = Form(""),
    nsfw: str = Form("true"),
    stream: str = Form("true"),
):
    logger.info(f"[chat] 接收到表单参数: model={model}, system_rule={system_rule}, nsfw={nsfw}")

    if model not in list_model_ids():
        raise HTTPException(status_code=400, detail=f"模型 '{model}' 不存在")

    try:
        system_prompt = get_system_prompt(system_rule)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"system_rule '{system_rule}' 不存在")

    nsfw_enabled = nsfw.lower() == "true"
    stream_enabled = stream.lower() == "true"

    try:
        async def event_stream():
            async for chunk in execute_model_for_app(
                model_name=model,
                user_input=prompt,
                system_instructions=system_prompt,
                personas=current_personas,
                web_input=web_input,
                nsfw=nsfw_enabled,
                stream=stream_enabled
            ):
                # 转成 JSON 行（NDJSON）
                yield json.dumps(chunk, ensure_ascii=False) + "\n"

        # 修改 media_type，前端方便解析
        return StreamingResponse(event_stream(), media_type="application/json")

    except Exception as e:
        logger.error(f"[chat] 流式响应出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器处理请求时出错")

# -----------------------------
# 获取人物列表
# -----------------------------
@app.get("/personas")
async def get_persona_list():
    """返回所有可选人物，并标记当前选择状态"""
    all_personas = list_personas()
    return JSONResponse({
        "personas": [{"name": name, "selected": name in current_personas} for name in all_personas]
    })

# -----------------------------
# 更新人物列表
# -----------------------------
@app.post("/personas")
async def update_personas(selected: str = Form(...)):
    """更新当前出场人物"""
    global current_personas
    available = set(list_personas())
    names = [name.strip() for name in selected.split(",") if name.strip()]
    current_personas = [name for name in names if name in available]
    logger.info(f"[人物更新] 当前出场人物: {current_personas}")
    return JSONResponse({"status": "ok", "current_personas": current_personas})



# -----------------------------
# 重新加载聊天历史
# -----------------------------
@app.post("/reload_history")
async def reload_history():
    """重新从文件加载最新的聊天记录"""
    try:
        chat_history.reload()
        logger.info("[操作] 历史记录已从文件重新加载 (来自 Web)")
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"[reload_history] 重新加载失败: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# -----------------------------
# 清空聊天历史
# -----------------------------
@app.post("/clear_history")
async def clear_history():
    """清空聊天历史记录"""
    chat_history.clear_history()
    logger.info("[操作] 历史记录已清空 (来自 Web)")
    return JSONResponse({"status": "ok"})

# -----------------------------
# 获取system prompt
# -----------------------------
@app.get("/system_rules")
async def get_system_rules():
    """返回所有可选的 system_rules"""
    return JSONResponse({"rules": list(PROMPT_FILES.keys())})

# -----------------------------
# 删除最后一条聊天记录
# -----------------------------
@app.post("/remove_last_entry")
async def remove_last_entry():
    """删除最后一条聊天记录"""
    try:
        if chat_history.is_empty():
            return JSONResponse({"status": "empty", "message": "没有可删除的记录"}, status_code=400)

        chat_history.remove_last_entry()
        logger.info("[操作] 已删除最后一条聊天记录 (来自 Web)")
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"[remove_last_entry] 删除最后一条记录失败: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

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
