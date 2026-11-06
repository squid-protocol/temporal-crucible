"""Fetch OSS-Fuzz daily per-file coverage summaries (public GCS) for one project, resumably."""
import json, sys, time, urllib.request, pathlib
proj = sys.argv[1]
d = pathlib.Path(proj); dates = json.load(open(d / "dates.json"))
for i, day in enumerate(dates):
    out = d / f"{day}.json"
    if out.exists() and out.stat().st_size > 0:
        continue
    url = f"https://storage.googleapis.com/oss-fuzz-coverage/{proj}/reports/{day}/linux/summary.json"
    try:
        data = urllib.request.urlopen(url, timeout=60).read()
        tmp = out.with_suffix(".tmp"); tmp.write_bytes(data); tmp.rename(out)
    except Exception as e:
        (d / f"{day}.missing").write_text(str(e))
    if i % 100 == 0:
        print(i, day, flush=True)
    time.sleep(0.2)
print("DONE", flush=True)
