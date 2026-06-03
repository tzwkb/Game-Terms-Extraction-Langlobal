import os

LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_enabled": True,
    "console_enabled": True,
}

VOTE_TEMPS = [0, 0.3, 0.7]

EXTRACTOR_CONFIG = {
    "max_tokens": 65536,
    "max_concurrent": 20,
    "timeout": 120.0,
    "max_retries": 3,
}

TRANSLATOR_CONFIG = {
    "temperature": 0.1,
    "max_tokens": 65536,
    "max_concurrent": 20,
    "timeout": 120.0,
    "max_retries": 3,
}



def get_token_param_name(model: str) -> str:
    return "max_tokens"
