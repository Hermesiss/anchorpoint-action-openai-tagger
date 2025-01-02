import anchorpoint as ap
import apsync as aps
import os

def init_openai_key() -> str:
    local_settings = aps.Settings("ht_ai_tagger")
    open_api_key = local_settings.get("openai_api_key")
    if not open_api_key:
        ap.UI().show_error("No API key", "Please set up an API key in the settings")
        raise ValueError("No API key set")

    os.environ["OPENAI_API_KEY"] = open_api_key
    return open_api_key

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"