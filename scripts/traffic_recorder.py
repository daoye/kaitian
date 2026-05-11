"""记录 HTTP 流量到 JSON Lines 文件。"""
import json
from datetime import datetime, timezone
from mitmproxy import http

MAX_BODY = 131072


class Recorder:
    def response(self, flow: http.HTTPFlow) -> None:
        req = flow.request
        resp = flow.response
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "method": req.method,
            "url": req.pretty_url,
            "request_headers": dict(req.headers),
            "response_headers": dict(resp.headers),
            "status": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
            "response_bytes": len(resp.content),
        }
        try:
            entry["request_body"] = req.get_text()[:MAX_BODY]
        except Exception:
            entry["request_body"] = f"<binary: {len(req.content)} bytes>"
        try:
            entry["response_body"] = resp.get_text()[:MAX_BODY]
        except Exception:
            entry["response_body"] = f"<binary: {len(resp.content)} bytes>"
        with open("traffic.jsonl", "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


addons = [Recorder()]
