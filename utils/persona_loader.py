# utils/persona_loader.py

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

# 日志配置
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 人物配置文件路径
PERSONA_FILE = Path(__file__).parent.parent / "config" / "persona.json"

# 主角名字
DEFAULT_USER_NAME = "常亮"
# 默认出场 NPC（除玩家）
DEFAULT_NPC_NAMES = []


def load_personas() -> Dict[str, Dict[str, Any]]:
    """
    从 persona.json 读取所有人物设定
    """
    if not PERSONA_FILE.exists():
        raise FileNotFoundError(f"未找到人物配置文件: {PERSONA_FILE}")

    with open(PERSONA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_persona(name: str) -> Dict[str, Any]:
    """根据名字加载单个人物设定（包括默认玩家主角）"""
    personas = load_personas()
    if name not in personas:
        raise KeyError(f"未找到 persona: {name}, 可选值: {list(personas.keys())}")
    return personas[name]


def list_personas() -> List[str]:
    """列出所有人物名称（不含默认玩家主角）"""
    return list(load_personas().keys())


def get_default_personas() -> List[str]:
    """
    获取默认出场人物列表
    默认包含玩家主角 {user} 和指定 NPC
    """
    available = list_personas()
    # print("available = ", available)
    personas = []
    if DEFAULT_USER_NAME in available:
        # print("DEFAULT_USER_NAME = ", DEFAULT_USER_NAME)
        personas.append(DEFAULT_USER_NAME)
    else:
        logger.warning(f"persona.json 中没有找到 {DEFAULT_USER_NAME}，请补充！")
    for name in DEFAULT_NPC_NAMES:
        if name in available:
            personas.append(name)
    return personas


async def select_personas() -> List[str]:
    """
    让用户选择当前出场人物
    返回选中的人物列表（可为空，仅包含玩家主角 {user}）
    """
    available = list_personas()
    selected_personas: List[str] = []

    if not available:
        print("当前没有可选 NPC，仅包含玩家主角 {user}")
        return [DEFAULT_USER_NAME]

    print("\n可用人物：")
    for i, name in enumerate(available):
        print(f"{i+1}. {name}")

    selected = input("请输入出场人物编号（逗号分隔，可多个，留空仅使用玩家主角 {user}）: ").strip()
    if not selected:
        print(f"已选择：仅包含玩家主角 {DEFAULT_USER_NAME}")
        logger.info("[操作] 出场人物为空，仅玩家主角 {user}")
        return [DEFAULT_USER_NAME]

    try:
        indices = [int(x)-1 for x in selected.split(",")]
        selected_personas = [DEFAULT_USER_NAME]  # 玩家主角始终在列表中
        selected_personas += [available[i] for i in indices if 0 <= i < len(available)]
        print(f"已选择出场人物: {selected_personas}")
        logger.info(f"[操作] 选择出场人物: {selected_personas}")
    except Exception:
        print("选择有误，请重新选择")
        return await select_personas()

    return selected_personas


if __name__ == "__main__":
    # 调试输出
    personas = load_personas()
    print("全部人物:")
    for name, info in personas.items():
        print(f"{name}: {info}")

    print("\n单独取一个:")
    print(load_persona("张静"))

    print("\n get_default_personas 默认出场人物:")
    print(get_default_personas())
