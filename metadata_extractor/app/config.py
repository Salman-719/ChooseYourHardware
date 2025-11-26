import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

PROMPTS_DIR = BASE_DIR / "prompts"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_LLM_MODEL = os.getenv("OPENAI_LLM_MODEL")
if OPENAI_API_KEY is None:
    OPENAI_API_KEY = input("Please enter your OpenAI API Key: ")

if OPENAI_LLM_MODEL is None:
    OPENAI_LLM_MODEL = "o4-mini"

OPENAI_WEB_MODEL = os.getenv("OPENAI_WEB_MODEL") or OPENAI_LLM_MODEL
HARDWARE_LLM_MODEL = os.getenv("HARDWARE_LLM_MODEL") or OPENAI_LLM_MODEL

ASKER_PROMPT_PATH = PROMPTS_DIR / "metadata_extractor_asker.txt"
UPDATER_PROMPT_PATH = PROMPTS_DIR / "metadata_extractor_updater.txt"
MODEL_FIELDS_PATH = PROMPTS_DIR / "model_fields.json"
LAYER_TYPES_PATH = PROMPTS_DIR / "layer_types.json"
WEB_SEARCH_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "web_search_system_prompt.txt"
HARDWARE_CRAWLER_PROMPT_PATH = PROMPTS_DIR / "hardware_crawler_prompt.txt"

with open(ASKER_PROMPT_PATH) as f:
    ASKER_PROMPT = f.read()

with open(UPDATER_PROMPT_PATH) as f:
    UPDATER_PROMPT = f.read()

with open(MODEL_FIELDS_PATH) as f:
    MODEL_FIELDS = json.loads(f.read())

with open(LAYER_TYPES_PATH) as f:
    LAYER_TYPES = {"cnn": json.loads(f.read())}

with open(WEB_SEARCH_SYSTEM_PROMPT_PATH) as f:
    WEB_SEARCH_SYSTEM_PROMPT = f.read().strip()
with open(HARDWARE_CRAWLER_PROMPT_PATH) as f:
    HARDWARE_CRAWLER_PROMPT = f.read().strip()

# Hardware crawler settings
HARDWARE_FEED_URL = os.getenv("HARDWARE_FEED_URL", "https://example.com")
HARDWARE_DB_PATH = Path(os.getenv("HARDWARE_DB_PATH", BASE_DIR / "hardware.db"))
HARDWARE_CRAWL_INTERVAL_SECONDS = int(os.getenv("HARDWARE_CRAWL_INTERVAL_SECONDS", 1800))
