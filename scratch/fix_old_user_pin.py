
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv("services/backend_api/.env")
db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("❌ 未找到 DATABASE_URL")
    exit(1)

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
email = "carson_tu@hotmail.com"
default_pin = "123456" # 给你设置一个初始 PIN

try:
    with engine.connect() as conn:
        print(f"🛠 正在为 {email} 补全 PIN 码...")
        query = text("UPDATE users SET reset_pin = :pin WHERE email = :email")
        result = conn.execute(query, {"pin": default_pin, "email": email})
        conn.commit()
        if result.rowcount > 0:
            print(f"✅ 成功！账号 {email} 的重置码现在是: {default_pin}")
        else:
            print(f"⚠️ 未找到账号 {email}，请确认邮箱是否正确。")
except Exception as e:
    print(f"❌ 错误: {e}")
