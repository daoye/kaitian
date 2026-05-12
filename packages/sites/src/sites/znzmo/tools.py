"""znzmo 纯工具函数 — 无业务逻辑，可被 agent 调用。"""

import zipfile
from pathlib import Path

_MODEL_EXTS = {
    ".max", ".blend", ".skp", ".3dm", ".rvt", ".c4d",
    ".obj", ".fbx", ".3ds", ".dwg", ".dxf", ".stl",
    ".iges", ".step",
}
_RENDER_KEYWORDS = {"rendir", "preview", "thumb", "渲染", "预览"}


def _is_render_preview(fp: Path) -> bool:
    return any(kw in fp.stem.lower() for kw in _RENDER_KEYWORDS)


def group_files(extracted: Path) -> list[list[Path]]:
    """将 extracted 目录下的文件按模型文件分组打包。"""
    all_files = [f for f in extracted.rglob("*") if f.is_file()]
    model_files = [f for f in all_files if f.suffix.lower() in _MODEL_EXTS]
    support_files = [f for f in all_files if f.suffix.lower() not in _MODEL_EXTS]
    if not model_files:
        return [all_files]
    if len(model_files) == 1:
        return [all_files]
    groups: list[list[Path]] = []
    for mf in model_files:
        package = [mf]
        for sf in support_files:
            if not _is_render_preview(sf):
                package.append(sf)
        groups.append(package)
    return groups


def create_temp_archives(model_dir: str) -> tuple[list[str], list[dict]]:
    """打包 extracted 目录为临时 zip，返回 (archive_paths, archive_metas)。"""
    model_path = Path(model_dir)
    extracted = model_path / "extracted"
    if not extracted.exists():
        raise RuntimeError(f"extracted 不存在: {extracted}")

    groups = group_files(extracted)
    if not groups or not groups[0]:
        raise RuntimeError("无文件可打包")

    archives: list[str] = []
    metas: list[dict] = []
    for i, file_list in enumerate(groups):
        tag = f"_{i}" if len(groups) > 1 else ""
        zip_name = f".upload_temp{tag}.zip"
        zip_path = model_path / zip_name
        count = 0
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in file_list:
                zf.write(str(fp), str(fp.relative_to(extracted)))
                count += 1
        if count == 0:
            zip_path.unlink(missing_ok=True)
            continue
        archives.append(str(zip_path))
        # initName 使用原始文件名（去掉临时 zip 后缀，保留实际后缀）
        first_file = file_list[0]
        actual_init_name = first_file.name if first_file.suffix else zip_name
        metas.append({"path": str(zip_path), "initName": actual_init_name, "fileCount": count})
        print(f"  包{i+1}: {count} 个文件 → {zip_name} (initName: {actual_init_name})")

    if not archives:
        raise RuntimeError("打包后无有效文件")
    return archives, metas


def repair_image(image_path: str) -> str:
    """修复图片：确保 >=1000x1000 且 >=50KB，返回新路径。"""
    from PIL import Image
    img = Image.open(image_path)

    # 颜色模式转换
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    min_dim = min(w, h)

    # 尺寸修复：最小边不足 1000 时，按比例放大到 1024（留余量）
    if min_dim < 1000:
        ratio = 1024 / min_dim
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        print(f"  [cyan]图片尺寸修复: {w}x{h} → {new_w}x{new_h}[/cyan]")
        w, h = new_w, new_h

    stem = Path(image_path).stem
    parent = Path(image_path).parent
    repaired = str(parent / f"{stem}_repaired.jpg")

    # 文件大小修复：确保 >= 50KB
    quality = 85
    img.save(repaired, "JPEG", quality=quality)
    file_size_kb = Path(repaired).stat().st_size / 1024

    # 逐步提高质量直到满足 50KB
    while file_size_kb < 50 and quality < 100:
        quality = min(quality + 5, 100)
        img.save(repaired, "JPEG", quality=quality)
        file_size_kb = Path(repaired).stat().st_size / 1024

    # 若质量提到最高仍不足 50KB，轻微放大（120%）增加体积
    if file_size_kb < 50:
        new_w = int(w * 1.2)
        new_h = int(h * 1.2)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        img.save(repaired, "JPEG", quality=95)
        file_size_kb = Path(repaired).stat().st_size / 1024
        print(f"  [cyan]图片放大修复: {w}x{h} → {new_w}x{new_h}, {file_size_kb:.1f}KB[/cyan]")
    else:
        print(f"  [cyan]图片已修复: {w}x{h}, {file_size_kb:.1f}KB (quality={quality})[/cyan]")

    return repaired


def cleanup_archives(archives: list[str]) -> None:
    for a in archives:
        Path(a).unlink(missing_ok=True)
    print("  清理临时文件")
