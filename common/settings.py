import apsync as aps

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

tagger_settings = TaggerSettings()
