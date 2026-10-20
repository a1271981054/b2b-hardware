"""Collect native-generation provenance and delivery hashes; fail on any gap."""
from pathlib import Path
import json,hashlib,struct
root=Path(__file__).resolve().parents[1]
manifest=root/'artwork/manifest.json'
jobs=json.loads(manifest.read_text())
missing=[]
for j in jobs:
 result=root/'artwork/results'/f"{j['id']}.json"
 if result.exists():j.update(json.loads(result.read_text()))
 original=root/j['path'];webp=original.with_suffix('.webp')
 if not original.exists() or not webp.exists():
  missing.append(j['id']);continue
 raw=original.read_bytes()
 assert raw[:8]==b'\x89PNG\r\n\x1a\n',original
 width,height=struct.unpack('>II',raw[16:24])
 assert width>=1024 and height>=1024,(original,width,height)
 j.update(status='complete',webPath=webp.relative_to(root).as_posix(),
  width=width,height=height,originalBytes=len(raw),webBytes=webp.stat().st_size,
  originalSHA256=hashlib.sha256(raw).hexdigest(),webSHA256=hashlib.sha256(webp.read_bytes()).hexdigest(),
  promptFile='artwork/prompts/'+j['id']+'.txt')
manifest.write_text(json.dumps(jobs,ensure_ascii=False,indent=2))
if missing:raise SystemExit('Artwork incomplete: '+', '.join(missing))
assert len(jobs)==120
assert len({j['originalSHA256'] for j in jobs})==120
print(json.dumps({'images':len(jobs),'originalMB':round(sum(j['originalBytes'] for j in jobs)/1048576,2),'webMB':round(sum(j['webBytes'] for j in jobs)/1048576,2)},ensure_ascii=False))
