"""Conversion DOCX -> PDF.

Primario : CloudConvert (job asíncrono, alta calidad).
Fallback  : ConvertAPI  (POST directo, 250s gratis/mes ≈ 80 lettres).
"""

import base64
import os
import time

import requests

CLOUDCONVERT_API_URL = "https://api.cloudconvert.com/v2"
CONVERTAPI_URL = "https://v2.convertapi.com/convert/docx/to/pdf"


def _raise_for_status(resp):
    if not resp.ok:
        try:
            detail = resp.json().get("message", resp.text)
        except ValueError:
            detail = resp.text
        raise requests.HTTPError(f"{resp.status_code} {detail}", response=resp)


# ── CloudConvert ──────────────────────────────────────────────────────────────

def _via_cloudconvert(docx_bytes, filename, max_wait, poll_interval):
    headers = {"Authorization": f"Bearer {os.environ['CLOUDCONVERT_API_KEY']}"}

    job_resp = requests.post(
        f"{CLOUDCONVERT_API_URL}/jobs",
        headers={**headers, "Content-Type": "application/json"},
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
    _raise_for_status(job_resp)
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
    _raise_for_status(upload_resp)

    elapsed = 0.0
    while elapsed < max_wait:
        status_resp = requests.get(
            f"{CLOUDCONVERT_API_URL}/jobs/{job_id}", headers=headers, timeout=15
        )
        _raise_for_status(status_resp)
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


# ── ConvertAPI (fallback) ─────────────────────────────────────────────────────

def _via_convertapi(docx_bytes, filename):
    secret = os.environ.get("CONVERTAPI_SECRET")
    if not secret:
        raise RuntimeError("CONVERTAPI_SECRET not configured")

    resp = requests.post(
        CONVERTAPI_URL,
        params={"Secret": secret},
        files={
            "File": (
                filename,
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        timeout=40,
    )
    _raise_for_status(resp)
    files = resp.json().get("Files", [])
    if not files:
        raise RuntimeError("ConvertAPI returned no files")
    return base64.b64decode(files[0]["FileData"])


# ── Punto de entrada ──────────────────────────────────────────────────────────

def docx_a_pdf(docx_bytes, filename="lettre.docx", max_wait=25, poll_interval=1.5):
    """Convierte bytes DOCX a bytes PDF. Usa CloudConvert; cae a ConvertAPI en 402."""
    try:
        return _via_cloudconvert(docx_bytes, filename, max_wait, poll_interval)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 402:
            print("⚠️  CloudConvert sin créditos, usando ConvertAPI como fallback.")
            return _via_convertapi(docx_bytes, filename)
        raise
