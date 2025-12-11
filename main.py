# main.py
import json
import logging
import os
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from config.models import list_model_ids
from prompt.get_system_prompt import PROMPT_FILES, get_system_prompt
from utils.persona_loader import list_personas, get_default_personas
from utils.stream_chat_app import execute_model_for_app, chat_history

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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
ASSETS_DIR = os.path.join(FRONTEND_DIST, "assets")

app = FastAPI(title="Nebula Chat API")

# 托管 Vite 构建后的静态资源
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
else:
    logger.warning("⚠️ 未检测到 frontend/dist/assets，请先执行：npm run build")

# 托管你原有的 static 目录（如果还需要）
if os.path.exists(os.path.join(BASE_DIR, "static")):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------------
# 全局变量
# -----------------------------
current_personas = get_default_personas()

# -----------------------------
# 前端入口（替代 Flask + templates）
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    index_file = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.exists(index_file):
        return HTMLResponse(
            content="前端尚未构建，请先在 frontend 目录执行：npm run build",
            status_code=500
        )
    return FileResponse(index_file)

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
    logger.info(f"[chat] 接收到表单参数: model={model}, system_rule={system_rule}, stream={stream}, nsfw={nsfw}")
    if model not in list_model_ids():
        raise HTTPException(status_code=400, detail=f"模型 '{model}' 不存在")
    try:
        system_prompt = get_system_prompt(system_rule)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"system_rule '{system_rule}' 不存在")

    nsfw_enabled = nsfw.lower() == "true"
    stream_enabled = stream.lower() == "true"
    print("stream_enabled =", stream_enabled)
    try:
        if stream_enabled:
            async def event_stream():
                async for chunk in execute_model_for_app(
                    model_name=model,
                    user_input=prompt,
                    system_instructions=system_prompt,
                    personas=current_personas,
                    web_input=web_input,
                    nsfw=nsfw_enabled,
                    stream=True
                ):
                    yield json.dumps(chunk, ensure_ascii=False) + "\n"
            return StreamingResponse(event_stream(), media_type="application/json")
        else:
            # 非流式：一次性获取完整结果
            result_chunks = []
            async for chunk in execute_model_for_app(
                model_name=model,
                user_input=prompt,
                system_instructions=system_prompt,
                personas=current_personas,
                web_input=web_input,
                nsfw=nsfw_enabled,
                stream=False
            ):
                logger.info(f"[非流模式] 收到 chunk: {chunk}")  # 打印每个 chunk
                result_chunks.append(chunk)
            # 根据 execute_model_for_app 的返回结构调整
            logger.info(f"[非流模式] 总共 {len(result_chunks)} 个 chunk")
            full_result = {"results": result_chunks}
            logger.info(f"[非流模式] full_result={full_result}")  # 打印最终返回数据
            return JSONResponse(full_result)
    except Exception as e:
        logger.error(f"[chat] 响应出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器处理请求时出错")
    
# -----------------------------
# 获取人物列表
# -----------------------------
@app.get("/personas")
async def get_persona_list():
    all_personas = list_personas()
    return JSONResponse({
        "personas": [{"name": name, "selected": name in current_personas} for name in all_personas]
    })

# -----------------------------
# 更新人物列表
# -----------------------------
@app.post("/personas")
async def update_personas(selected: str = Form(...)):
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
    try:
        chat_history.reload()
        logger.info("[操作] 历史记录已从文件重新加载")
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"[reload_history] 失败: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# -----------------------------
# 清空聊天历史
# -----------------------------
@app.post("/clear_history")
async def clear_history():
    chat_history.clear_history()
    logger.info("[操作] 历史记录已清空")
    return JSONResponse({"status": "ok"})

# -----------------------------
# 获取 system_rules
# -----------------------------
@app.get("/system_rules")
async def get_system_rules():
    return JSONResponse({"rules": list(PROMPT_FILES.keys())})

# -----------------------------
# 获取模型列表
# -----------------------------
@app.get("/system_model")
async def get_system_models():
    return JSONResponse({"rules": list(list_model_ids())})

# -----------------------------
# 删除最后一条聊天记录
# -----------------------------
@app.post("/remove_last_entry")
async def remove_last_entry():
    try:
        if chat_history.is_empty():
            return JSONResponse({"status": "empty", "message": "没有可删除的记录"}, status_code=400)

        chat_history.remove_last_entry()
        logger.info("[操作] 已删除最后一条聊天记录")
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"[remove_last_entry] 失败: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# SPA 前端兜底路由（必须放在所有 API 之后）
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str):
    # 排除后端 API 与静态资源路径
    if full_path.startswith("chat") \
        or full_path.startswith("personas") \
        or full_path.startswith("system_rules") \
        or full_path.startswith("system_model") \
        or full_path.startswith("reload_history") \
        or full_path.startswith("clear_history") \
        or full_path.startswith("remove_last_entry") \
        or full_path.startswith("assets") \
        or full_path.startswith("static"):
        return JSONResponse({"error": "Not Found"}, status_code=404)

    index_file = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)

    return HTMLResponse("Frontend not built", status_code=404)

# -----------------------------
# 启动服务（生产安全版）
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    logger.info("启动服务：http://localhost:8080")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
