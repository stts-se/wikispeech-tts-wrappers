import sys
import syslog
import logging

default_handler = "python"
default_level = "warning"

handler = default_handler
level = default_level

pylogger = None

syslog_level_map = {
    "fatal": syslog.LOG_CRIT,
    "error": syslog.LOG_ERR,
    "warning": syslog.LOG_WARNING,
    "info": syslog.LOG_INFO,
    "debug": syslog.LOG_DEBUG
}
pylog_level_map = {
    "fatal": logging.FATAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG
}

def configure(name, hdlr, lvl):
    print(f"Setting {name} logger to {hdlr} {lvl}", file=sys.stderr)
    global handler, level, pylogger
    handler = hdlr
    level = lvl
    #if handler == "python":
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    pylog_level = pylog_level_map[level]
    pylogger = logging.getLogger(name)
    logging.getLogger("name").setLevel(pylog_level)
    #logging.basicConfig(level=logging_level, format='%(asctime)s - %(name)s:%(filename)s - %(levelname)s - %(message)s')
    logging.basicConfig(level=pylog_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    

def log(lvl, msg):
    levels = ["debug", "info", "warning", "error", "fatal"]
    if lvl in levels:
        l = levels.index(lvl)
    else:
        raise ValueError("Level %s not in %s" % (lvl, levels))

    if level in levels:
        ll = levels.index(level)
    else:
        raise ValueError("Level %s not in %s" % (level, levels))

    if l >= ll:
        if handler == "stderr":
            print(f"{lvl.upper()} {msg}", file=sys.stderr)
        elif handler == "stdout":
            print(f"{lvl.upper()} {msg}")
        elif handler == "python":
            pylog_level = pylog_level_map[lvl]
            pylogger.log(pylog_level, msg)
        elif handler == "syslog":
            syslog_level = syslog_level_map[lvl]        
            syslog.syslog(syslog_level, msg)
        else:
            with open(handler,"a") as out:
                out.write(msg+"\n")
                

def debug(msg):
    log("debug",msg)

def info(msg):
    log("info",msg)

def warn(msg):
    log("warning",msg)
def warning(msg):
    log("warning",msg)

def error(msg):
    log("error", msg)

def fatal(msg):
    log("fatal", msg)
    sys.exit(1)


import os    
import threading
import time
import psutil

class MemoryLogger:

    def __init__(self, interval=60):
        self.interval = interval
        debug(f"Initializing memory logger with interal {interval}")
    
    def log_memory(self):
        process = psutil.Process(os.getpid())
        while True:
            mem = process.memory_info().rss / (1024 ** 3)  # GB
            debug(f"[MEM] {mem:.2f} GB")
            #mem = process.memory_info().rss / (1024 ** 2)
            #debug(f"[MEM] {mem:.2f} MB")
            time.sleep(self.interval)

    def start(self):
        threading.Thread(target=self.log_memory, daemon=True).start()
