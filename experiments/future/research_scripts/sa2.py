import sys, openpyxl
wb = openpyxl.load_workbook(sys.argv[1], read_only=True, data_only=True)
pat = [s.lower() for s in sys.argv[2:]]
for ws in wb.worksheets:
    print("SHEET", ws.title)
    hdr = None
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        cells = ["" if c is None else str(c) for c in row]
        if i < 8 and any("2041" in c or "SA2" in c for c in cells): hdr = cells; print("HDR", i, cells[:20])
        line = " | ".join(cells).lower()
        if any(p in line for p in pat): print(i, cells[:20])
