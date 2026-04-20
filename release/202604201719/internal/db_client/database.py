import sqlite3
import pandas as pd
import os

class StockDB:
    def __init__(self, db_path="/Users/tuxy/Codes/Github2/BRstock1/Data/stocks.db"):
        self.db_path = db_path
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def save_stock_data(self, df, table_name):
        """
        将 DataFrame 存入数据库。
        采用合并去重策略，自动处理列名不一致的情况（如 ETF 额外的 Capital Gains 列）。
        """
        if df.empty:
            return
        
        # 统一索引名
        df = df.copy()
        df.index.name = 'timestamp'
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                # 尝试读取现有数据
                existing_df = pd.read_sql(f'SELECT * FROM "{table_name}"', conn, index_col='timestamp', parse_dates=True)
                # 合并新旧数据
                combined = pd.concat([existing_df, df])
                # 根据时间戳去重，保持最新的数据
                combined = combined[~combined.index.duplicated(keep='last')]
                combined.sort_index(inplace=True)
                # 全量替换存回
                combined.to_sql(table_name, conn, if_exists='replace', index=True)
            except Exception:
                # 如果表不存在或读取失败，则直接创建
                df.to_sql(table_name, conn, if_exists='replace', index=True)

    def get_stock_data(self, table_name, limit=1000):
        """
        从数据库读取数据。
        """
        with sqlite3.connect(self.db_path) as conn:
            try:
                query = f'SELECT * FROM "{table_name}" ORDER BY timestamp DESC LIMIT {limit}'
                df = pd.read_sql(query, conn, index_col='timestamp', parse_dates=True)
                # 因为是按 DESC 取的，展示时通常希望按时间正序
                return df.sort_index()
            except Exception as e:
                print(f"读取表 {table_name} 出错: {e}")
                return pd.DataFrame()

if __name__ == "__main__":
    db = StockDB()
    print(f"数据库文件位于: {os.path.abspath(db.db_path)}")
