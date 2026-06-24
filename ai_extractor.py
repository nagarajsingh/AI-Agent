import os
import json
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def get_openai_client():
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY environment variable is missing")
    return OpenAI(api_key=OPENAI_API_KEY)


def extract_json_from_ai_response(content):
    content = content.strip()
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No valid JSON object found in AI response")
    return json.loads(content[start:end + 1])


def ai_extract_services_from_text(document_text):
    client = get_openai_client()
    prompt = f"""
Extract deployment container image details from this release document.
Return only valid JSON with this shape:
{{"services":[{{"service_display_name":"","service":"","image_registry":"","image_tag":"","vendorImage":""}}]}}
Rules:
- service is the image name only.
- image_registry is the registry only.
- image_tag is the tag only.
- vendorImage must be service:image_tag and must not include registry.
- If a common version tag exists and image tag is missing, apply the common tag.
- If no services are found, return {{"services":[]}}.
Document:
{document_text}
"""
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": "Extract structured deployment data from documents."},
            {"role": "user", "content": prompt},
        ],
    )
    ai_json = extract_json_from_ai_response(response.choices[0].message.content)
    rows = []
    seen = set()
    for item in ai_json.get("services", []):
        service = str(item.get("service", "")).strip()
        image_tag = str(item.get("image_tag", "")).strip()
        vendor_image = str(item.get("vendorImage", "")).strip()
        if not vendor_image and service and image_tag:
            vendor_image = f"{service}:{image_tag}"
        if service and image_tag and vendor_image and vendor_image not in seen:
            seen.add(vendor_image)
            rows.append({
                "Select": True,
                "Service": service,
                "Image Tag": image_tag,
                "vendorImage": vendor_image,
                "Extraction Method": "AI-Agent",
            })
    return rows


def ai_extract_code_pull_details(document_text):
    client = get_openai_client()
    prompt = f"""
Extract code-pull pipeline details from this release document.
Return only valid JSON with this shape:
{{"application_name":"","project_name":"","release_version":"","source_branch":"","azure_commit_id":"","target_environment":"","change_type":"","confidence":"","notes":[]}}
Rules:
- application_name should come from deployment service/application information.
- project_name should come from project details.
- release_version should come from document version or release version.
- source_branch should come from deployment steps or sync instructions.
- azure_commit_id should be a 40-character commit SHA if present.
- target_environment should be deployment target environment if present.
- confidence is high, medium, or low.
- notes should list missing or inferred fields.
Document:
{document_text}
"""
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": "Extract code-pull pipeline parameters from release documents."},
            {"role": "user", "content": prompt},
        ],
    )
    return extract_json_from_ai_response(response.choices[0].message.content)
