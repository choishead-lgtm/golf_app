"""아주 작은 메모리 캐시 (추가 설치 없이 동작). 같은 요청을 반복해서 외부 API에 보내지 않게 해줍니다."""
import time


class TTLCache:
    def __init__(self, ttl: float, maxsize: int = 2000):
        self.ttl, self.maxsize = ttl, maxsize
        self._d: dict = {}

    def get(self, key):
        item = self._d.get(key)
        if item is None:
            return None
        value, expires = item
        if expires < time.monotonic():
            self._d.pop(key, None)
            return None
        return value

    def set(self, key, value):
        if len(self._d) >= self.maxsize:  # 가장 오래된 것부터 정리
            for k in list(self._d)[: self.maxsize // 10 or 1]:
                self._d.pop(k, None)
        self._d[key] = (value, time.monotonic() + self.ttl)

    def clear(self):
        self._d.clear()


weather_cache = TTLCache(ttl=60 * 60)       # 기상청: 같은 격자·발표시각
search_cache = TTLCache(ttl=24 * 60 * 60)   # 장소 검색
food_cache = TTLCache(ttl=30 * 60)          # 맛집
