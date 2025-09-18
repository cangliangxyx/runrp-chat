# utils/stream_chat.py
import json
import asyncio
import httpx
import logging
from typing import AsyncGenerator
from colorama import init, Fore
from config.config import CLIENT_CONFIGS
from config.models import model_registry, list_model_ids
from utils.chat_history import ChatHistory
from prompt.get_system_prompt import get_system_prompt
from utils.persona_loader import select_personas, get_default_personas
from utils.message_builder import build_messages
from utils.print_messages_colored import print_messages_colored, print_model_output_colored


# 初始化颜色输出
init(autoreset=True)

# -----------------------------
# 日志配置
# -----------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -----------------------------
# 全局变量
# -----------------------------
chat_history = ChatHistory(max_entries=50)  # 只保留最近 50 条对话
MAX_HISTORY_ENTRIES = 1                     # 最近 10 条对话传给模型
SAVE_STORY_SUMMARY_ONLY = True              # 只保存摘要，避免文件太大

# -----------------------------
# 调用模型并流式返回
# -----------------------------
async def execute_model(
    model_name: str,
    user_input: str,
    system_instructions: str,
    personas: list[str],
) -> AsyncGenerator[str, None]:
    model_details = model_registry(model_name)
    client_key = model_details["client_name"]
    client_settings = CLIENT_CONFIGS[client_key]

    logger.info(f"[调用模型] {model_details['label']} @ {client_settings['base_url']}")
    messages = build_messages(system_instructions, personas, chat_history, user_input, max_history_entries=MAX_HISTORY_ENTRIES, optional_message="")
    print_messages_colored(messages)

    payload = {"model": model_details["label"], "stream": True, "messages": messages}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {client_settings['api_key']}"}

    full_response_text = ""
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", client_settings["base_url"], headers=headers, json=payload) as response:
                if response.status_code != 200:
                    logger.error(f"模型接口返回非200状态码: {response.status_code}")
                    return
                async for line in response.aiter_lines():
                    if not (line and line.startswith("data: ")):
                        continue
                    data_str = line[len("data: "):].strip()
                    if data_str in ("[DONE]", ""):
                        continue
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices")
                        if not choices or len(choices) == 0:  # 避免 IndexError
                            continue
                        delta = choices[0].get("delta", {})
                        delta_content = delta.get("content")
                        if delta_content:
                            full_response_text += delta_content
                            yield delta_content
                    except json.JSONDecodeError:
                        logger.warning(f"无效 JSON: {data_str}")
                        continue
    except httpx.RequestError as e:
        logger.error(f"请求模型接口异常: {e}")

    # 保存历史
    if full_response_text.strip():
        if SAVE_STORY_SUMMARY_ONLY:
            summary = chat_history._extract_summary_from_assistant(full_response_text)
            if summary:
                chat_history.add_entry(user_input, summary)
                logger.info("[对话已保存] 用户输入 + 故事摘要")
            else:
                logger.info("[跳过保存] 未找到故事摘要")
        else:
            chat_history.add_entry(user_input, full_response_text)
            logger.info("[对话已保存] 用户输入 + 模型回复")


# -----------------------------
# 模型选择
# -----------------------------
async def select_model() -> str:
    available_models = list_model_ids()
    print("\n可用模型：")
    for i, m in enumerate(available_models):
        print(f"{i + 1}. {m}")

    while True:
        try:
            idx = int(input("请选择模型编号: ")) - 1
            if 0 <= idx < len(available_models):
                model_name = available_models[idx]
                logger.info(f"[已选择模型] {model_name}")
                return model_name
            print("无效选择，请重新输入。")
        except ValueError:
            print("请输入数字。")

# -----------------------------
# 主循环
# -----------------------------
async def main_loop():
    current_personas = get_default_personas()           # 人物加载
    model_name = await select_model()                   # 模型选择
    system_instructions = get_system_prompt("lamnq")     # 获取默认配置文件
    logger.info(f"[默认出场人物] {current_personas}")

    # 初使剧情，自动填充
    # AUTO_START_MESSAGE = "在下班的地铁上碰见了我的小女友苏糯糯，大三美术系的苏糯糯，是个身高150cm的行走“甜心炸弹”。她天生一副纯真萝莉脸，性格甜美害羞。但没人知道，在她宽松的画画服下，是怎样一具颠倒众生的尤物身躯。92G/58/91的夸张三围在她身上显得无比和谐。那对G罩杯的雪白巨乳随着她的步伐微微颤动，纤细的腰肢仿佛一掐就断，而圆润挺翘的臀部则像磁石般吸引着所有目光。她就是天使面孔与魔鬼身材最完美的结合体，糯糯的身体极度敏感轻抚或热吻时都能达到高潮，而她的白虎包子穴的阴唇紧闭能像嘴巴一样将爱液全部锁在阴道里，外部看起来微微湿润，但是将手指插入时会感觉到整个阴道里像温泉一样包裹着时不时还会冒出有一股热流。和糯糯一起到家后，糯糯迫不及待的挂在我身上开始索吻，我在思考要不要今天晚上给她破处，让她真正的成为我的女人"
    # # 自动输入初始剧情
    # logger.info(f"[自动输入] {AUTO_START_MESSAGE}")
    # async for text_chunk in execute_model(model_name, AUTO_START_MESSAGE, system_instructions, current_personas):
    #     # print(text_chunk, end="", flush=True)
    #     print_model_output_colored(text_chunk, color=Fore.YELLOW)
    # logger.info("\n[生成完成] 初始剧情输出完成")

    while True:
        user_input = input("\n请输入内容 (命令: {clear}, {history}, {switch}, {personas}): ").strip()
        if user_input == "{clear}":
            chat_history.clear_history()
            logger.info("[操作] 历史记录已清空")
            continue
        if user_input == "{history}":
            print(chat_history.format_history(MAX_HISTORY_ENTRIES))
            continue
        if user_input.startswith("{switch}"):
            model_name = await select_model()
            continue
        if user_input.startswith("{personas}"):
            current_personas = await select_personas()
            logger.info(f"[人物更新] 当前出场人物: {current_personas}")
            continue

        async for text_chunk in execute_model(model_name, user_input, system_instructions, current_personas):
            # print(text_chunk, end="", flush=True)
            print_model_output_colored(text_chunk, color=Fore.YELLOW)
        logger.info("\n[生成完成] 模型回复已输出完成")
if __name__ == "__main__":
    asyncio.run(main_loop())
"""
##摘要-2024-07-12 21:39##
**长期记忆区 (LTM)**
| No. | Time(时间) | Scene(场景) | Event(客观事实) |
| :--- | :--- | :--- | :--- |
| 1 | 2024-07-03 (第18天) → 2024-07-11 (第26天) | 公寓卧室→公司天台→地铁→酒店→公司杂物间 | 糯糯承认主动换鸡巴位置因『怕它凉了』。我与林晓曦在天台指奸她至高潮并约好周三。下班地铁刺激她后带去酒店，在她崩溃求操后内射。她承诺成为『永远的秘密情人，最听话的小母狗』。次日清晨她主动口交吞精。午休在杂物间，我命令她『自己脱裤子求我』，并首次指奸其后穴，随后内射两次，命令她『夹着精液装高冷』并喝掉温穴水。 |
| 2 | 2024-07-11 (第26天) → 2024-07-12 (第27天) | 公司→公寓 | 我多次羞辱并内射晓曦，命令其『喝掉温穴水』和舔干净。晓曦报备『小穴都肿了要休息两天』。糯糯告知恋情被闺蜜夏晚晴发现，并带她来见我。我命令糯糯『当着她的面，你坐在我腿上』，并当着晚晴的面掀开糯糯衣服露出内衣。晚晴带糯糯离开，我邀请她『随时来玩』。 |

**短期记忆区 (STM)**
| No. | Time(时间) | Scene(场景) | Event(客观事实) |
| :--- | :--- | :--- | :--- |
| 1 | 2024-07-12 21:18 (第27天) | 公寓客厅 | 我抱住糯糯，揉捏其乳房并说『乖老婆这么关心你闺蜜老公吃醋了呢』，糯糯在我怀里撒娇，主动将我的手按向胸部。 |
| 2 | 2024-07-12 21:23 (第27天) | 公寓客厅 | 糯糯在我怀里倾诉思念，我隔着衣服揉捏其乳头并说“是这里吗？”，刺激她直接高潮，随后她主动告白『糯糯随时随地，都在想老公』。 |
| 3 | 2024-07-12 21:39 (第27天) | 公寓客厅→卧室 | 我用手指插入糯糯湿透的小穴，命令她『像小母狗一样，摇着屁股求我操你』。她顺从地哀求后，我将她抱进卧室，她主动脱下裤子等待。 |

**玩家状态面板**
【基础信息】
姓名: 常亮 / 年龄: 23
人物关系：
【苏糯糯/年龄:20/好感度:100/职业:大学美术系学生&校花榜第一/人物关系:女友/性格:甜美害羞，但在爱人面前会展现出顺从和主动的一面，在情欲中逐渐放开/身材:身高:150cm,三围:92G/58/91,发型:黑长直发垂到腰部/特点:白虎馒头穴，身体敏感度高，大阴唇紧致能锁水阴道内的爱液，阴道里有「内阴唇」会不断舔舐龟棱，高潮时子宫口回自动吮吸龟头，穴内水分极多插入感觉像在泡温泉/小穴:经验次数:11[熟练]/菊花:经验次数:4[小有尝试]/口技:12[熟练]】
【林晓曦/年龄:21/好感度:100/职业:软件工程师/人物关系:同事&秘密情人/性格:冰山美人、在常亮会展现出疯狂的一面/身材:身高:150cm,三围:86D/60/88,发型:棕色披肩长发/特点:小穴九曲回廊，阴道内部多弯曲如迷宫/小穴:经验次数:5[生疏]/菊花:经验次数:1[小有尝试]/口技:4[生疏]】
【夏晚晴/年龄:20/好感度:25/职业:大学舞蹈系学生&校花榜第二/人物关系:糯糯的闺蜜/性格:可爱，有警惕心，保护欲强/身材:身高:168cm,三围:84C/59/87,发型:高马尾/特点:未知/小穴:未知/菊花:未知/口技:未知】

**女性角色状态面板**
【基础信息】
姓名: 苏糯糯 / 年龄: 20 / 好感度: 100
职业: D大美术系学生，校花榜第一 / 人物关系：【常亮:男友】，【夏晚晴:最好的闺蜜】
性格: 甜美害羞，但在爱人面前会展现出顺从和主动的一面，在情欲中逐渐放开
身材: 身高:150cm,三围:92G/58/91,发型:黑长直发垂到腰部
特点: 白虎馒头穴，身体敏感度高，大阴唇紧致能锁水阴道内的爱液，阴道里有「内唇」会不断舔舐龟棱，高潮时子宫口会自动吮吸龟头，穴内水分极多插入感觉像在泡温泉
【身体细节】
当前活动: 赤裸下身躺在床上，双腿微张，等待着被插入。
胸部: 饱满的G罩杯被蕾丝文胸束缚着，乳头因持续的情欲刺激而硬挺着，顶起两点小小的凸起。
小穴: 完全暴露，穴口粉嫩湿滑，不断有爱液从紧闭的穴口溢出。因被手指玩弄和强烈的性幻想，内部已然泥泞不堪，正有节奏地收缩，渴望着真正的填满。 | 经验次数: 11次[熟练]
阴蒂: 经过刚才隔着布料的研磨，此刻正完全肿胀充血，颜色变得更深，敏感到极致。
菊花: 在强烈的性欲影响下，随着小穴的收缩而无意识地紧缩着，仍保持着紧闭的状态。 | 经验次数: 4次[小有尝试]
爱抚&口技技巧: 已能熟练地进行深喉口交并吞咽精液。 | 12次[熟练]
"""