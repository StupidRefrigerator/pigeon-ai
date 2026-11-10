import sys, pypdf
r = pypdf.PdfReader(sys.argv[1])
with open(sys.argv[2], "w") as f:
    for i, p in enumerate(r.pages, 1):
        f.write(f"\n=====PAGE {i}=====\n")
        f.write(p.extract_text() or "")
