"""위경도 ↔ 기상청 격자(nx, ny) 변환 (기상청 제공 LCC 투영 공식)."""
import math

RE = 6371.00877  # 지구 반경(km)
GRID = 5.0       # 격자 간격(km)
SLAT1, SLAT2 = 30.0, 60.0  # 표준위도
OLON, OLAT = 126.0, 38.0   # 기준점 경도·위도
XO, YO = 43, 136           # 기준점 격자 좌표

_D = math.pi / 180.0
_re = RE / GRID
_s1, _s2 = SLAT1 * _D, SLAT2 * _D
_olon, _olat = OLON * _D, OLAT * _D
_sn = math.log(math.cos(_s1) / math.cos(_s2)) / math.log(
    math.tan(math.pi / 4 + _s2 / 2) / math.tan(math.pi / 4 + _s1 / 2)
)
_sf = math.tan(math.pi / 4 + _s1 / 2) ** _sn * math.cos(_s1) / _sn
_ro = _re * _sf / math.tan(math.pi / 4 + _olat / 2) ** _sn


def latlon_to_grid(lat: float, lon: float) -> tuple[int, int]:
    ra = _re * _sf / math.tan(math.pi / 4 + lat * _D / 2) ** _sn
    theta = lon * _D - _olon
    if theta > math.pi:
        theta -= 2 * math.pi
    if theta < -math.pi:
        theta += 2 * math.pi
    theta *= _sn
    nx = int(ra * math.sin(theta) + XO + 0.5)
    ny = int(_ro - ra * math.cos(theta) + YO + 0.5)
    return nx, ny


def is_in_korea(lat: float, lon: float) -> bool:
    """기상청 단기예보가 제공되는 대략적인 범위."""
    return 32.5 <= lat <= 39.0 and 124.0 <= lon <= 132.0
