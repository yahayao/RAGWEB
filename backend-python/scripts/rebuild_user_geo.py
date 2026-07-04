#!/usr/bin/env python3
"""rebuild_user_geo.py — 分批回填已有用户的 IP 地理位置数据

只更新 chat_users 的三个地理字段: region, country_code, country_name。
不修改 id, username, ip, create_time, manual_geo 或任何其他表/列。

用法:
  python scripts/rebuild_user_geo.py
  python scripts/rebuild_user_geo.py --dry-run
  python scripts/rebuild_user_geo.py --batch-size 500 --limit 1000
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

# 确保可以导入项目模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import update

from database import ChatUser, SessionLocal, lookup_geo


def main() -> None:
    parser = argparse.ArgumentParser(description="回填已有用户 IP 地理位置数据")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不提交数据库")
    parser.add_argument("--batch-size", type=int, default=500, help="每批处理数量（默认 500）")
    parser.add_argument("--limit", type=int, default=0, help="最多处理用户数（0=全部）")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # 查询需要处理的用户
        query = db.query(ChatUser.id, ChatUser.ip, ChatUser.region, ChatUser.country_code, ChatUser.country_name)
        if args.limit > 0:
            query = query.limit(args.limit)

        users = query.all()
        total = len(users)
        print(f"共 {total} 个用户待处理")

        china_count = 0
        overseas_count = 0
        unknown_count = 0
        failed_count = 0

        for i, user in enumerate(users):
            user_id = int(user.id)
            ip = user.ip or ""

            try:
                geo = lookup_geo(ip)
            except Exception as exc:
                print(f"  [{user_id}] 查询失败: {exc}")
                failed_count += 1
                continue

            # 统计
            if geo.region in ("Unknown", ""):
                unknown_count += 1
            elif geo.region == "海外":
                overseas_count += 1
            else:
                china_count += 1

            if not args.dry_run:
                db.execute(
                    update(ChatUser)
                    .where(ChatUser.id == user_id)
                    .values(
                        region=geo.region,
                        country_code=geo.country_code,
                        country_name=geo.country_name,
                    )
                )

            if (i + 1) % args.batch_size == 0:
                if not args.dry_run:
                    db.commit()
                print(f"  已处理 {i + 1}/{total} ...")

        # 最后一批提交
        if not args.dry_run and (i + 1) % args.batch_size != 0:
            db.commit()

        if args.dry_run:
            print("\n[Dry Run] 统计结果（未写入数据库）:")
        else:
            print("\n更新完成:")
        print(f"  总计: {total}")
        print(f"  中国省份: {china_count}")
        print(f"  海外: {overseas_count}")
        print(f"  Unknown: {unknown_count}")
        print(f"  失败: {failed_count}")

    except Exception as exc:
        db.rollback()
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
