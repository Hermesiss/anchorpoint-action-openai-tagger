import anchorpoint as ap
import os

from common.settings import tagger_settings


def init_openai_key() -> str:
    open_api_key = tagger_settings.openai_api_key
    if not open_api_key:
        ap.UI().show_error("No API key", "Please set up an API key in the settings")
        raise ValueError("No API key set")

    os.environ["OPENAI_API_KEY"] = open_api_key
    return open_api_key


OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
