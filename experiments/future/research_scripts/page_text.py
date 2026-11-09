import sys, re, pypdf
r = pypdf.PdfReader(sys.argv[1])
for n in sys.argv[2:]:
    t = re.sub(r"\s+", " ", r.pages[int(n)-1].extract_text() or "")
    print(f"=== p{n} ===\n{t[:3000]}\n")
