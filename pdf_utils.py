import re
import pdfplumber


def extract_text_from_pdf(pdf_file):
    text_content = ""
    pdf_file.seek(0)
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text_content += (page.extract_text() or "") + "\n"
    return text_content.strip()


def extract_services_from_pdf(pdf_file):
    results = []
    pdf_file.seek(0)
    pattern = r"[a-zA-Z0-9\-\.]+\.azurecr\.io\/([a-zA-Z0-9\-]+):([a-zA-Z0-9_\.\-]+)"

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table or []:
                    for cell in row or []:
                        if not cell:
                            continue
                        for service, tag in re.findall(pattern, str(cell)):
                            results.append({
                                "Select": True,
                                "Service": service,
                                "Image Tag": tag,
                                "vendorImage": f"{service}:{tag}",
                                "Extraction Method": "Rule-Based",
                            })

    unique = []
    seen = set()
    for item in results:
        if item["vendorImage"] not in seen:
            seen.add(item["vendorImage"])
            unique.append(item)
    return unique
