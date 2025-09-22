from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True)

colors = [
    # 普通颜色
    (Fore.BLACK,   "BLACK 黑色"),
    (Fore.RED,     "RED 红色"),
    (Fore.GREEN,   "GREEN 绿色"),
    (Fore.YELLOW,  "YELLOW 黄色"),
    (Fore.BLUE,    "BLUE 蓝色"),
    (Fore.MAGENTA, "MAGENTA 洋红/紫色"),
    (Fore.CYAN,    "CYAN 青色"),
    (Fore.WHITE,   "WHITE 白色"),

    # 亮色系列
    (Fore.LIGHTBLACK_EX,   "LIGHTBLACK_EX 灰色/亮黑色"),
    (Fore.LIGHTRED_EX,     "LIGHTRED_EX 亮红色"),
    (Fore.LIGHTGREEN_EX,   "LIGHTGREEN_EX 亮绿色"),
    (Fore.LIGHTYELLOW_EX,  "LIGHTYELLOW_EX 亮黄色"),
    (Fore.LIGHTBLUE_EX,    "LIGHTBLUE_EX 亮蓝色"),
    (Fore.LIGHTMAGENTA_EX, "LIGHTMAGENTA_EX 亮紫色"),
    (Fore.LIGHTCYAN_EX,    "LIGHTCYAN_EX 亮青色"),
    (Fore.LIGHTWHITE_EX,   "LIGHTWHITE_EX 亮白色"),
]

for color, name in colors:
    print(color + name)

print(Fore.RESET + Style.RESET_ALL + "恢复默认颜色")
