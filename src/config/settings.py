from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class UserCredentials:
    username: str
    password: str

    @property
    def auth_tuple(self) -> tuple[str, str]:
        return (self.username, self.password)


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("API_BASE_URL", "http://localhost:8080")
    base_path: str = os.getenv("API_BASE_PATH", "/api/v1")

    user1: UserCredentials = UserCredentials(
        username=os.getenv("USER1_USERNAME", "test1"),
        password=os.getenv("USER1_PASSWORD", "test123"),
    )
    user2: UserCredentials = UserCredentials(
        username=os.getenv("USER2_USERNAME", "test2"),
        password=os.getenv("USER2_PASSWORD", "test456"),
    )

    load_test_users: int = int(os.getenv("LOAD_TEST_USERS", "10"))
    load_test_duration: int = int(os.getenv("LOAD_TEST_DURATION", "60"))
    load_test_spawn_rate: int = int(os.getenv("LOAD_TEST_SPAWN_RATE", "2"))
    load_test_target_rpm: int = int(os.getenv("LOAD_TEST_TARGET_RPM", "1000"))

    @property
    def api_url(self) -> str:
        return f"{self.base_url}{self.base_path}"


settings = Settings()
