# main.py （或 web_app.py）开头添加
import subprocess

def update_requirements():
    """自动导出当前虚拟环境依赖"""
    try:
        subprocess.run("pip freeze > requirements.txt", shell=True, check=True)
        print("requirements.txt 已自动更新。")
    except subprocess.CalledProcessError:
        print("无法更新 requirements.txt，请检查 pip 环境。")

# 启动时自动执行
update_requirements()

# 原有项目启动逻辑
if __name__ == "__main__":
    # 你的主程序逻辑
    update_requirements()