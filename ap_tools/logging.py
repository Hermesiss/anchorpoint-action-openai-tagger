from package_settings import TaggerSettings

settings = TaggerSettings()
verbose = settings.debug_log

def log(data, important=False):
    if verbose or important:
        print(data)