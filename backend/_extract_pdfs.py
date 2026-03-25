import pdfplumber

files = [
    "docs/E-mails de prospecção1.pdf",
    "docs/E-mails de prospecção - métodos 2.pdf",
    "docs/Abordagens no LinkedIn.pdf",
]

out = open("_pdf_output.txt", "w", encoding="utf-8")

for f in files:
    sep = "=" * 80
    out.write(f"\n{sep}\n")
    out.write(f"ARQUIVO: {f}\n")
    out.write(f"{sep}\n")
    with pdfplumber.open(f) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                out.write(f"\n--- Página {i+1} ---\n")
                out.write(text + "\n")

out.close()
print("Done")
