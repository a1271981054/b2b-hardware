"""Assign complete source passages to lessons; retain line-level coverage evidence."""
import re

def build_details(topics, docs, catalog, core, render):
 by_id={t['id']:t for t in topics}; covered={k:set() for k in core}
 lines={k:catalog[v]['text'].splitlines() for k,v in core.items()}
 spans={t['id']:[] for t in topics}
 def add(topic,key,start,end):
  spans[topic].append((key,start,end));covered[key].update(range(start,end))
 for t in topics:
  for key,needle in t['refs']:
   ls=lines[key];start=next(i for i,l in enumerate(ls) if re.match(r'^#{1,6} ',l) and needle in l)
   level=len(ls[start])-len(ls[start].lstrip('#'))
   end=next((i for i in range(start+1,len(ls)) if re.match(r'^#{1,'+str(level)+r'} ',ls[i])),len(ls))
   add(t['id'],key,start,end)
 # Full applied examples accompany the frameworks, rather than remaining in the archive.
 extra={
 'questions': [('Q1 追问 7.','value'),('Q1 追问 11.','buyers')],
 'gateway':[('0. 一页纸','gateway'),('3.1','jtbd'),('3.2','value'),('3.3','buyers'),('3.4','opportunity'),('4. 第二问','industry'),('5. 第三问','model'),('8.1','spec'),('8.4','cert'),('8.5','stages'),('11. 数据来源','gateway')],
 'quality':[('0. 使用说明','control'),('1. 一页总览','control'),('10. 面试前','answer'),('11. 小练习','nfc-case'),('12. 后续学习','answer')],
 'notes':[('附录：术语','role'),('附录二：面试','answer'),('第 6 课：串成','answer')],
 'acs':[('公司一句话','acs'),('第 1 页','acs'),('第 2 页','buyers'),('第 3 页','acs'),('面试表达','answer'),('可引用','acs')]
 }
 for key,items in extra.items():
  for needle,tid in items:
   ls=lines[key];start=next(i for i,l in enumerate(ls) if re.match(r'^#{1,6} ',l) and needle in l)
   level=len(ls[start])-len(ls[start].lstrip('#'))
   end=next((i for i in range(start+1,len(ls)) if re.match(r'^#{1,'+str(level)+r'} ',ls[i])),len(ls))
   add(tid,key,start,end)
 # Retain introductions, pending questions and study routes as actual lesson sections.
 fallback={'notes':'answer','questions':'role','gateway':'gateway','quality':'answer','acs':'acs'}
 for key,ls in lines.items():
  pending=[i for i in range(len(ls)) if i not in covered[key]]
  runs=[]
  for i in pending:
   if not runs or i!=runs[-1][-1]+1:runs.append([i])
   else:runs[-1].append(i)
  for run in runs:
   if any(ls[i].strip() and ls[i].strip()!='---' for i in run):add(fallback[key],key,run[0],run[-1]+1)
 for t in topics:
  t['chapters']=[];seen=set()
  for key,start,end in spans[t['id']]:
   ls=lines[key]
   # Remove overlaps within a lesson; split long passages at internal headings.
   indices=[i for i in range(start,end) if (key,i) not in seen]
   runs=[]
   for i in indices:
    if not runs or i!=runs[-1][-1]+1:runs.append([i])
    else:runs[-1].append(i)
   for run in runs:
    a,b=run[0],run[-1]+1
    cuts=[a]
    for i in range(a+1,b):
     if re.match(r'^#{2,4} ',ls[i]) and sum(len(x) for x in ls[cuts[-1]:i])>850:cuts.append(i)
    cuts.append(b)
    for x,y in zip(cuts,cuts[1:]):
     text='\n'.join(ls[x:y]).strip()
     if not text or not re.search(r'[\w\u4e00-\u9fff]',text):continue
     heading=next((re.sub(r'^#+\s*','',l) for l in ls[x:y] if re.match(r'^#{1,6} ',l)),None)
     if not heading:
      heading=next((re.sub(r'^#+\s*','',ls[i])+'（续）' for i in range(x-1,-1,-1) if re.match(r'^#{1,6} ',ls[i])),'学习约定')
     # Heading is rendered explicitly; renderer skips a leading H1 only.
     body,_=render(text,docs[core[key]].path)
     chapter={'id':f'{t["id"]}-{len(t["chapters"])+1}','title':re.sub(r'^(?:Q1(?: 追问(?: \d+)?)?\.\s*|第\s*\d+\s*[课页]：|\d+(?:\.\d+)*[.、]?\s+)', '', heading),'doc':catalog[core[key]]['id'],'html':body,'text':text,'startLine':x+1,'endLine':y,'chars':len(text)}
     t['chapters'].append(chapter);seen.update((key,i) for i in range(x,y))
  t['readingChars']=sum(c['chars'] for c in t['chapters'])
  if t['refs']:assert t['chapters'],t['id']
 report=[]
 for key,ls in lines.items():
  substantive={i for i,l in enumerate(ls) if l.strip() and l.strip()!='---'}
  actual={i for t in topics for c in t['chapters'] if c['doc']==catalog[core[key]]['id'] for i in range(c['startLine']-1,c['endLine'])}
  missing=sorted(substantive-actual)
  assert not missing,(key,missing)
  report.append({'document':catalog[core[key]]['title'],'nonemptyLines':len(substantive),'coveredLines':len(substantive&actual),'missingLines':missing})
 return report
