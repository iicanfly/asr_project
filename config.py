import os
from dotenv import load_dotenv

load_dotenv()

USE_INTRANET = os.getenv('USE_INTRANET', 'False').strip().lower() in ('true', '1', 'yes')

if not USE_INTRANET:
    API_KEY = os.getenv('ONLINE_API_KEY', '')
    BASE_URL = os.getenv('ONLINE_BASE_URL', '')
    ASR_MODEL = os.getenv('ONLINE_ASR_MODEL', 'qwen3-asr-flash-2026-02-10')
    LLM_MODEL = os.getenv('ONLINE_LLM_MODEL', 'qwen-plus-2025-07-28')
    ASR_BASE_URL = os.getenv('ONLINE_ASR_BASE_URL', BASE_URL)
    ASR_API_KEY = os.getenv('ONLINE_ASR_API_KEY', API_KEY)
    ASR_MODE = os.getenv('ONLINE_ASR_MODE', 'chat')
else:
    API_KEY = os.getenv('INTRANET_API_KEY', '')
    BASE_URL = os.getenv('INTRANET_BASE_URL', '')
    ASR_MODEL = os.getenv('INTRANET_ASR_MODEL', 'qwen-asr')
    LLM_MODEL = os.getenv('INTRANET_LLM_MODEL', 'qwen2.5-7b')
    ASR_BASE_URL = os.getenv('INTRANET_ASR_BASE_URL', BASE_URL)
    ASR_API_KEY = os.getenv('INTRANET_ASR_API_KEY', API_KEY)
    ASR_MODE = os.getenv('INTRANET_ASR_MODE', 'transcriptions')

HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '6543'))
EXPORT_DIR = os.getenv('EXPORT_DIR', 'exports')
TEMP_DIR = os.getenv('TEMP_DIR', 'temp_audio')

ENABLE_HTTPS = os.getenv('ENABLE_HTTPS', 'False').strip().lower() in ('true', '1', 'yes')
SSL_CERT = os.getenv('SSL_CERT', 'cert/cert.pem')
SSL_KEY = os.getenv('SSL_KEY', 'cert/key.pem')
