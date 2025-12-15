import os

from cryptography.fernet import Fernet


# 读取密钥
def load_key():
    key = os.getenv("SECRET_KEY")  # 从环境变量'SECRET_KEY'读取密钥
    if not key:
        raise ValueError("未设置环境变量 SECRET_KEY")
    return key.encode()  # Fernet 期待字节类型的密钥

# 加密信息
def encrypt_message(message):
    key = load_key()
    f = Fernet(key)
    encrypted_message = f.encrypt(message.encode())
    return encrypted_message.decode()

# 解密信息
def decrypt_message(encrypted_message):
    key = load_key()
    f = Fernet(key)
    try:
        decrypted_message = f.decrypt(encrypted_message.encode())
        return decrypted_message.decode()
    except Exception as e:
        return f"解密失败: {e}"


if __name__ == "__main__":
    # SECRET_KEY 已设置在环境变量中
    plaintext = "sk-GFP62OhkTplx4DhkMNjwBhYAogftxZM6znbz2l8PDwc5CfBE"

    # 加密
    encrypted = encrypt_message(plaintext)
    print("加密后的信息:", encrypted)

    # 解密
    decrypted = decrypt_message(
        "gAAAAABow8ZswUlACpA9hOmG1AxERQC4EoFyPFDqlPZbAUC0g5K_cZ2jsA9j3tCg4nWy5oAgwDO2V25wciqij-qwaLQW-vLzI9joGVLNIhVBV98R902Kh0oAU_N0w3TXEmB9Klng87EIiSUO4FFYu0GSNN1vD56HXw==")
    print("解密后的信息:", decrypted)

    # 验证
    assert decrypted == plaintext, "解密结果不匹配！"
    print("加密解密验证通过")