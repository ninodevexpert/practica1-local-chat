from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    base_url: str = "http://127.0.0.1:1234/v1"
    timeout_seconds: float = 90.0
    default_temperature: float = 0.7
    default_max_tokens: int = 512
