import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_default")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "default_secret")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "aegis_webhook_secret_2026")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Financial Safety Thresholds
    MAX_ORDER_VALUE_INR: float = 15000.0
    MAX_RETRY_LIMIT: int = 3
    APPROVED_MERCHANT_IDS: List[str] = ["merchant_rzp_001"]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()