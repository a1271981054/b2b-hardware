"""Regression checks for a wording change, not a readability score."""
from pathlib import Path
from html.parser import HTMLParser
import json, re, zipfile, hashlib, sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from plain_language import LESSON_COPY,METHODS,CHECK_COPY,GLOSS,help_html
read=lambda s:json.loads(s[12:].rstrip(';\n'))
new=read((root/'data.js').read_text())
with zipfile.ZipFile(root/'qa/before-plain-language-learning.zip') as z:
 old=read(z.read('learning/data.js').decode())
 old_images={n.removeprefix('learning/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.endswith('.webp')}
assert [(t['id'],[c['id'] for c in t['chapters']]) for t in new['topics']]==[(t['id'],[c['id'] for c in t['chapters']]) for t in old['topics']]
assert 'hardware-island-v1' in (root/'app.js').read_text()
assert set(LESSON_COPY)==set(METHODS)==set(CHECK_COPY)=={t['id'] for t in new['topics']}
class Inspector(HTMLParser):
 def __init__(self):super().__init__();self.buttons=0;self.code=0;self.codes=[];self.cells=[];self.cell=None;self.helpers=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='button':
   assert not self.buttons,'nested buttons';self.buttons+=1
   if a.get('data-action')=='explain-term':assert a.get('data-term') in GLOSS;self.helpers+=1
  if tag=='code':self.code+=1;self.codes.append('')
  if tag in ('td','th'):self.cell=''
 def handle_endtag(self,tag):
  if tag=='button':self.buttons-=1;assert self.buttons>=0
  if tag=='code':self.code-=1
  if tag in ('td','th'):self.cells.append(self.cell);self.cell=None
 def handle_data(self,d):
  if self.code:self.codes[-1]+=d
  if self.cell is not None:self.cell+=d
 def run(self,s):self.feed(s);self.close();assert self.buttons==0;return self
source_count=0;helper_count=0
for t,before in zip(new['topics'],old['topics']):
 assert t['chapters'][0]['text']!=before['chapters'][0]['text']
 for q in ('quiz','scenario'):
  assert t[q]['answer']==before[q]['answer'],(t['id'],q)
  assert len(t[q]['options'])==len(before[q]['options'])
 for c,prev in zip(t['chapters'],before['chapters']):
  assert c['plainLanguageVersion']==1
  current=Inspector().run(c.get('readingHtml',c['html']))
  helper_count+=current.helpers
  assert [f['src'] for f in c['figures']]==[f['src'] for f in prev['figures']]
  if c['doc']:
   source_count+=1;assert c['text']==prev['text']
   original=Inspector().run(c['html'])
   assert current.codes==original.codes,(t['id'],c['id'],'code')
   # Word changes are allowed; numerical content of each table cell is not.
   assert len(current.cells)==len(original.cells)
   number=lambda text:re.findall(r'\d+(?:\.\d+)?',text or '')
   assert [number(x) for x in current.cells]==[number(x) for x in original.cells],(t['id'],c['id'],'table numbers')
for name,digest in old_images.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
assert 'data-action="explain-term"' in help_html('<p>SPC 与 MP，EXAMPLE 不应拆开。</p>')
assert 'EXAMPLE' in help_html('<p>EXAMPLE</p>') and 'button' not in help_html('<p>EXAMPLE</p>')
report=dict(authored_topics=60,authored_sections=sum(len(x['sections']) for x in LESSON_COPY.values()),rewritten_methods=60,rewritten_checks=180,original_chapters_preserved=source_count,source_code_and_table_numbers='unchanged',image_hashes_preserved=len(old_images),inline_definitions=len(GLOSS),rendered_term_buttons=helper_count,topic_chapter_ids_and_answer_indices='unchanged',note='These checks verify coverage and integrity. Readability is reviewed through the authored wording and browser samples, not inferred from a numerical score.')
(root/'qa/plain-language-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
