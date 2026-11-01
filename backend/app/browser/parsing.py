import re

# Current HH resume IDs used in public and applicant URLs are 38 lowercase
# hexadecimal characters. This deliberately excludes service routes such as
# /resume/edit, which otherwise look like a resume link in the DOM.
RESUME_PATH_RE = re.compile(r"/resume/([0-9a-f]{38})(?:[/?#]|$)", re.IGNORECASE)
RESUME_ID_RE = re.compile(r"^[0-9a-f]{38}$", re.IGNORECASE)


def resume_id_from_url(url: str) -> str | None:
    match = RESUME_PATH_RE.search(url)
    return match.group(1).lower() if match else None
