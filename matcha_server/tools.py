import os
from pathlib import Path

logger = None
def get_logger(name="matcha"):
    global logger
    if logger is not None:
        return logger
    import logging
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logger = logging.getLogger(name)
    logging.getLogger(name).setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    return logger
    
# if the same model/file is found in multiple paths, the first one will be used
def find_file(name, paths):
    for p in paths:
        f = os.path.join(p, name)
        if os.path.isfile(f):
            return f
    return None

def create_path(p,create=True):
    p = os.path.expandvars(p)
    if create:
        folder = Path(p)
        folder.mkdir(exist_ok=True, parents=True)
        #logger.debug(f"Created directory: {p}")
    if not os.path.isdir(p):
        raise IOError(f"Couldn't create output folder: {p}")
    return p


def clear_audio(audio_path):
    get_logger().info(f"Clearing audio set to true")
    n=0
    for fn in os.listdir(audio_path):
        file_path = os.path.join(audio_path, fn)
        if os.path.isfile(file_path):
            os.remove(file_path)
            n+=1
            #print(fn, "is removed")
    get_logger().debug(f"Deleted {n} files from folder {audio_path}")
   
def get_or_else(value1, value2, default=None):
    if value1 is not None:
        return value1
    elif value2 is not None:
        return value2
    else:
        return default
