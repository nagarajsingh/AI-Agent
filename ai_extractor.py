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
        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

    json_start = content.find("{")
    json_end = content.rfind("}")

    if json_start == -1 or json_end == -1:
        raise ValueError("No valid JSON object found in AI response")

    return json.loads(content[json_start:json_end + 1])


def ai_extract_services_from_text(document_text):
    client = get_openai_client()

    prompt = f"""
You are an AI extraction agent for deployment release documents.

Extract all container image deployment details from the document text.

Return ONLY valid JSON. No markdown. No explanation.

Required JSON format:
{{
  "services": [
    {{
      "service_display_name": "",
      "service": "",
      "image_registry": "",
      "image_tag": "",
      "vendorImage": ""
    }}
  ]
}}

Rules:
1. Extract only container images related to deployment/release.
2. service must be image name only.
3. image_registry must be registry only.
4. image_tag must be tag only.
5. vendorImage must be service:image_tag.
6. vendorImage must not include registry.
7. If a common Version Tag is mentioned and images do not show full tag, apply that version tag.
8. If no services are found, return {{"services": []}}.

Document text:
{document_text}
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You extract structured deployment image data from unstructured release documents."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
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
                "Extraction Method": "AI-Agent"
            })

    return rows


def ai_extract_code_pull_details(document_text):
    client = get_openai_client()

    prompt = f"""
You are an AI extraction agent for bank release documents.

Extract details required to trigger a code-pull pipeline.

Return ONLY valid JSON. No markdown. No explanation.

Required JSON format:
{{
  "application_name": "",
  "project_name": "",
  "release_version": "",
  "source_branch": "",
  "azure_commit_id": "",
  "target_environment": "",
  "change_type": "",
  "confidence": "",
  "notes": []
}}

Rules:
1. application_name:
   - Prefer Deployment Information > Services.
   - Example: OBP.

2. project_name:
   - Prefer Project Details > Project Name.
   - Example: Oracle Banking Payment.

3. release_version:
   - Prefer document Version or Release version.
   - Example: 5.12.60.

4. source_branch:
   - Extract branch from deployment steps.
   - Example sentence:
     DevOps Team will sync the OBP_Kernel_Hotfix_T24_USUKHK from the Profinch to Mashreq Env.
   - source_branch = OBP_Kernel_Hotfix_T24_USUKHK.

5. azure_commit_id:
   - Extract 40-character commit SHA if present.

6. target_environment:
   - Extract deployment target environment.
   - Example: T24-UAT.

7. change_type:
   - Extract values like KERNEL, UI, DB, CONFIG if available.

8. confidence:
   - high if application_name and source_branch are clearly found.
   - medium if one value is inferred.
   - low if important values are missing.

9. notes:
   - Mention missing or inferred fields.

Document text:
{document_text}
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You extract code-pull pipeline parameters from release documents."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return extract_json_from_ai_response(response.choices[0].message.content)
