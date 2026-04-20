import yfinance as yf
import os
import sys

# 将项目根目录加入 sys.path, 这样可以引用 internal 中的模块
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from internal.db_client.database import StockDB

def fetch_and_update_to_db(symbols):
    """
    抓取股票数据并存入数据库。
    """
    db = StockDB()
    
    for symbol in symbols:
        try:
            print(f"📡 正在从 Yahoo Finance 获取 {symbol} 的 5 分钟数据...")
            
            ticker = yf.Ticker(symbol)
            # 获取最近 7 天的 5m 数据
            new_data = ticker.history(period="7d", interval="5m")
            
            if new_data.empty:
                print(f"⚠️ 警告: 未能获取到 {symbol} 的数据。")
                continue

            # 存入数据库 (表名为 股票代码_5m)
            table_name = f"{symbol}_5m"
            db.save_stock_data(new_data, table_name)
            
            print(f"✅ {symbol} 数据已成功存入数据库表: {table_name}")
                
        except Exception as e:
            print(f"❌ 处理 {symbol} 时出错: {e}")

if __name__ == "__main__":
    TARGETS = ["QQQ", "VOO", "TSLA"]
    print("🚀 开始执行每日数据抓取并存入数据库...")
    fetch_and_update_to_db(TARGETS)
    print("✨ 任务完成。")
