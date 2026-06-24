import os
import requests
from requests.auth import HTTPBasicAuth

ORG = os.getenv("AZDO_ORG")
PROJECT = os.getenv("AZDO_PROJECT")
PAT = os.getenv("AZDO_PAT")
BRANCH = os.getenv("AZDO_BRANCH", "refs/heads/master")
API_VERSION = "7.1"

CODE_PULL_PIPELINE_NAME = os.getenv("CODE_PULL_PIPELINE_NAME")
CODE_PULL_PIPELINE_ID = os.getenv("CODE_PULL_PIPELINE_ID")
CODE_PULL_PARAM_APPLICATION = os.getenv("CODE_PULL_PARAM_APPLICATION", "APPLICATION")
CODE_PULL_PARAM_BRANCH = os.getenv("CODE_PULL_PARAM_BRANCH", "BRANCH_NAME")
CODE_PULL_PARAM_ENVIRONMENT = os.getenv("CODE_PULL_PARAM_ENVIRONMENT", "ENVIRONMENT")
CODE_PULL_PARAM_RELEASE_VERSION = os.getenv("CODE_PULL_PARAM_RELEASE_VERSION", "")
CODE_PULL_PARAM_COMMIT_ID = os.getenv("CODE_PULL_PARAM_COMMIT_ID", "")
CODE_PULL_PARAM_CHANGE_TYPE = os.getenv("CODE_PULL_PARAM_CHANGE_TYPE", "")


def azdo_auth():
    return HTTPBasicAuth("", PAT)


def list_pipelines():
    url = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis/pipelines?api-version={API_VERSION}"
    response = requests.get(url, auth=azdo_auth(), timeout=30)
    response.raise_for_status()
    return response.json().get("value", [])


def resolve_pipeline_id(pipeline_name):
    for pipeline in list_pipelines():
        if pipeline.get("name") == pipeline_name:
            return pipeline.get("id")
    return None


def post_pipeline_run(pipeline_id, template_parameters):
    url = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis/pipelines/{pipeline_id}/runs?api-version={API_VERSION}"
    payload = {
        "resources": {"repositories": {"self": {"refName": BRANCH}}},
        "templateParameters": template_parameters,
    }
    response = requests.post(url, json=payload, auth=azdo_auth(), headers={"Content-Type": "application/json"}, timeout=30)
    if response.status_code not in [200, 201]:
        raise Exception(response.text)
    return response.json()


def trigger_image_pipeline(pipeline_id, vendor_image, use_vendor_image):
    return post_pipeline_run(pipeline_id, {
        "vendorImage": vendor_image,
        "useVendorImage": use_vendor_image,
    })


def trigger_code_pull_pipeline(code_pull_json):
    pipeline_id = CODE_PULL_PIPELINE_ID
    if not pipeline_id:
        if not CODE_PULL_PIPELINE_NAME:
            raise Exception("Either CODE_PULL_PIPELINE_ID or CODE_PULL_PIPELINE_NAME must be configured")
        pipeline_id = resolve_pipeline_id(CODE_PULL_PIPELINE_NAME)
    if not pipeline_id:
        raise Exception(f"Could not resolve code-pull pipeline: {CODE_PULL_PIPELINE_NAME}")

    param_map = {
        CODE_PULL_PARAM_APPLICATION: code_pull_json.get("application_name", ""),
        CODE_PULL_PARAM_BRANCH: code_pull_json.get("source_branch", ""),
        CODE_PULL_PARAM_ENVIRONMENT: code_pull_json.get("target_environment", ""),
        CODE_PULL_PARAM_RELEASE_VERSION: code_pull_json.get("release_version", ""),
        CODE_PULL_PARAM_COMMIT_ID: code_pull_json.get("azure_commit_id", ""),
        CODE_PULL_PARAM_CHANGE_TYPE: code_pull_json.get("change_type", ""),
    }
    template_parameters = {key: value for key, value in param_map.items() if key and value is not None}
    if not template_parameters:
        raise Exception("No code-pull parameters generated. Check CODE_PULL_PARAM_* env vars.")
    return post_pipeline_run(pipeline_id, template_parameters)


def get_run_status(pipeline_id, run_id):
    url = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis/pipelines/{pipeline_id}/runs/{run_id}?api-version={API_VERSION}"
    response = requests.get(url, auth=azdo_auth(), timeout=30)
    if response.status_code != 200:
        return {"state": "unknown", "result": "unknown", "url": "", "error": response.text}
    data = response.json()
    return {
        "state": data.get("state", ""),
        "result": data.get("result", ""),
        "url": data.get("_links", {}).get("web", {}).get("href", ""),
        "error": "",
    }
