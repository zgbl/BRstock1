import os
import pandas as pd
from sqlalchemy import create_engine, text

class StockDB:
    def __init__(self, db_url=None):
        # 优先使用环境变量 DATABASE_URL
        self.db_url = db_url or os.getenv("DATABASE_URL")
        
        # 如果都没有，回退到本地 SQLite (用于开发)
        if not self.db_url:
            local_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Data/stocks.db"))
            os.makedirs(os.path.dirname(local_db_path), exist_ok=True)
            self.db_url = f"sqlite:///{local_db_path}"
        
        # 处理 Neon/PostgreSQL 的连接字符串（如果以 postgres:// 开头，SQLAlchemy 1.4+ 需要改为 postgresql://）
        if self.db_url.startswith("postgres://"):
            self.db_url = self.db_url.replace("postgres://", "postgresql://", 1)
            
        self.engine = create_engine(self.db_url)

    def save_stock_data(self, df, table_name):
        """
        将 DataFrame 存入数据库。
        采用合并去重策略。
        """
        if df.empty:
            return
        
        # 统一索引名
        df = df.copy()
        df.index.name = 'timestamp'
        
        # 统一表名为小写
        table_name = table_name.lower()
        
        try:
            from sqlalchemy import inspect, text
            # 强制新数据索引为 Datetime 并统一为无时区 (tz-naive)
            df.index = pd.to_datetime(df.index).tz_localize(None)
            
            # 1. 尝试合并数据 (如果表存在)
            inspector = inspect(self.engine)
            if inspector.has_table(table_name):
                try:
                    query = text(f'SELECT * FROM "{table_name}"')
                    existing_df = pd.read_sql(query, self.engine, index_col='timestamp')
                    # 强制旧数据索引为 Datetime 并统一为无时区
                    existing_df.index = pd.to_datetime(existing_df.index).tz_localize(None)
                    
                    combined = pd.concat([existing_df, df])
                    combined = combined[~combined.index.duplicated(keep='last')]
                    combined.sort_index(inplace=True)
                    df = combined # 后续统一写入 df
                except Exception as e:
                    print(f"⚠️ 合并历史数据失败，将执行全量覆盖: {e}")

            # 2. 手动删除旧表并写入新数据 (彻底绕过 if_exists='replace' 的反射 Bug)
            with self.engine.begin() as conn:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
            
            df.to_sql(table_name, self.engine, if_exists='fail', index=True)
            
        except Exception as e:
            print(f"❌ 严重错误: 无法写入表 {table_name}: {e}")

    def get_stock_data(self, table_name, limit=1000):
        """
        从数据库读取数据。
        """
        try:
            from sqlalchemy import text
            table_name = table_name.lower()
            # 使用 text() 包装，并在 query 中保留双引号处理表名
            query = text(f'SELECT * FROM "{table_name}" ORDER BY timestamp DESC LIMIT {limit}')

            df = pd.read_sql(query, self.engine, index_col='timestamp')
            # 确保索引是 Datetime 类型
            df.index = pd.to_datetime(df.index)
            return df.sort_index()
        except Exception as e:
            print(f"读取表 {table_name} 出错: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    db = StockDB()
    print(f"当前数据库连接: {db.db_url}")

