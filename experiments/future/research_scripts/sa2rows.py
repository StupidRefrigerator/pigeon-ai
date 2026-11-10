import sys, openpyxl
wb = openpyxl.load_workbook(sys.argv[1], read_only=True, data_only=True)
names = sys.argv[2:]
for sh in ["Total population", wb.sheetnames[-1]]:
    ws = wb[sh]; rows = list(ws.iter_rows(values_only=True))
    hdr = rows[6]; print("SHEET", sh, [h for h in hdr if h is not None][:30])
    for r in rows:
        if r and r[0] in names:
            d = dict(zip(hdr, r)); print(r[0], {k: d.get(k) for k in hdr if str(k) in ("2021","2026","2031","2036","2041") or (isinstance(k,str) and k!='SA2')})
