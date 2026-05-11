"""捕获 uploadModelNew.do 请求的 addon。"""
from mitmproxy import http
import json
import time


class ZnzmoSubmitSniffer:
    def __init__(self):
        self.captured = []

    def request(self, flow: http.HTTPFlow) -> None:
        if "uploadModelNew.do" in flow.request.pretty_url:
            body = flow.request.get_text()
            self.captured.append({
                "time": time.time(),
                "url": flow.request.pretty_url,
                "method": flow.request.method,
                "headers": dict(flow.request.headers),
                "body": body,
            })
            # Save immediately
            with open("data/znzmo_submit_payload.json", "w", encoding="utf-8") as f:
                json.dump(self.captured, f, ensure_ascii=False, indent=2)
            print(f"[CAPTURED] {flow.request.pretty_url}")
            print(f"  Body: {body[:2000]}")

    def done(self) -> None:
        if self.captured:
            print(f"\nCaptured {len(self.captured)} requests. Saved to data/znzmo_submit_payload.json")


addons = [ZnzmoSubmitSniffer()]
