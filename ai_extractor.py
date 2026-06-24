import os
import json
from openai import OpenAI

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def get_client():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise Exception("AI API key is missing")
    return OpenAI(api_key=key)


def extract_json_from_ai_response(content):
    content = content.strip()
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No valid JSON object found in AI response")
    return json.loads(content[start:end + 1])


def ai_extract_code_pull_details(document_text):
    client = get_client()
    prompt = f"""
Extract code-pull pipeline details from this release document.
Return only valid JSON with these fields:
application_name, project_name, release_version, source_branch,
azure_commit_id, target_environment, change_type, confidence, notes.

Document:
{document_text}
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        messages=[
            {"role": "system", "content": "You extract structured data from release documents."},
            {"role": "user", "content": prompt}
        ]
    )
    return extract_json_from_ai_response(response.choices[0].message.content)


def ai_extract_services_from_text(document_text):
    client = get_client()
    prompt = f"""
Extract deployment container image details from this document.
Return only valid JSON in format:
{{"services":[{{"service_display_name":"","service":"","image_registry":"","image_tag":"","vendorImage":""}}]}}
Rules: vendorImage must be service:image_tag and must not include registry.

Document:
{document_text}
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        messages=[
            {"role": "system", "content": "You extract deployment image data from release documents."},
            {"role": "user", "content": prompt}
        ]
    )
    data = extract_json_from_ai_response(response.choices[0].message.content)
    rows = []
    seen = set()
    for item in data.get("services", []):
        service = str(item.get("service", "")).strip()
        tag = str(item.get("image_tag", "")).strip()
        vendor = str(item.get("vendorImage", "")).strip() or f"{service}:{tag}"
        if service and tag and vendor not in seen:
            seen.add(vendor)
            rows.append({"Select": True, "Service": service, "Image Tag": tag, "vendorImage": vendor, "Extraction Method": "AI-Agent"})
    return rows
