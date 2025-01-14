# This example demonstrates how to create a simple dialog in Anchorpoint
import anchorpoint as ap
import apsync as aps
import os


class TaggerSettings:
    def __init__(self):
        self.local_settings = aps.Settings("ht_ai_tagger")
        self.load()

    def get(self, key: str, default: object = "") -> object:
        return self.local_settings.get(key, default)

    def set(self, key: str, value: object):
        self.local_settings.set(key, value)

    openai_api_key: str
    file_label_ai_types: bool
    file_label_ai_genres: bool
    file_label_ai_objects: bool
    file_label_ai_objects_min: int
    file_label_ai_objects_max: int
    folder_use_ai_engines: bool
    folder_use_ai_types: bool
    folder_use_ai_genres: bool
    debug_log: bool

    def any_file_tags_selected(self):
        return self.file_label_ai_types or self.file_label_ai_genres or self.file_label_ai_objects

    def any_folder_tags_selected(self):
        return self.folder_use_ai_engines or self.folder_use_ai_types or self.folder_use_ai_genres

    def load(self):
        self.openai_api_key = str(self.get("openai_api_key"))
        self.file_label_ai_types = bool(self.get("file_label_ai_types", True))
        self.file_label_ai_genres = bool(self.get("file_label_ai_genres", True))
        self.file_label_ai_objects = bool(self.get("file_label_ai_objects", True))
        self.file_label_ai_objects_min = int(str(self.get("file_label_ai_objects_min", 1)))
        self.file_label_ai_objects_max = int(str(self.get("file_label_ai_objects_max", 5)))
        self.folder_use_ai_engines = bool(self.get("folder_use_ai_engines", True))
        self.folder_use_ai_types = bool(self.get("folder_use_ai_types", True))
        self.folder_use_ai_genres = bool(self.get("folder_use_ai_genres", True))
        self.debug_log = bool(self.get("debug_log", False))

    def store(self):
        self.set("openai_api_key", self.openai_api_key)
        self.set("file_label_ai_types", self.file_label_ai_types)
        self.set("file_label_ai_genres", self.file_label_ai_genres)
        self.set("file_label_ai_objects", self.file_label_ai_objects)
        self.set("file_label_ai_objects_min", self.file_label_ai_objects_min)
        self.set("file_label_ai_objects_max", self.file_label_ai_objects_max)
        self.set("folder_use_ai_engines", self.folder_use_ai_engines)
        self.set("folder_use_ai_types", self.folder_use_ai_types)
        self.set("folder_use_ai_genres", self.folder_use_ai_genres)
        self.set("debug_log", self.debug_log)
        self.local_settings.store()


settings = TaggerSettings()


def apply_callback(dialog: ap.Dialog):
    token = str(dialog.get_value("token"))
    if token == "":
        ap.UI().show_error("No key entered", "Please enter a valid API key")
        return

    os.environ["OPENAI_API_KEY"] = token
    settings.openai_api_key = token

    settings.file_label_ai_types = bool(dialog.get_value("file_label_ai_types"))
    settings.file_label_ai_genres = bool(dialog.get_value("file_label_ai_genres"))
    settings.file_label_ai_objects = bool(dialog.get_value("file_label_ai_objects"))

    settings.file_label_ai_objects_min = int(str(dialog.get_value("file_label_ai_objects_min")))
    settings.file_label_ai_objects_max = int(str(dialog.get_value("file_label_ai_objects_max")))

    settings.folder_use_ai_engines = bool(dialog.get_value("folder_use_ai_engines"))
    settings.folder_use_ai_types = bool(dialog.get_value("folder_use_ai_types"))
    settings.folder_use_ai_genres = bool(dialog.get_value("folder_use_ai_genres"))

    settings.debug_log = bool(dialog.get_value("debug_log"))

    settings.store()
    ap.UI().show_success("Settings Updated", "The API key has been stored in your system environment")
    dialog.close()


def main():
    # Create a dialog container
    dialog = ap.Dialog()
    dialog.title = "AI Tagging Settings"
    ctx = ap.get_context()
    if ctx.icon:
        dialog.icon = ctx.icon

    dialog.add_text("<b>OpenAI API Key</b>")

    try:
        token = settings.openai_api_key
    except KeyError:
        token = ""

    dialog.add_input(token, var="token", width=400, placeholder="sk-proj-45jdh5k3kjdh5k3jh54kjh3...", password=True)
    dialog.add_info(
        "An API key is an identifier (similar to username and password), that<br>allows you to access the AI-cloud services from OpenAI. Create an<br>API key on <a href='https://platform.openai.com/settings/organization/api-keys'>the Open AI website</a>. You will need to set up billing first.")

    dialog.start_section("File Settings", folded=False)
    dialog.add_checkbox(settings.file_label_ai_types, var="file_label_ai_types",text="Label Types")
    dialog.add_info("e.g. model, texture, sfx")
    dialog.add_checkbox(settings.file_label_ai_genres, var="file_label_ai_genres",text="Label Genres")
    dialog.add_info("e.g. casual, cyberpunk, steampunk")
    (
        dialog.add_checkbox(settings.file_label_ai_objects, var="file_label_ai_objects",text="Label Objects\t")
        .add_text("Count:")
        .add_input(str(settings.file_label_ai_objects_min), var="file_label_ai_objects_min", width=50)
        .add_text("-")
        .add_input(str(settings.file_label_ai_objects_max), var="file_label_ai_objects_max", width=50)
    )
    dialog.add_info("What's in the picture. For example, an axe, a car, a character")
    dialog.add_separator()
    dialog.end_section()

    dialog.start_section("Folder Settings", folded=False)
    dialog.add_info("This will check the content of the folder, including all subfolders")
    dialog.add_checkbox(settings.folder_use_ai_engines, var="folder_use_ai_engines",text="Label Engines")
    dialog.add_info("e.g. Unity, Unreal, Godot")
    dialog.add_checkbox(settings.folder_use_ai_types, var="folder_use_ai_types",text="Label Types")
    dialog.add_info("e.g. model, texture, sfx")
    dialog.add_checkbox(settings.folder_use_ai_genres, var="folder_use_ai_genres",text="Label Genres")
    dialog.add_info("e.g. casual, cyberpunk, steampunk")
    dialog.add_separator()
    dialog.end_section()

    dialog.start_section("Debugging", folded=True)
    dialog.add_checkbox(settings.debug_log, var="debug_log",text="Enable Extended Logging")
    dialog.add_info("Log additional information to the console (open with CTRL+SHIFT+P)")
    dialog.end_section()


    dialog.add_info("Monitor your <a href='https://platform.openai.com/settings/organization/api-keys'>API keys</a> and <a href='https://platform.openai.com/settings/organization/usage'>current spending</a> on the OpenAI website. This<br> Action was created by <b>Hermesis Trismegistus</b>.If you like it, feel free to<br><a href='https://ko-fi.com/hermesistrismegistus'>make a donation.</a>")

    dialog.add_button("Apply", callback=apply_callback)

    dialog.show()


if __name__ == "__main__":
    main()
