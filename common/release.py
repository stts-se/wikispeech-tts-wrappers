import datetime
import pytz
from pytz import timezone
import sys
import subprocess

from . import log

def versionInfo(name: str, startedAt: str):
    res = []

    # for pre-packaged releases (container type)
    # buildInfoFile = f"/wikispeech/{name}/build_info.txt"
    # if os.path.isfile(buildInfoFile):
    #     with open(buildInfoFile) as fp:  
    #         lines = fp.readlines()
    #         fp.close()
    #         for l in lines:
    #             res.append(l.strip())
    # else:

    res.append(f"Application name: {name}")
    # res.append("Build timestamp: n/a")
    # res.append("Built by: user")
    
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode("utf-8").strip()
        log.info(f"git branch {branch}")
        log.info(f"git commit {commit}")
        commit = commit[0:7]
        res.append( ("Commit %s on branch %s") % (commit, branch) )
        try:
            tag = subprocess.check_output(["git","describe","--tags"]).decode("utf-8").strip()
            log.info(f"git tag {tag}")
            res.append( ("Release %s on branch %s") % (tag, branch) )
        except: 
            log.warning("couldn't retrieve git tags: %s" % sys.exc_info()[1])
            #commit = commit[0:7]
            #res.append( ("Commit %s on branch %s") % (commit, branch) )
    except:
        log.warning("couldn't retrieve git release info: %s" % sys.exc_info()[1])
        res.append("Release: unknown");

    res.append("Started: " + startedAt)
    for l in res:
        log.info(f"LOGGING VERSION INFO {l}")
    return res


def genStartedAtString():
    try:
        from time import strftime, gmtime
        from tzlocal import get_localzone
        local_tz = get_localzone()
        now = datetime.datetime.now()
        if local_tz != None:
            now = now.replace(tzinfo=local_tz)
            #now = now.astimezone(pytz.utc)
        return '{:%Y-%m-%d %H:%M:%S %Z}'.format(now)
    except Exception as e:
        log.info(f"Couldn't retrieve start time: {e}")
        return "unknown"
