from __future__ import annotations

import ipaddress
from functools import lru_cache


# Publicly registered or commonly observed LTE/5G address pools for the three
# nationwide Korean mobile carriers. KT and LG U+ share portions of their
# address space with fixed-line services, so operators may override this list
# through FOCUSAWAY_CARRIER_IP_RANGES when stricter classification is needed.
KOREAN_CARRIER_IP_RANGES = (
    # SK Telecom
    "27.160.0.0-27.183.255.255",
    "42.16.0.0-42.47.255.255",
    "58.102.0.0-58.103.255.255",
    "61.250.0.0-61.250.63.255",
    "111.218.0.0-111.219.255.255",
    "113.216.0.0-113.217.255.255",
    "114.52.0.0-114.53.255.255",
    "123.228.0.0-123.229.255.255",
    "124.0.0.0-124.3.255.255",
    "124.136.0.0-124.139.255.255",
    "180.132.0.0-180.135.255.255",
    "203.226.192.0-203.226.252.255",
    "203.236.0.0-203.236.43.255",
    "211.63.0.0-211.63.31.255",
    "211.110.240.0-211.110.255.255",
    "211.111.176.0-211.111.191.255",
    "211.115.0.0-211.115.15.255",
    "211.188.128.0-211.188.255.255",
    "211.234.128.0-211.234.239.255",
    "211.234.244.0-211.234.255.255",
    "211.235.64.0-211.235.191.255",
    "211.240.128.0-211.240.255.255",
    "219.252.0.0-219.253.255.255",
    "220.103.0.0-220.103.255.255",
    "223.32.0.0-223.63.255.255",
    "2001:2d8::/32",
    "2001:f28::/32",
    # KT
    "1.96.0.0-1.111.255.255",
    "39.4.0.0-39.7.255.255",
    "49.16.0.0-49.31.255.255",
    "49.56.0.0-49.63.255.255",
    "61.252.32.0-61.252.47.255",
    "110.68.0.0-110.71.255.255",
    "116.200.0.0-116.201.255.255",
    "118.234.0.0-118.235.255.255",
    "163.213.0.0-163.213.255.255",
    "163.222.0.0-163.222.255.255",
    "163.229.0.0-163.229.255.255",
    "163.255.0.0-163.255.255.255",
    "175.216.0.0-175.223.255.255",
    "211.246.0.0-211.246.127.255",
    "2001:e60::/32",
    # LG U+
    "106.96.0.0-106.103.255.255",
    "117.110.0.0-117.111.255.255",
    "180.210.192.0-180.210.199.255",
    "203.82.240.0-203.82.247.255",
    "211.36.128.0-211.36.159.255",
    "211.234.0.0-211.234.95.255",
    "223.168.0.0-223.175.255.255",
    "2001:4430::/32",
)


def _range_to_networks(value: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    text = value.strip()
    if not text:
        return []
    if "-" not in text:
        return [ipaddress.ip_network(text, strict=False)]
    start_text, end_text = (part.strip() for part in text.split("-", 1))
    start = ipaddress.ip_address(start_text)
    end = ipaddress.ip_address(end_text)
    if start.version != end.version or int(start) > int(end):
        raise ValueError(f"Invalid IP range: {value}")
    return list(ipaddress.summarize_address_range(start, end))


@lru_cache(maxsize=16)
def parse_ip_ranges(raw_ranges: str) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    values = [item.strip() for item in raw_ranges.replace("\n", ",").split(",") if item.strip()]
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for value in values:
        networks.extend(_range_to_networks(value))
    return tuple(networks)


DEFAULT_KOREAN_CARRIER_IP_RANGES = ",".join(KOREAN_CARRIER_IP_RANGES)


def ip_in_ranges(ip_value: str, raw_ranges: str) -> bool:
    try:
        address = ipaddress.ip_address(str(ip_value).strip())
        networks = parse_ip_ranges(raw_ranges)
    except ValueError:
        return False
    return any(address.version == network.version and address in network for network in networks)

