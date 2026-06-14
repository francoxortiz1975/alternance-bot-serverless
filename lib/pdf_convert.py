"""Conversion DOCX -> PDF via l'API CloudConvert (free tier)."""

import os
import time

import requests

CLOUDCONVERT_API_URL = "https://api.cloudconvert.com/v2"


def _headers():
    api_key = os.environ["CLOUDCONVERT_API_KEY"]
    return {"Authorization": f"Bearer {api_key}"}


def docx_a_pdf(docx_bytes, filename="lettre.docx", max_wait=25, poll_interval=1.5):
    """Convertit des bytes DOCX en bytes PDF via CloudConvert. Lève une exception en cas d'échec."""
    job_resp = requests.post(
        f"{CLOUDCONVERT_API_URL}/jobs",
        headers={**_headers(), "Content-Type": "application/json"},
        json={
            "tasks": {
                "import-file": {"operation": "import/upload"},
                "convert-file": {
                    "operation": "convert",
                    "input": "import-file",
                    "input_format": "docx",
                    "output_format": "pdf",
                },
                "export-file": {"operation": "export/url", "input": "convert-file"},
            }
        },
        timeout=15,
    )
    job_resp.raise_for_status()
    job = job_resp.json()["data"]
    job_id = job["id"]

    import_task = next(t for t in job["tasks"] if t["name"] == "import-file")
    upload_form = import_task["result"]["form"]
    upload_resp = requests.post(
        upload_form["url"],
        data=upload_form["parameters"],
        files={"file": (filename, docx_bytes)},
        timeout=15,
    )
    upload_resp.raise_for_status()

    elapsed = 0.0
    while elapsed < max_wait:
        status_resp = requests.get(
            f"{CLOUDCONVERT_API_URL}/jobs/{job_id}", headers=_headers(), timeout=15
        )
        status_resp.raise_for_status()
        job = status_resp.json()["data"]

        if job["status"] == "error":
            raise RuntimeError(f"CloudConvert job failed: {job}")

        if job["status"] == "finished":
            export_task = next(t for t in job["tasks"] if t["name"] == "export-file")
            file_url = export_task["result"]["files"][0]["url"]
            pdf_resp = requests.get(file_url, timeout=15)
            pdf_resp.raise_for_status()
            return pdf_resp.content

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError("CloudConvert job did not finish in time")
