import os

# if the same file is found in multiple paths, the first one will be used
def find_file(name, paths):
    for p in paths:
        f = os.path.join(p, name)
        if os.path.isfile(f):
            return f
    return None
