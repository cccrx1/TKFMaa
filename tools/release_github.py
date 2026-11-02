"""Small GitHub REST transport with explicit read/write boundaries."""

import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise ValueError("Non-HTTPS redirect refused")
        redirected = super().redirect_request(request, fp, code, msg, headers, newurl)
        if redirected and urlsplit(request.full_url).netloc != urlsplit(newurl).netloc:
            redirected.remove_header("Authorization")
        return redirected


class GitHub:
    def __init__(self, repository: str, token: str | None = None, writable: bool = False):
        if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Invalid repository")
        self.repository, self.token, self.writable = repository, token, writable
        self.opener = build_opener(SafeRedirect())

    def request(self, method: str, path: str, payload=None, upload: Path | None = None):
        if method != "GET" and (not self.writable or not self.token):
            raise ValueError("Remote writes are disabled")
        if not path.startswith("/") or ".." in path:
            raise ValueError("Invalid API path")
        host = "uploads.github.com" if upload else "api.github.com"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "TKFMaa-release",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        data = json.dumps(payload).encode() if payload is not None else None
        if data is not None:
            headers["Content-Type"] = "application/json"
        stream = None
        try:
            if upload:
                stream = upload.open("rb")
                data = stream
                headers.update({"Content-Type": "application/octet-stream", "Content-Length": str(upload.stat().st_size)})
            request = Request(f"https://{host}/repos/{self.repository}{path}", data=data, headers=headers, method=method)
            with self.opener.open(request, timeout=120) as response:
                return json.load(response)
        except HTTPError as error:
            # Do not print response bodies, signed URLs or credentials.
            raise RuntimeError(f"GitHub {method} failed with HTTP {error.code}") from None
        finally:
            if stream:
                stream.close()

    def pages(self, path: str) -> list:
        result = []
        for page in range(1, 1001):
            batch = self.request("GET", f"{path}?per_page=100&page={page}")
            if not isinstance(batch, list):
                raise ValueError("Unexpected paginated response")
            result.extend(batch)
            if len(batch) < 100:
                return result
        raise ValueError("Pagination limit reached; refusing incomplete remote state")

    def snapshot(self) -> dict:
        releases = self.pages("/releases")
        for release in releases:
            release["assets"] = self.pages(f"/releases/{int(release['id'])}/assets")
        return {"repository": self.repository, "complete": True, "releases": releases,
                "tags": self.pages("/tags")}

    def resolve_tag(self, tag: str) -> str:
        obj = self.request("GET", "/git/ref/tags/" + quote(tag, safe=""))["object"]
        for _ in range(8):
            if obj["type"] == "commit" and re.fullmatch(r"[0-9a-f]{40}", obj["sha"]):
                return obj["sha"]
            if obj["type"] != "tag" or not re.fullmatch(r"[0-9a-f]{40}", obj["sha"]):
                break
            obj = self.request("GET", "/git/tags/" + obj["sha"])["object"]
        raise ValueError("Tag does not resolve to a commit")

    def download(self, asset: dict, destination: Path) -> None:
        expected = asset.get("digest", "")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", expected or "") or not 0 < asset["size"] <= 4 * 1024**3:
            raise ValueError("Source asset lacks a valid digest or size")
        # Public source only: no token is forwarded to downloads or redirects.
        request = Request(f"https://api.github.com/repos/{self.repository}/releases/assets/{int(asset['id'])}",
                          headers={"Accept": "application/octet-stream", "User-Agent": "TKFMaa-release",
                                   "X-GitHub-Api-Version": "2022-11-28"})
        checksum, size = hashlib.sha256(), 0
        with self.opener.open(request, timeout=120) as response, destination.open("xb") as target:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > asset["size"]:
                    raise ValueError("Download exceeds declared size")
                checksum.update(chunk)
                target.write(chunk)
        if size != asset["size"] or "sha256:" + checksum.hexdigest() != expected:
            raise ValueError("Downloaded source asset digest/size mismatch")
