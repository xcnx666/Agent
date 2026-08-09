#!/usr/bin/env python3
"""重置 Open WebUI 中与「模型引擎」相关的持久化配置。

背景
----
Open WebUI 的大量配置是 PersistentConfig：**首次启动**时把环境变量的值写入
``webui.db``，之后即使修改环境变量也不再生效（DB 优先）。

如果第一次启动时还没配好「零本地模型下载」，DB 里就会留下
``rag.embedding_engine = ""``（= 使用本地 sentence-transformers），
导致后续启动仍尝试加载本地权重并在离线模式下报错。

本脚本删除这些键，使下次启动重新从 ``config/webui.env`` 读取并写回正确值。
不会触碰对话记录、用户、知识库等任何业务数据。

用法
----
    ./scripts/reset_model_config.py            # 重置默认键
    ./scripts/reset_model_config.py --dry-run  # 只看会改什么，不落盘
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# 仅重置「决定是否加载本地模型」的键，其余配置一律保留
TARGET_KEYS = [
    "rag.embedding_engine",
    "rag.embedding_model",
    "rag.reranking_engine",
    "rag.reranking_model",
    "audio.stt.engine",
    "audio.stt.whisper_model",
    "audio.tts.engine",
]

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "webui" / "webui.db"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB), help="webui.db 路径")
    parser.add_argument(
        "--dry-run", action="store_true", help="只打印将删除的键，不实际修改"
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"· 数据库不存在，无需重置: {db_path}")
        print("  （首次启动会直接采用 config/webui.env 的值，本来就是对的）")
        return 0

    conn = sqlite3.connect(db_path)
    try:
        existing = {
            key: value
            for key, value in conn.execute(
                "SELECT key, value FROM config WHERE key IN ({})".format(
                    ",".join("?" * len(TARGET_KEYS))
                ),
                TARGET_KEYS,
            )
        }

        if not existing:
            print("· 没有需要重置的键，配置已是干净状态。")
            return 0

        print(f"数据库: {db_path}")
        print("将删除以下持久化配置（下次启动从 config/webui.env 重新读取）：")
        for key, value in existing.items():
            print(f"  - {key:28} 当前值 = {value}")

        if args.dry_run:
            print("\n[dry-run] 未做任何修改。")
            return 0

        conn.executemany(
            "DELETE FROM config WHERE key = ?", [(k,) for k in existing]
        )
        conn.commit()
        print(f"\n✔ 已重置 {len(existing)} 项。请重启服务：")
        print("    ./scripts/stop_webui.sh && ./scripts/start_webui.sh --daemon")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
