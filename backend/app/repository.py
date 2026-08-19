import sqlite3
from pathlib import Path
from typing import Any


class Repository:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS orders (
              order_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, product_name TEXT NOT NULL,
              amount REAL NOT NULL, status TEXT NOT NULL, tracking_no TEXT, carrier TEXT
            );
            CREATE TABLE IF NOT EXISTS refunds (
              refund_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL,
              order_id TEXT NOT NULL, user_id TEXT NOT NULL, reason TEXT NOT NULL,
              amount REAL NOT NULL, status TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS feedback (
              id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
              message_id TEXT, rating INTEGER NOT NULL, comment TEXT,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.executemany(
                "INSERT OR IGNORE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    ("ORD-20260801", "demo-user", "云朵护颈枕", 299.0, "已发货", "SF1234567890", "顺丰速运"),
                    ("ORD-20260802", "demo-user", "星空降噪耳机", 799.0, "已完成", "YT9876543210", "圆通速递"),
                    ("ORD-OTHER001", "other-user", "隐私测试商品", 999.0, "已发货", "SECRET", "测试物流"),
                ],
            )

    def get_order(self, order_id: str, user_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE order_id = ? AND user_id = ?", (order_id, user_id)
            ).fetchone()
        return dict(row) if row else None

    def create_refund(self, order: dict[str, Any], reason: str, idem_key: str) -> dict[str, Any]:
        refund_id = "RF-" + idem_key[:12].upper()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO refunds(refund_id,idempotency_key,order_id,user_id,reason,amount,status) VALUES(?,?,?,?,?,?,?)",
                (refund_id, idem_key, order["order_id"], order["user_id"], reason, order["amount"], "处理中"),
            )
            row = conn.execute("SELECT * FROM refunds WHERE idempotency_key = ?", (idem_key,)).fetchone()
        return dict(row)

    def add_feedback(self, session_id: str, message_id: str | None, rating: int, comment: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO feedback(session_id,message_id,rating,comment) VALUES(?,?,?,?)",
                (session_id, message_id, rating, comment),
            )

