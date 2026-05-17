import os
import re
import uuid
import hashlib
import time
from collections import OrderedDict
import pandas as pd
from sqlalchemy import create_engine, inspect, text

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
            
        engine_kwargs = {}
        if self.db_url.startswith("postgresql://"):
            engine_kwargs = {
                "pool_pre_ping": True,
                "pool_recycle": 1800,
            }

        self.engine = create_engine(self.db_url, **engine_kwargs)
        self.local_query_cache_enabled = (
            self._is_postgres()
            and os.getenv("DB_LOCAL_QUERY_CACHE", "1").strip().lower() not in {"0", "false", "no"}
        )
        self.local_query_cache_ttl_seconds = int(os.getenv("DB_LOCAL_QUERY_CACHE_TTL_SECONDS", "86400"))
        self.local_query_cache_dir = os.getenv("DB_LOCAL_QUERY_CACHE_DIR", "/tmp/brstock_db_query_cache")
        if self.local_query_cache_enabled:
            os.makedirs(self.local_query_cache_dir, exist_ok=True)
        self.memory_query_cache_enabled = (
            self._is_postgres()
            and os.getenv("DB_MEMORY_QUERY_CACHE", "1").strip().lower() not in {"0", "false", "no"}
        )
        self.memory_query_cache_ttl_seconds = int(os.getenv("DB_MEMORY_QUERY_CACHE_TTL_SECONDS", "900"))
        self.memory_query_cache_max_entries = int(os.getenv("DB_MEMORY_QUERY_CACHE_MAX_ENTRIES", "256"))
        self._memory_query_cache = OrderedDict()

    def _is_postgres(self):
        return self.db_url.startswith("postgresql://")

    def _quote_identifier(self, identifier):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
            raise ValueError(f"Unsafe SQL identifier: {identifier}")
        return f'"{identifier}"'

    def _normalize_price_frame(self, df):
        df = df.copy()
        df.index.name = "timestamp"
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df[~df.index.duplicated(keep="last")]
        return df.sort_index()

    def _cache_key(self, table_name, limit=None, start=None, end=None, columns=None):
        payload = "|".join([
            table_name.lower(),
            str(limit),
            str(start),
            str(end),
            ",".join(columns or ["*"]),
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _cache_path(self, cache_key):
        return os.path.join(self.local_query_cache_dir, f"{cache_key}.pkl")

    def _read_memory_query_cache(self, table_name, limit=None, start=None, end=None, columns=None):
        if not self.memory_query_cache_enabled:
            return None
        cache_key = self._cache_key(table_name, limit=limit, start=start, end=end, columns=columns)
        item = self._memory_query_cache.get(cache_key)
        if not item:
            return None
        ts, value = item
        if time.time() - ts > self.memory_query_cache_ttl_seconds:
            self._memory_query_cache.pop(cache_key, None)
            return None
        self._memory_query_cache.move_to_end(cache_key)
        return value

    def _write_memory_query_cache(self, value, table_name, limit=None, start=None, end=None, columns=None):
        if not self.memory_query_cache_enabled:
            return
        cache_key = self._cache_key(table_name, limit=limit, start=start, end=end, columns=columns)
        self._memory_query_cache[cache_key] = (time.time(), value)
        self._memory_query_cache.move_to_end(cache_key)
        while len(self._memory_query_cache) > self.memory_query_cache_max_entries:
            self._memory_query_cache.popitem(last=False)

    def _read_local_query_cache(self, table_name, limit=None, start=None, end=None, columns=None):
        if not self.local_query_cache_enabled:
            return None
        cache_key = self._cache_key(table_name, limit=limit, start=start, end=end, columns=columns)
        path = self._cache_path(cache_key)
        try:
            if not os.path.exists(path):
                return None
            if time.time() - os.path.getmtime(path) > self.local_query_cache_ttl_seconds:
                return None
            return pd.read_pickle(path)
        except Exception as e:
            print(f"读取本地查询缓存失败 {table_name}: {e}")
            return None

    def _write_local_query_cache(self, value, table_name, limit=None, start=None, end=None, columns=None):
        if not self.local_query_cache_enabled:
            return
        cache_key = self._cache_key(table_name, limit=limit, start=start, end=end, columns=columns)
        path = self._cache_path(cache_key)
        temp_path = f"{path}.{uuid.uuid4().hex[:8]}.tmp"
        try:
            pd.to_pickle(value, temp_path)
            os.replace(temp_path, path)
        except Exception as e:
            print(f"写入本地查询缓存失败 {table_name}: {e}")
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    def _invalidate_local_query_cache(self, table_name):
        self._memory_query_cache.clear()
        if not self.local_query_cache_enabled:
            return
        try:
            for filename in os.listdir(self.local_query_cache_dir):
                if filename.endswith(".pkl"):
                    os.remove(os.path.join(self.local_query_cache_dir, filename))
        except Exception as e:
            print(f"清理本地查询缓存失败 {table_name}: {e}")

    def _save_stock_data_postgres(self, df, table_name):
        """
        Incrementally merge rows into Neon/PostgreSQL without reading the full
        history table back over the network.
        """
        table_sql = self._quote_identifier(table_name)
        temp_table = f"_tmp_{table_name}_{uuid.uuid4().hex[:10]}"
        temp_sql = self._quote_identifier(temp_table)
        inspector = inspect(self.engine)

        with self.engine.begin() as conn:
            if not inspector.has_table(table_name):
                df.to_sql(table_name, conn, if_exists="fail", index=True, chunksize=1000, method="multi")
                self._invalidate_local_query_cache(table_name)
                return

            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
            for col in df.reset_index().columns:
                if col not in existing_columns:
                    dtype = "TIMESTAMP" if col == "timestamp" else (
                        "DOUBLE PRECISION" if pd.api.types.is_numeric_dtype(df[col]) else "TEXT"
                    )
                    conn.execute(text(f"ALTER TABLE {table_sql} ADD COLUMN {self._quote_identifier(col)} {dtype}"))
                    existing_columns.add(col)

            df.to_sql(temp_table, conn, if_exists="fail", index=True, chunksize=1000, method="multi")
            conn.execute(text(f"DELETE FROM {table_sql} WHERE timestamp IN (SELECT timestamp FROM {temp_sql})"))

            insert_columns = ["timestamp", *df.columns.tolist()]
            quoted_columns = ", ".join(self._quote_identifier(col) for col in insert_columns)
            conn.execute(text(
                f"INSERT INTO {table_sql} ({quoted_columns}) "
                f"SELECT {quoted_columns} FROM {temp_sql} ORDER BY timestamp"
            ))
            conn.execute(text(f"DROP TABLE IF EXISTS {temp_sql}"))
        self._invalidate_local_query_cache(table_name)

    def save_stock_data(self, df, table_name):
        """
        将 DataFrame 存入数据库。
        采用合并去重策略。
        """
        if df.empty:
            return
        
        # 统一表名为小写
        table_name = table_name.lower()
        
        try:
            df = self._normalize_price_frame(df)

            if self._is_postgres():
                self._save_stock_data_postgres(df, table_name)
                return
            
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

    def get_stock_data(self, table_name, limit=1000, start=None, end=None, columns=None):
        """
        从数据库读取数据。
        """
        try:
            table_name = table_name.lower()
            cached_df = self._read_memory_query_cache(table_name, limit=limit, start=start, end=end, columns=columns)
            if cached_df is not None:
                return cached_df.copy()

            cached_df = self._read_local_query_cache(table_name, limit=limit, start=start, end=end, columns=columns)
            if cached_df is not None:
                self._write_memory_query_cache(cached_df, table_name, limit=limit, start=start, end=end, columns=columns)
                return cached_df.copy()

            table_sql = self._quote_identifier(table_name)
            selected_columns = ["timestamp", *(columns or [])]
            if columns:
                select_sql = ", ".join(self._quote_identifier(col) for col in selected_columns)
            else:
                select_sql = "*"

            where_clauses = []
            params = {}
            if start is not None:
                where_clauses.append("timestamp >= :start")
                params["start"] = start
            if end is not None:
                where_clauses.append("timestamp <= :end")
                params["end"] = end
            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            limit_sql = ""
            if limit is not None:
                limit_sql = " LIMIT :limit"
                params["limit"] = int(limit)

            query = text(f"SELECT {select_sql} FROM {table_sql}{where_sql} ORDER BY timestamp DESC{limit_sql}")

            df = pd.read_sql(query, self.engine, params=params, index_col='timestamp')
            # 确保索引是 Datetime 类型
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            self._write_memory_query_cache(df, table_name, limit=limit, start=start, end=end, columns=columns)
            self._write_local_query_cache(df, table_name, limit=limit, start=start, end=end, columns=columns)
            return df
        except Exception as e:
            print(f"读取表 {table_name} 出错: {e}")
            return pd.DataFrame()

    def get_stock_data_bounds(self, table_name):
        """
        Return the stored timestamp range with a single-row query.
        """
        try:
            table_name = table_name.lower()
            cached_bounds = self._read_memory_query_cache(table_name, limit="bounds", columns=["timestamp_bounds"])
            if cached_bounds is not None:
                return cached_bounds

            cached_bounds = self._read_local_query_cache(table_name, limit="bounds", columns=["timestamp_bounds"])
            if cached_bounds is not None:
                self._write_memory_query_cache(cached_bounds, table_name, limit="bounds", columns=["timestamp_bounds"])
                return cached_bounds

            table_sql = self._quote_identifier(table_name)
            query = text(f"SELECT MIN(timestamp) AS start_ts, MAX(timestamp) AS end_ts FROM {table_sql}")
            with self.engine.connect() as conn:
                row = conn.execute(query).fetchone()
            if not row or row[0] is None or row[1] is None:
                return None
            bounds = {
                "start": pd.to_datetime(row[0]).tz_localize(None),
                "end": pd.to_datetime(row[1]).tz_localize(None),
            }
            self._write_memory_query_cache(bounds, table_name, limit="bounds", columns=["timestamp_bounds"])
            self._write_local_query_cache(bounds, table_name, limit="bounds", columns=["timestamp_bounds"])
            return bounds
        except Exception as e:
            print(f"读取表 {table_name} 时间范围出错: {e}")
            return None

if __name__ == "__main__":
    db = StockDB()
    print(f"当前数据库连接: {db.db_url}")
