
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 加载 .env 中的 DATABASE_URL
load_dotenv("services/backend_api/.env")
db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("❌ 未在 .env 中找到 DATABASE_URL")
    exit(1)

# 处理 postgresql 协议头
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)

print(f"🚀 正在连接 Neon 数据库并更新表结构...")

try:
    with engine.connect() as conn:
        # 1. 给 users 表增加 reset_pin 列
        print("--- Updating 'users' table ---")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_pin VARCHAR(20);"))
            print("✅ Added 'reset_pin' column to 'users' table.")
        except Exception as e:
            if "already exists" in str(e):
                print("ℹ️ 'reset_pin' column already exists.")
            else:
                print(f"❌ Error updating users: {e}")

        # 2. 给 user_watchlists 表更新 (如果需要)
        # 这里之前已经改过 TIMESTAMPTZ，Neon 本身支持所以通常没问题
        
        conn.commit()
    print("\n✨ Neon 数据库 Schema 更新完成！现在你可以尝试重新注册或重置密码了。")
except Exception as e:
    print(f"❌ 数据库连接失败: {e}")
