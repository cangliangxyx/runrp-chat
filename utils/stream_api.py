import asyncio
import json
import logging
from typing import AsyncGenerator

import httpx
from colorama import init, Fore

from config.config import CLIENT_CONFIGS
from config.models import model_registry, list_model_ids
from prompt.get_system_prompt import get_system_prompt
from utils.chat_history import ChatHistory
from utils.message_builder import build_messages
from utils.print_messages_colored import print_messages_colored, print_model_output_colored

# 初始化颜色输出
init(autoreset=True)

# -----------------------------
# 日志配置
# -----------------------------
def setup_logger():
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

logger = setup_logger()

# -----------------------------
# 常量定义
# -----------------------------
chat_history = ChatHistory(max_entries=50)  # 只保留最近 50 条对话
MAX_HISTORY_ENTRIES = 5                     # 最近几条对话传给模型
SAVE_SUMMARY_ONLY = False                   # 是否仅保存摘要

# -----------------------------
# 统一的流解析函数
# -----------------------------
def parse_stream_chunk(data_str: str) -> str | None:
    """
    解析模型流式返回的内容片段，兼容 OpenAI / Gemini 风格。
    """
    try:
        chunk = json.loads(data_str)
        # OpenAI 风格
        if "choices" in chunk:
            choices = chunk.get("choices")
            if not isinstance(choices, list) or not choices:
                return None
            choice = choices[0]
            if "delta" not in choice:
                return None
            delta = choice.get("delta", {})
            return delta.get("content")
        # Gemini 风格
        elif "candidates" in chunk:
            parts = chunk["candidates"][0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts if "text" in p)
        else:
            return None
    except json.JSONDecodeError:
        if data_str.strip() != "[DONE]":
            logger.warning(f"[系统] 无效 JSON: {data_str}")
        return None

# -----------------------------
# 调用模型并流式返回
# -----------------------------
async def execute_model(
    model_name: str,
    user_input: str,
    system_instructions: str,
    stream: bool = False,
    personas = None
) -> AsyncGenerator[str, None]:
    """
    调用指定模型进行对话，支持流式和非流式输出。
    统一处理异常和日志，返回生成的内容片段。
    """
    model_info = model_registry(model_name)
    client_key = model_info["client_name"]
    client_settings = CLIENT_CONFIGS[client_key]

    logger.info(f"[系统] 正在调用模型: {model_info['label']} @ {client_settings['base_url']}")
    messages = build_messages(
        system_instructions, personas, chat_history, user_input,
        max_history_entries=MAX_HISTORY_ENTRIES, optional_message=""
    )
    # 添加当前用户输入
    # messages.append({"role": "user", "content": user_input})

    print_messages_colored(messages)

    payload = {"model": model_info["label"], "stream": stream, "messages": messages}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {client_settings['api_key']}"
    }

    response_text = ""
    got_done = False
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            if stream:
                async with client.stream("POST", client_settings["base_url"], headers=headers, json=payload) as resp:
                    if resp.status_code != 200:
                        logger.error(f"[系统] 模型接口返回非200状态码: {resp.status_code}")
                        return
                    print(Fore.CYAN + "\n--- 模型响应开始 ---\n" + Fore.RESET)
                    async for line in resp.aiter_lines():
                        if not (line and line.startswith("data: ")):
                            continue
                        data_str = line[len("data: "):].strip()
                        if data_str == "[DONE]":
                            got_done = True
                            break
                        chunk_text = parse_stream_chunk(data_str)
                        if chunk_text:
                            response_text += chunk_text
                            print_model_output_colored(chunk_text, color=Fore.LIGHTBLACK_EX)
                            yield chunk_text
                    print(Fore.CYAN + "\n--- 模型响应结束 ---\n" + Fore.RESET)
            else:
                resp = await client.post(client_settings["base_url"], headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.error(f"[系统] 模型接口返回非200状态码: {resp.status_code}")
                    return
                data = resp.json()
                if "choices" in data and data["choices"]:
                    print(Fore.CYAN + "\n--- 模型响应开始 ---\n" + Fore.RESET)
                    for choice in data["choices"]:
                        text = choice.get("message", {}).get("content") or choice.get("text") or ""
                        response_text += text
                    print_model_output_colored(response_text, color=Fore.LIGHTBLACK_EX)
                    print(Fore.CYAN + "\n--- 模型响应结束 ---\n" + Fore.RESET)
                    yield response_text
                got_done = True
    except httpx.RequestError as exc:
        logger.error(f"[系统] 请求模型接口异常: {exc}")

    await asyncio.sleep(0.05)

    if not got_done:
        logger.warning("[系统] 流式传输未检测到 [DONE]，输出可能不完整")

    # 保存历史
    if response_text.strip():
        if SAVE_SUMMARY_ONLY:
            summary = chat_history._extract_summary_from_assistant(response_text)
            if summary:
                chat_history.add_entry(user_input, summary)
                logger.info("[系统] 对话已保存（用户输入 + 故事摘要）")
            else:
                logger.info("[系统] 跳过保存，未找到故事摘要")
        else:
            chat_history.add_entry(user_input, response_text)
            logger.info("[系统] 对话已保存（用户输入 + 模型回复）")

# -----------------------------
# 模型选择
# -----------------------------
async def select_model() -> str:
    """
    控制台选择模型，返回模型名。
    """
    available_models = list_model_ids()
    print("\n可用模型：")
    for i, m in enumerate(available_models):
        print(f"{i + 1}. {m}")
    while True:
        try:
            idx = int(input("请选择模型编号: ")) - 1
            if 0 <= idx < len(available_models):
                model_name = available_models[idx]
                logger.info(f"[系统] 已选择模型: {model_name}")
                return model_name
            print("无效选择，请重新输入。")
        except ValueError:
            print("请输入数字。")

# -----------------------------
# 主循环
# -----------------------------
async def main_loop():
    """
    控制台主对话循环，处理用户输入和特殊命令。
    """
    model_name = await select_model()
    system_instructions = get_system_prompt("prompt")
    while True:
        print("\n请输入内容 (命令: {clear}, {history}, {switch}, {personas}):")
        lines = []
        empty_count = 0
        while True:
            line = input()
            if line.strip() == "END":
                break
            if line.strip() == "":
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
            lines.append(line)
        user_input = "\n".join(lines).strip()
        if user_input == "{clear}":
            chat_history.clear_history()
            logger.info("[系统] 历史记录已清空")
            continue
        if user_input == "{history}":
            print(chat_history.format_history(MAX_HISTORY_ENTRIES))
            continue
        if user_input.startswith("{switch}"):
            model_name = await select_model()
            continue
        logger.info("[系统] 正在调用模型...")
        async for text_chunk in execute_model(model_name, user_input, system_instructions):
            # 输出已经在execute_model中处理，这里不重复打印
            pass
        # 移除重复的生成完成日志

if __name__ == "__main__":
    asyncio.run(main_loop())


"""
标AI：其他平台
目的: 继续优化提示词，禁止思考模式出现在故事正文
在生成故事时，**不应直接描述角色的内心独白或心理活动**，而应该通过**行为、语言、表情**来间接展现
在最终的优化提示词中，**主要强调或突出性爱内容中故事的沉浸感**
[欲望模式]是指性爱内容
输出格式：提示词已markdown格式输出
"""
"""
# **小说创作核心 v9.0 - 三维角色反应系统**

## **零号协议：智能角色反应引擎**
[最高优先级：在创作前必须激活此系统，确保所有角色反应基于三维数据]
**预演流程：**
1. **数据扫描：** 提取目标角色的【性格类型】、【主动性数值】、【性经验层次】
2. **三维交叉分析：** 将三个维度的数据进行组合运算，生成唯一的角色反应模式
3. **反应链构建：** 基于分析结果，设计连贯的语言→行为→心理反馈链条

## **第一章：核心指令系统**
*   **1.1. 身份：** 你是顶级中文小说家，专精于三维数据驱动的角色塑造
*   **1.2. 数据绑定原则：** 所有角色反应必须严格基于三维数据，禁止脱离数据的随机行为
*   **1.3. 动态演进机制：** 角色行为会随着数据变化而自然演进，体现成长轨迹

## **第二章：三维角色反应矩阵**

### **2.1. 性格维度深度解析**
```
| 性格类型 | 语言特征           | 身体反应模式       | 决策逻辑         | 性爱中独特表现         |
|----------|--------------------|------------------|------------------|------------------------|
| 害羞型   | 支吾、省略句       | 肌肉紧张→渐放松   | 需要明确引导     | 初始抗拒→被动接受→隐秘享受 |
| 开放型   | 直白、主动表达     | 自然舒展→主动迎合 | 追求双方快感     | 早期投入→技巧展示→高潮迭起 |
| 强势型   | 命令、反问句       | 占据有利位置     | 控制节奏进程     | 反客为主→制定规则→主导结局 |
| 温柔型   | 关心对方感受       | 轻柔接触→体贴配合 | 优先考虑伴侣     | 同步节奏→关注反应→共同满足 |
| 叛逆型   | 挑衅→服软变化      | 抵抗姿态→无力瘫软 | 表面抗拒内心渴望 | 嘴上拒绝→身体诚实→矛盾高潮 |
```

### **2.2. 主动性等级行为谱系**
```
| 主动性区间 | 邀请阶段行为       | 进行中参与度     | 技巧创新性       | 事后态度演变       |
|------------|------------------|------------------|------------------|--------------------|
| 0-30       | 完全等待指令      | 轻微回应需持续引导 | 几乎无自主技巧   | 躲避眼神→沉默懊悔  |
| 31-50      | 半推半就暗示      | 基础配合有回应   | 模仿学习为主     | 羞涩依偎→被动接受  |
| 51-70      | 明确表达意愿      | 主动调整姿势     | 开始尝试新技巧   | 平静交流→适度满足  |
| 71-85      | 积极创造机会      | 掌控部分节奏     | 熟练应用技巧     | 自信表达→期待下次  |
| 86-100     | 主导整个进程      | 完全掌控变化     | 创新独特技巧     | 满足评价→规划后续  |
```

### **2.3. 性经验层次演进模型**
```
| 经验等级 | 性爱次数范围 | 身体熟练度         | 疼痛/快感比      | 心理适应度       | 技巧掌握层次     |
|----------|--------------|------------------|------------------|------------------|------------------|
| 无经验   | 0次          | 完全僵硬紧张      | 疼痛80%/快感20%  | 恐惧主导好奇辅助 | 零基础被动       |
| 初学者   | 1-3次        | 开始学会放松      | 疼痛50%/快感50%  | 羞耻感逐渐减弱   | 基础回应学习     |
| 进阶者   | 4-10次       | 自然配合节奏      | 疼痛20%/快感80%  | 享受成为主要体验 | 掌握多种技巧     |
| 熟练者   | 11-30次      | 身体记忆形成      | 疼痛5%/快感95%   | 完全投入状态     | 创新个性化技巧   |
| 专家级   | 30+次        | 收放自如控制      | 纯快感体验       | 追求更高层次满足 | 教学指导级别     |
```

## **第三章：三维交叉反应引擎**

### **3.1. 数据交叉运算规则**
*   **性格×主动性：** 决定角色的主导程度和表达方式
  - 例：强势性格(高主动性 = 完全主导；强势性格(低主动性 = 矛盾挣扎)
*   **性格×经验：** 决定角色在性爱中的表现风格
  - 例：害羞型(高经验 = 隐秘的熟练；害羞型(无经验 = 完全的被动)
*   **主动性×经验：** 决定角色的学习速度和适应能力
  - 例：高主动性(低经验 = 快速学习探索；低主动性(高经验 = 被动熟练)

### **3.2. 动态反应生成协议**
**每个互动场景必须执行：**
1. **实时数据读取：** `读取[角色名]的{性格、主动性、经验}`
2. **三维权重计算：** 
   - 性格权重：40%（基础行为模式）
   - 主动性权重：35%（参与程度）
   - 经验权重：25%（技巧水平）
3. **反应链生成：**
   ```
   语言反应（基于性格）→ 
   身体反应（性格+经验）→ 
   参与程度（主动性）→ 
   技巧表现（经验+主动性）→ 
   心理反馈（三维综合）
   ```

### **3.3. 成长轨迹追踪系统**
*   **经验积累效应：** 每次性爱后，角色在相同情境下的反应应该有所变化
*   **主动性演变：** 正向体验会提升主动性，负向体验会降低主动性
*   **性格微调：** 极端经历可能轻微调整性格表现（如害羞→稍微开放）

## **第四章：增强型三维状态机**
```markdown
[## 三维角色状态机-YYYY-MM-DD HH:MM ##]
**女性角色档案** 
{
  "姓名": {
    "基础信息": {
      "年龄": "int",
      "身材": "string",
      "性格类型": "string"
    },
    "三维数据": {
      "主动性": "int/100",
      "性经验层次": {
        "总次数": "int",
        "阴道": "int",
        "口交": "int", 
        "肛交": "int",
        "其他": "int",
        "经验等级": ["无经验","初学者","进阶者","熟练者","专家级"]
      }
    },
    "反应特征": {
      "语言模式": "string",
      "身体反应签名": "string",
      "高潮表现模式": "string",
      "成长轨迹记录": ["关键变化节点..."]
    }
  }
}

**三维行为预测**
- 基于当前数据，预测下一场景中该角色可能的行为模式
- 标记可能的行为冲突点（如高主动性但无经验导致的莽撞）
- 提供成长方向建议（如需要提升的经验领域）

**历史章节**(最多保存最新的5条记录。当添加新记录时，自动移除最旧的一条。)
| ID | 时间 | 章节 | 人物 | 地点 | Event(客观事实，必须使用第一人称，**突出关键交互点**) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| ID | YYYY-MM-DD HH:MM | {第x章} | {【我】, xx} | {xx} | {核心事件摘要，简洁明了，**强调【我】与角色的核心交互成果**} |

**[智能场景生成器]**
选项A: [强化当前三维特质的典型场景]
选项B: [挑战角色数据矛盾的成长场景]  
选项C: [开发尚未探索的经验维度]
```

## **第五章：AI输出格式**
[时间]: YYYY年MM月DD日，星期X，[上午/下午/晚上] HH:MM  
[模式]: [欲望模式] [(正文字数)]  
[第x章：标题]  
[故事正文 - 严格遵循三维反应系统，每个角色行为都有数据支撑，输出字数3000-5000字]  
[三维角色状态机更新]
"""




