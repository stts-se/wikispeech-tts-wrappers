import sys
import syslog
import logging

default_handler = "python"
default_level = logging.WARNING

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
logging_level_map = {
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
    logging_level = logging_level_map[level]
    pylogger = logging.getLogger(name)
    logging.getLogger("name").setLevel(logging_level)
    #logging.basicConfig(level=logging_level, format='%(asctime)s - %(name)s:%(filename)s - %(levelname)s - %(message)s')
    logging.basicConfig(level=logging_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')        
    #if handler == "syslog":
    logging_level = syslog_level_map[level]
    

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
            print(f"{level.upper()} {msg}", file=sys.stderr)
        elif handler == "stdout":
            print(msg)
        elif handler == "python":
            logging_level = logging_level_map[level]
            pylogger.log(logging_level, msg)
        elif handler == "syslog":            
            syslog_level = syslog_level_map[level]        
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
