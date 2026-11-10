import sys, re, pypdf
path, pat = sys.argv[1], re.compile(sys.argv[2], re.I)
ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 150
r = pypdf.PdfReader(path)
for i, p in enumerate(r.pages, 1):
    try: t = p.extract_text() or ""
    except Exception: continue
    t = re.sub(r"\s+", " ", t)
    for m in pat.finditer(t):
        print(f"[p{i}] ...{t[max(0,m.start()-ctx):m.end()+ctx]}...")
