from package_settings import TaggerSettings

settings = TaggerSettings()
verbose = settings.debug_log

def log(data):
    if verbose:
        print(data)

def log_err(data):
    print(data)