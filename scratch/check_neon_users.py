
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

try:
    with engine.connect() as conn:
        print("🔍 正在扫描 Neon 数据库中的用户...")
        query = text("SELECT email, full_name, reset_pin FROM users")
        rows = conn.execute(query).fetchall()
        
        if not rows:
            print("📭 数据库中没有任何用户。")
        else:
            print(f"✅ 找到 {len(rows)} 个用户:")
            for row in rows:
                pin_status = "✅ 已设置" if row[2] else "❌ 未设置 (NULL)"
                print(f" - Email: [{row[0]}], Name: {row[1]}, PIN: {pin_status}")
except Exception as e:
    print(f"❌ 错误: {e}")
