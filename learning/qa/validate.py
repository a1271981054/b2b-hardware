from pathlib import Path
import json, hashlib, re, subprocess, concurrent.futures
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'data.js').read_text()[12:].rstrip(';\n'))
manifest=json.loads((root/'manifest.json').read_text())
issues=[]
order={t['id']:i for i,t in enumerate(data['topics'])}
assert all(order[p]<order[t['id']] for t in data['topics'] for p in t['pre']), 'Prerequisite order'
assert all(len(t['chapters'][0]['text'])>=900 for t in data['topics'])
assert all(t['chapters'][0]['kind']=='主课' and len(t['chapters'][0]['checks'])>=3 for t in data['topics'])
assert all(len(re.findall(r'^### ',t['chapters'][0]['text'],re.M))>=7 for t in data['topics'])
assert '这张表里的关系' not in (root/'data.js').read_text()
assert 'function svg(' not in (root/'diagrams.js').read_text()
assert not re.search(r'data-nav="(?:library|listen)"',(root/'index.html').read_text())
assert len(data['topics'])==60 and len(data['documents'])==39
assert sum(len(t[k]['options'])>1 for t in data['topics'] for k in ['quiz','scenario'])==120
for d in data['documents']:
 p=root/d['download']; assert p.exists()
 assert hashlib.sha256(p.read_bytes()).hexdigest()==d['hash'],d['id']
 assert d['text']==p.read_text(),d['id']
for t in data['topics']:
 assert len(t['cards'])==3 and all(isinstance(s,str) and s.strip() for s in t['cards']),t['id']
 assert all(s['doc'] in [d['id'] for d in data['documents']] for s in t['sources'])
 for k in ('scenario','quiz'):
  q=t[k];assert 0<=q['answer']<len(q['options']) and len(q['feedback'])>10,t['id']
for key in ['index.html','style.css','reading.css','app.js','widgets.js','diagrams.js','journey.js','data.js']:
 assert (root/key).exists()
assert re.search(r'href="reading\.css(?:\?[^"]*)?"', (root/'index.html').read_text())
for t in data['topics']:
 assert t['chapters']
 for c in t['chapters']:
  assert len(c['figures'])>=2 and all(len(f['nodes'])>=2 for f in c['figures'])
  for f in c['figures']:
   image=root/f['src']
   assert image.is_file() and image.stat().st_size>2000,f['src']
   assert image.suffix=='.webp',f['src']
  assert all(k in data['references'] for k in c['external'])
  if not c['doc']:continue
  doc=next(d for d in data['documents'] if d['id']==c['doc'])
  expected='\n'.join(doc['text'].splitlines()[c['startLine']-1:c['endLine']]).strip()
  assert c['text']==expected,(t['id'],c['id'])
for coverage in manifest['coreCoverage']:
 assert not coverage['missingLines'] and coverage['coveredLines']==coverage['nonemptyLines']
allhtml=(root/'index.html').read_text()+''.join(d['html'] for d in data['documents'])+''.join(s['html'] for t in data['topics'] for s in t['sources'])
for url in re.findall(r'(?:src|href)="([^"]+)"',allhtml):
 if url.startswith(('http://','https://','mailto:','#','data:')):continue
 assert (root/url.split('#')[0].split('?')[0]).exists(),url
paths=set()
for m in data['media']:
 for k in ('audio','video'):
  if k in m:paths.add(m[k]);assert (root/m[k]).is_file()
def probe(path):
 p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,codec_name,width,height','-of','json',str(root/path)],capture_output=True,text=True)
 assert p.returncode==0,(path,p.stderr)
 obj=json.loads(p.stdout);assert float(obj['format']['duration'])>0
 return dict(path=path,duration=round(float(obj['format']['duration']),2),streams=obj['streams'])
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:probes=list(pool.map(probe,sorted(paths)))
image_paths=sorted({f['src'] for t in data['topics'] for c in t['chapters'] for f in c['figures']})
assert len(image_paths)==120
assert len({hashlib.sha256((root/p).read_bytes()).hexdigest() for p in image_paths})==120
artwork=json.loads((root/'artwork/manifest.json').read_text())
assert len(artwork)==120 and all(j['status']=='complete' for j in artwork)
assert {j['webPath'] for j in artwork}==set(image_paths)
visual_review=json.loads((root/'qa/art-review.json').read_text())
assert set(visual_review['reviewed'])=={j['id'] for j in artwork}
assert all(i['status']=='repaired-and-reviewed' for i in visual_review['issues'])
report={'source_integrity':'39 / 39 exact matches','topics':len(data['topics']),'unique_generated_images':len(image_paths),'learning_figures':sum(len(c['figures']) for t in data['topics'] for c in t['chapters']),'core_lesson_chars':{'min':min(t['chapters'][0]['chars'] for t in data['topics']),'max':max(t['chapters'][0]['chars'] for t in data['topics'])},'total_course_chars':sum(t['readingChars'] for t in data['topics']),'knowledge_cards':len(data['topics'])*3,'course_chapters':sum(len(t['chapters']) for t in data['topics']),'core_document_coverage':manifest['coreCoverage'],'questions':len(data['topics'])*2,'glossary_terms':len(data['terms']),'widget_types':sorted({t['widget'] for t in data['topics'] if t.get('widget')}),'linked_assets':'All local source/HTML/media links exist','media_probes':probes,'bundle_megabytes':round(sum(p.stat().st_size for p in root.rglob('*') if p.is_file())/1048576,2)}
(root/'qa/static-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='media_probes'},ensure_ascii=False));print('Media checked:',len(probes))
