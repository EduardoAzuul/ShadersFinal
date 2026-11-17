import json,re,glob,sys
want=sys.argv[1].split(',')
files=glob.glob('**/*.shadergraph',recursive=True)+glob.glob('**/*.shadersubgraph',recursive=True)
found={}
for f in files:
    try:
        t=open(f,encoding='utf-8-sig').read()
        objs=[json.loads(x) for x in re.split(r'\n\n(?=\{)',t.strip())]
    except Exception as e: continue
    byid={o.get('m_ObjectId'):o for o in objs}
    if None in byid: continue
    for o in objs:
        short=o['m_Type'].split('.')[-1]
        if short in want and short not in found:
            slots=[byid[s['m_Id']] for s in o.get('m_Slots',[])]
            found[short]=(f,o,slots)
for w in want:
    print('#####',w, found.get(w,[None])[0])
json.dump(found,open(sys.argv[2],'w'),indent=1)
