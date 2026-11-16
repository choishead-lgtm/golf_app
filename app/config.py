"""API 키와 설정. 호스팅 서비스의 '환경 변수' 또는 .env 파일에서 읽습니다."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    @property
    def kma_service_key(self) -> str:  # 공공데이터포털 기상청 단기예보 (Decoding 키)
        return os.getenv("KMA_SERVICE_KEY", "").strip()

    @property
    def tmap_app_key(self) -> str:  # TMAP App Key
        return os.getenv("TMAP_APP_KEY", "").strip()

    @property
    def naver_client_id(self) -> str:  # 네이버 개발자센터 Client ID
        return os.getenv("NAVER_CLIENT_ID", "").strip()

    @property
    def naver_client_secret(self) -> str:  # 네이버 개발자센터 Client Secret
        return os.getenv("NAVER_CLIENT_SECRET", "").strip()

    @property
    def http_timeout(self) -> float:
        return float(os.getenv("HTTP_TIMEOUT", "8"))


settings = Settings()
