import re, time, json, subprocess, sys, os
from pathlib import Path

class K:
    @staticmethod
    def deco():
        return 1

    @property
    def prop(self):
        return 2

def sleeper():
    time.sleep(1)

def exiter():
    sys.exit(2)

def runner():
    subprocess.run(["ls"])

def evaler(s):
    return eval(s)

def jsoner(s):
    return json.loads(s)

def timer():
    return time.perf_counter()

def finder(p):
    pat = re.compile("a")
    return [m for m in pat.finditer(p)]

def pather(p):
    return Path(p).read_text()

def ospath(a, b):
    return os.path.join(a, b)

def bits(s):
    return re.compile(r"^a|~b<<")
