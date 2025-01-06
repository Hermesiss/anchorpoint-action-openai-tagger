import anchorpoint as ap
import apsync as aps
import os

from package_settings import TaggerSettings


def init_openai_key() -> str:
    settings = TaggerSettings()
    open_api_key = settings.openai_api_key
    if not open_api_key:
        ap.UI().show_error("No API key", "Please set up an API key in the settings")
        raise ValueError("No API key set")

    os.environ["OPENAI_API_KEY"] = open_api_key
    return open_api_key


OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
