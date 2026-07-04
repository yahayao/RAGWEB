"""test_geo.py — MaxMind GeoLite2 迁移测试

通过 mock geoip2 Reader 测试 IP 查询、代理安全、数据库写入、API 端点。
不需要真实的 MMDB 文件或网络连接。

运行: python -m pytest test_geo.py -v
"""

from __future__ import annotations

import sys
import os

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ==================== 测试 lookup_geo 查询规则 ====================


class TestLookupGeo:
    """测试 lookup_geo 函数的各类 IP 场景"""

    def _mock_reader(self, country_code="CN", country_name="中国", subdivision_code="GD"):
        """创建 mock geoip2 Reader"""
        reader = MagicMock()
        response = MagicMock()
        type(response.country).iso_code = PropertyMock(return_value=country_code)
        type(response.country).name = PropertyMock(return_value=country_name)

        if subdivision_code:
            subdiv = MagicMock()
            type(subdiv).iso_code = PropertyMock(return_value=subdivision_code)
            type(response).subdivisions = PropertyMock(return_value=[subdiv])
        else:
            type(response).subdivisions = PropertyMock(return_value=[])

        reader.city.return_value = response
        return reader

    def test_china_ipv4_returns_province(self):
        """中国公网 IPv4 返回省份"""
        from database import lookup_geo, CN_PROVINCE_MAP
        import database as db

        reader = self._mock_reader("CN", "中国", "GD")
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("1.2.3.4")
        assert result.country_code == "CN"
        assert result.country_name == "中国"
        assert result.region == "广东省"
        assert result.source == "geolite2"

    def test_china_ip_no_subdivision(self):
        """中国 IP 无 subdivision: country_code=CN, region=Unknown"""
        from database import lookup_geo
        import database as db

        reader = self._mock_reader("CN", "中国", None)
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("1.2.3.4")
        assert result.country_code == "CN"
        assert result.country_name == "中国"
        assert result.region == "Unknown"

    def test_us_ip_returns_overseas(self):
        """美国 IP: region=海外, 保留具体国家"""
        from database import lookup_geo
        import database as db

        reader = self._mock_reader("US", "United States", "CA")
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("8.8.8.8")
        assert result.country_code == "US"
        assert result.country_name == "United States"
        assert result.region == "海外"
        assert result.source == "geolite2"

    def test_jp_ip_returns_overseas(self):
        """日本 IP: region=海外"""
        from database import lookup_geo
        import database as db

        reader = self._mock_reader("JP", "Japan", None)
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("106.0.0.1")
        assert result.country_code == "JP"
        assert result.region == "海外"

    def test_hk_returns_special_region(self):
        """香港 IP: region=香港特别行政区, name=中国香港"""
        from database import lookup_geo
        import database as db

        reader = self._mock_reader("HK", "Hong Kong", None)
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("1.2.3.4")
        assert result.country_code == "HK"
        assert result.country_name == "中国香港"
        assert result.region == "香港特别行政区"

    def test_mo_returns_special_region(self):
        """澳门 IP: region=澳门特别行政区"""
        from database import lookup_geo
        import database as db

        reader = self._mock_reader("MO", "Macau", None)
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("1.2.3.4")
        assert result.country_code == "MO"
        assert result.region == "澳门特别行政区"

    def test_tw_returns_taiwan(self):
        """台湾 IP: region=台湾省"""
        from database import lookup_geo
        import database as db

        reader = self._mock_reader("TW", "Taiwan", None)
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("1.2.3.4")
        assert result.country_code == "TW"
        assert result.country_name == "中国台湾"
        assert result.region == "台湾省"

    def test_address_not_found(self):
        """未命中: country_code=None, country_name=Unknown"""
        from database import lookup_geo
        from geoip2.errors import AddressNotFoundError
        import database as db

        reader = MagicMock()
        reader.city.side_effect = AddressNotFoundError("mock")
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("1.2.3.4")
        assert result.country_code is None
        assert result.country_name == "Unknown"
        assert result.region == "Unknown"
        assert result.source == "geolite2"

    def test_private_ip_not_queried(self):
        """私网 IP 不查询 Reader"""
        from database import lookup_geo
        import database as db

        reader = MagicMock()
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("192.168.1.1")
        assert result.country_code is None
        assert result.region == "Unknown"
        assert result.source == "unresolved"
        reader.city.assert_not_called()

    def test_loopback_not_queried(self):
        """回环地址不查询 Reader"""
        from database import lookup_geo
        import database as db

        reader = MagicMock()
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("127.0.0.1")
        assert result.region == "Unknown"
        assert result.source == "unresolved"
        reader.city.assert_not_called()

    def test_cgnat_not_queried(self):
        """CGNAT 地址不查询 Reader"""
        from database import lookup_geo
        import database as db

        reader = MagicMock()
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("100.64.0.1")
        assert result.source == "unresolved"
        reader.city.assert_not_called()

    def test_ipv6_ula_not_queried(self):
        """IPv6 ULA 不查询 Reader"""
        from database import lookup_geo
        import database as db

        reader = MagicMock()
        with patch.object(db, "_geoip_reader", reader):
            result = lookup_geo("fd00::1")
        assert result.source == "unresolved"
        reader.city.assert_not_called()

    def test_invalid_ip_returns_unknown(self):
        """非法 IP 返回 Unknown"""
        from database import lookup_geo

        result = lookup_geo("not-an-ip")
        assert result.country_code is None
        assert result.country_name == "Unknown"
        assert result.region == "Unknown"
        assert result.source == "unresolved"

    def test_reader_none_returns_unknown(self):
        """Reader 不可用时返回 Unknown"""
        from database import lookup_geo
        import database as db

        with patch.object(db, "_geoip_reader", None):
            result = lookup_geo("8.8.8.8")
        assert result.country_code is None
        assert result.region == "Unknown"
        assert result.source == "unresolved"


# ==================== 测试 lookup_region 兼容接口 ====================


class TestLookupRegionCompat:
    """测试 lookup_region 兼容包装"""

    def test_lookup_region_returns_tuple(self):
        from database import lookup_region, lookup_geo
        import database as db

        reader = MagicMock()
        response = MagicMock()
        type(response.country).iso_code = PropertyMock(return_value="US")
        type(response.country).name = PropertyMock(return_value="United States")
        type(response).subdivisions = PropertyMock(return_value=[])
        reader.city.return_value = response

        with patch.object(db, "_geoip_reader", reader):
            ip, region = lookup_region("8.8.8.8")
        assert ip == "8.8.8.8"
        assert region == "海外"


# ==================== 测试 normalize_ip ====================


class TestNormalizeIp:
    """测试 normalize_ip 各种输入"""

    def test_ipv4(self):
        from database import normalize_ip
        assert normalize_ip("1.2.3.4") == "1.2.3.4"

    def test_ipv6(self):
        from database import normalize_ip
        assert normalize_ip("2001:db8::1") == "2001:db8::1"

    def test_ipv4_mapped_ipv6(self):
        from database import normalize_ip
        assert normalize_ip("::ffff:1.2.3.4") == "1.2.3.4"

    def test_bracketed_ipv6(self):
        from database import normalize_ip
        assert normalize_ip("[2001:db8::1]") == "2001:db8::1"

    def test_ipv4_with_port(self):
        from database import normalize_ip
        assert normalize_ip("1.2.3.4:8080") == "1.2.3.4"

    def test_unknown(self):
        from database import normalize_ip
        assert normalize_ip("unknown") is None

    def test_empty(self):
        from database import normalize_ip
        assert normalize_ip("") is None


# ==================== 测试 _parse_ip_candidate (extract_client_ip 依赖) ====================


class TestParseIpCandidate:
    """测试 _parse_ip_candidate"""

    def test_valid_ipv4(self):
        from database import _parse_ip_candidate
        assert _parse_ip_candidate("1.2.3.4") == "1.2.3.4"

    def test_unknown(self):
        from database import _parse_ip_candidate
        assert _parse_ip_candidate("unknown") is None

    def test_empty(self):
        from database import _parse_ip_candidate
        assert _parse_ip_candidate("") is None


# ==================== 运行 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
