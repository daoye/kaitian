"""通用后处理模块：解压、格式转换、路径更新、预览图下载。"""

import json
import subprocess
from pathlib import Path

import httpx


def update_archive_path(model_dir: str | Path) -> None:
    """将 meta.json 中 archive.path 更新为 originals 中的实际文件名。"""
    model_dir = Path(model_dir)
    meta_path = model_dir / "meta.json"
    originals_dir = model_dir / "originals"
    if not originals_dir.exists():
        return
    files = list(originals_dir.iterdir())
    if not files:
        return
    actual = max(files, key=lambda f: f.stat().st_mtime)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    entry = meta.get("files", [{}])[0]
    if "archive" in entry:
        entry["archive"]["path"] = f"originals/{actual.name}"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  archive.path -> originals/{actual.name}")


def convert_previews(model_dir: str | Path) -> list[dict]:
    """将 previews 中的非 png/jpg 转为 png/jpg 并更新 meta.json。"""
    from PIL import Image

    model_dir = Path(model_dir)
    previews_dir = model_dir / "previews"
    if not previews_dir.exists():
        return []
    image_exts = {".webp", ".bmp", ".tiff", ".tif", ".gif", ".ico"}
    converted = []
    for path in sorted(previews_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in image_exts:
            continue
        img = Image.open(path)
        has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
        out_path = path.with_suffix(".png") if has_alpha else path.with_suffix(".jpg")
        if path == out_path:
            continue
        if not has_alpha and img.mode in ("P", "RGBA", "LA", "CMYK"):
            img = img.convert("RGB")
        kwargs = {"quality": 95} if out_path.suffix == ".jpg" else {}
        img.save(out_path, **kwargs)
        path.unlink()
        converted.append({"old": path.name, "new": out_path.name})
        print(f"  convert: {path.name} -> {out_path.name}")
    if converted:
        meta_path = model_dir / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            for p in meta.get("previews", []):
                old_name = Path(p["url"]).name
                for c in converted:
                    if c["old"] == old_name:
                        p["url"] = p["url"].replace(c["old"], c["new"])
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return converted


def extract_archive(model_dir: str | Path, seven_zip: str = r"C:\Program Files\7-Zip\7z.exe") -> None:
    """解压 originals 中的压缩包到 extracted 目录。"""
    model_dir = Path(model_dir)
    originals_dir = model_dir / "originals"
    extracted_dir = model_dir / "extracted"
    if not originals_dir.exists():
        return
    archives = [f for f in originals_dir.iterdir() if f.suffix.lower() in (".rar", ".zip", ".7z", ".tar", ".gz")]
    if not archives:
        return
    extracted_dir.mkdir(parents=True, exist_ok=True)
    for archive in archives:
        print(f"  extract: {archive.name}")
        r = subprocess.run([seven_zip, "x", str(archive), f"-o{extracted_dir}", "-y"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  extract failed: {archive.name} - {r.stderr[:200]}")
        else:
            print(f"  extract done: {archive.name}")


def download_preview(image_url: str, output_path: str | Path) -> dict:
    """下载预览图。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", image_url, follow_redirects=True) as stream:
        if stream.status_code == 403:
            raise RuntimeError(f"preview download failed (403): {image_url}")
        stream.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in stream.iter_bytes(chunk_size=8192):
                f.write(chunk)
    return {"path": str(output_path), "size": output_path.stat().st_size}
