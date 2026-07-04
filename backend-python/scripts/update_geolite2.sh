#!/bin/bash
# update_geolite2.sh — 使用 MaxMind 官方 geoipupdate 工具更新 GeoLite2-City 数据库
#
# 前置条件:
#   1. 安装 geoipupdate: https://github.com/maxmind/geoipupdate
#   2. 配置 /etc/GeoIP.conf（参考 geoip/GeoIP.conf.example）
#
# 用法:
#   bash scripts/update_geolite2.sh
#
# Cron 示例（每 12 小时）:
#   17 */12 * * * /opt/ragweb/backend-python/scripts/update_geolite2.sh >> /var/log/geoipupdate.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
GEOIP_DIR="$PROJECT_DIR/geoip"
MMDB_FILE="$GEOIP_DIR/GeoLite2-City.mmdb"

# 备份当前数据库（如果存在）
if [ -f "$MMDB_FILE" ]; then
    cp "$MMDB_FILE" "$MMDB_FILE.bak"
fi

# 执行更新
if geoipupdate -f /etc/GeoIP.conf -d "$GEOIP_DIR"; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') GeoLite2-City 更新成功"
    # 更新成功后删除备份
    rm -f "$MMDB_FILE.bak"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') GeoLite2-City 更新失败，已保留旧数据库"
    # 恢复备份
    if [ -f "$MMDB_FILE.bak" ]; then
        mv "$MMDB_FILE.bak" "$MMDB_FILE"
    fi
    exit 1
fi
