from common.settings import tagger_settings


def log(data):
    verbose = tagger_settings.debug_log
    if verbose:
        print(data)


def log_err(data):
    print(data)
