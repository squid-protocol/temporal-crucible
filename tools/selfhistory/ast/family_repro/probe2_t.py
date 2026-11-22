import re, json, subprocess, os
PAT = re.compile("a+")

def uses_module_pattern(s):
    return [m.group(0) for m in PAT.finditer(s)]

def uses_fullmatch(s):
    return PAT.fullmatch(s)

def runner():
    subprocess.run(["ls"])

def evaler(s):
    return eval(s)

def jsoner(s):
    return json.loads(s)

def env_reader():
    return os.environ.get("X")

def gen_only(xs):
    return (x for x in xs)
