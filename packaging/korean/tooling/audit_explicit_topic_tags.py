"""Audit every explicit topic tag against original INFO/topic identities.

Source text is read locally; no original game assets are published. Categories
are review evidence, not a claim that every flagged hyperlink is incorrect.
"""
import argparse,json,re,hashlib
from pathlib import Path
from collections import defaultdict,Counter
from audit_topic_collisions import records,fields,decode

def identity(items):
    # INFO IDs can be reused in different topics. Match speaker/faction/quest
    # conditions too, never assume INAM alone globally identifies one response.
    h=hashlib.sha256()
    for tag,value in items:
        if tag not in (b'NAME',b'PNAM',b'NNAM',b'BNAM'):
            h.update(tag);h.update(len(value).to_bytes(4,'little'));h.update(value)
    return h.hexdigest()

def scan(esp,masters):
    original=defaultdict(list);source_parent=None;kind=None
    for path in masters:
        for tag,body in records(path.read_bytes()):
            items=list(fields(body));f=dict(items)
            if tag==b'DIAL':
                source_parent=f.get(b'NAME',b'').rstrip(b'\0').decode('cp1252');kind=f.get(b'DATA',b'\xff')[0]
            elif tag==b'INFO' and b'INAM' in f:
                iid=f[b'INAM'].rstrip(b'\0').decode('ascii')
                original[identity(items)].append({'INFO':iid,'parent':source_parent,'kind':kind,
                    'text':f.get(b'NAME',b'').rstrip(b'\0').decode('cp1252')})
    aliases={};duplicates=defaultdict(set)
    for line in esp.with_suffix('.top').read_text(encoding='utf-8-sig').splitlines():
        if '\t' in line:
            k,v=line.split('\t',1);aliases.setdefault(k,v);duplicates[k].add(v)
    topic_sources=defaultdict(set);entries=[];parent=None;kind=None;normal=set();anchors=Counter()
    for tag,body in records(esp.read_bytes()):
        items=list(fields(body));f=dict(items)
        if tag==b'DIAL':
            parent=decode(f.get(b'NAME',b''));kind=f.get(b'DATA',b'\xff')[0]
            if kind==0 and b'DELE' not in f:normal.add(parent)
        elif tag==b'INFO' and b'INAM' in f:
            iid=decode(f[b'INAM'])
            candidates=original.get(identity(items),[])
            if kind==4:candidates=[r for r in candidates if r['parent'].lower()==parent.lower()]
            unique_texts={r['text'] for r in candidates}
            source=next(iter(unique_texts)) if len(unique_texts)==1 else None
            anchors['unique']+=source is not None
            anchors['ambiguous']+=len(unique_texts)>1
            anchors['unmatched']+=not candidates
            if kind==0 and source is not None:
                topic_sources[parent].update(r['parent'] for r in candidates if r['kind']==0)
            if kind in (0,2,3,4) and b'NAME' in f:
                entries.append({'INFO':iid,'parent':parent,'kind':kind,'text':decode(f[b'NAME']),
                    'identity':identity(items),'original':source})
    english_patterns={}
    for target,names in topic_sources.items():
        english_patterns[target]=[(name,re.compile(r'(?<![A-Za-z0-9])'+re.escape(name)+r'(?:s|es)?(?![A-Za-z0-9])',re.I)) for name in names]
    findings=[];total=0;totals=Counter();by_target=Counter();seen_duplicate_tags=Counter()
    for entry in entries:
        text=entry['text'];source=entry['original']
        for match in re.finditer(r'@([^@#]*)#',text):
            total+=1;phrase=match[1];shown=phrase.rstrip('\x7f');key=shown+'*'*(len(phrase)-len(shown))
            target=aliases.get(key,key);categories=[];english=topic_sources.get(target,set())
            before=text[:match.start()];after=text[match.end():]
            if len(target)==1 and re.fullmatch('[가-힣]',target):categories.append('single_syllable_target')
            if before and re.fullmatch('[가-힣]',before[-1]):categories.append('explicit_inside_hangul_word')
            if (len(before)>=2 and before[-1] in '-·‐‑–—' and re.fullmatch('[가-힣]',before[-2])) or (len(after)>=2 and after[0] in '-·‐‑–—' and re.fullmatch('[가-힣]',after[1])):
                categories.append('explicit_compound_fragment')
            if target not in normal:categories.append('unresolved_target')
            if len(duplicates.get(key,()))>1:
                categories.append('first_wins_alias_collision');seen_duplicate_tags[key]+=1
            embedded=[]
            if source is not None and english:
                whole=any(pattern.search(source) for _,pattern in english_patterns[target])
                if not whole:
                    for name in english:
                        for m in re.finditer(re.escape(name),source,re.I):
                            embedded.append(source[max(0,m.start()-18):m.end()+18])
                    if embedded:categories.append('source_only_inside_English_word')
                    else:categories.append('no_original_topic_phrase')
            if categories:
                totals.update(categories);by_target[target]+=1
                findings.append({**entry,'tag':shown,'target':target,'categories':categories,
                    'context':text[max(0,match.start()-38):match.end()+42],
                    'English_topic_candidates':sorted(english),'original':source,
                    'embedded_English_examples':embedded[:4],'span':[match.start(),match.end()]})
    return {'INFO_count':len(entries),'explicit_tag_occurrences':total,'flagged_occurrences':len(findings),
      'category_counts':dict(totals),'top_flagged_targets':by_target.most_common(50),
      'source_identity_anchors':dict(anchors),
      'observed_duplicate_aliases':[{'alias':k,'targets':sorted(duplicates[k]),'occurrences':n} for k,n in seen_duplicate_tags.most_common()],
      'notes':'Flags require review. English word-embedding and homonyms are different failure mechanisms. Actual visibility also depends on topic knowledge.',
      'findings':findings}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--esp',type=Path,required=True)
    ap.add_argument('--master',type=Path,action='append',required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();r=scan(a.esp,a.master);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in r.items() if k not in ('findings','observed_duplicate_aliases')},ensure_ascii=False,indent=2))
