import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
import sys
import os

# 直接使用你提供的 Neon 连接字符串进行测试
NEON_CONN_STR = "postgresql://neondb_owner:npg_Qc0yJfgdbxO5@ep-proud-snow-aj4t7adu-pooler.c-3.us-east-2.aws.neon.tech/neondb?sslmode=require"

def test_neon_upload():
    print("🚀 开始测试 Neon DB 写入...")
    
    try:
        # 1. 创建引擎
        engine = create_engine(NEON_CONN_STR)
        print("🔗 数据库引擎创建成功。")
        
        # 2. 获取一点测试数据 (AAPL)
        symbol = "AAPL"
        print(f"📡 正在获取 {symbol} 的测试数据...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1d", interval="1h")
        
        if df.empty:
            print("❌ 未能获取到股票数据，请检查网络。")
            return

        # 格式化数据
        df.index.name = 'timestamp'
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_convert('UTC').tz_localize(None)
            
        table_name = "test_connection_aapl"
        
        # 3. 写入数据库
        print(f"💾 正在写入表 {table_name} 到 Neon DB...")
        df.to_sql(table_name, engine, if_exists='replace', index=True)
        print(f"✅ 写入成功！表名: {table_name}, 行数: {len(df)}")
        
        # 4. 验证读取
        print("🔍 正在从数据库读取刚才写入的数据进行验证...")
        df_read = pd.read_sql(f'SELECT * FROM "{table_name}" LIMIT 5', engine)
        print("📈 读取到的前几行数据:")
        print(df_read)
        
        print("\n✨ 测试完全通过！Neon DB 连接和写入功能正常。")
        
    except Exception as e:
        print(f"\n❌ 测试失败！错误信息:\n{e}")

if __name__ == "__main__":
    # 确保安装了必要库
    try:
        import sqlalchemy
        import psycopg2
    except ImportError:
        print("❌ 缺少必要库，请先运行: pip install sqlalchemy psycopg2-binary yfinance pandas")
        sys.exit(1)
        
    test_neon_upload()
