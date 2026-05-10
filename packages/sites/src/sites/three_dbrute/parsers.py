"""3dbrute.com HTML 解析器。"""

import json
import re
from typing import Any

from bs4 import BeautifulSoup, Tag


def parse_detail_page(html: str) -> dict[str, Any]:
    """解析 3dbrute.com 模型详情页 HTML，返回完整 Meta Schema。"""
    soup = BeautifulSoup(html, "html.parser")
    pd = _parse_meta_desc(soup)
    tbl = _parse_table(soup)
    ld = _parse_ldjson(soup)
    btn = _parse_download_button(soup)
    previews = _parse_previews(soup)
    likes = _int(soup.select_one(".like-count"))
    bookmarks = _int(soup.select_one(".bookmark-count"))
    followers = _int(soup.select_one(".post-followers"))
    author_name, author_url = _parse_author(soup, ld)
    tags = _ld_val(ld, "Article", "keywords")
    category = _ld_val(ld, "Article", "articleSection")
    date_published = _ld_val(ld, "Article", "datePublished")
    dim_str = pd.get("Dimension") or tbl.get("Dimensions") or ""
    dim_m = re.match(r"^([\d.]+)\s*x\s*([\d.]+)\s*x\s*([\d.]+)", dim_str)
    dimensions = {"x": _float(dim_m[1]), "y": _float(dim_m[2]), "z": _float(dim_m[3])} if dim_m else {"x": 0, "y": 0, "z": 0}
    colors = re.findall(r"#[0-9a-fA-F]{6}", tbl.get("Colors", ""))

    if pd.get("Verts"):
        vm = re.match(r"^(\d+)\s+X\s+([\d.]+)\s+Y\s+([\d.]+)\s+Z\s+([\d.]+)", pd["Verts"])
        if vm:
            pd["Verts"] = vm[1]
            pd["Dimension"] = f"{vm[2]} x {vm[3]} x {vm[4]}"
            dimensions = {"x": _float(vm[2]), "y": _float(vm[3]), "z": _float(vm[4])}

    formats = [img.get("alt", "").lower() for img in soup.select(".format-item img[alt]") if img.get("alt")]
    h1 = soup.select_one("h1")
    name = h1.text.strip() if h1 else pd.get("Name", "")
    price = 0
    pp = soup.select_one(".product-price")
    if pp and (pm := re.search(r"[\d.]+", pp.text)):
        price = _float(pm[0])
    slug = ""
    og_url = soup.select_one('meta[property="og:url"]')
    if og_url:
        slug = og_url.get("content", "").rstrip("/").rsplit("/", 1)[-1] or ""

    return {
        "name": name, "slug": slug, "platform": "3dbrute",
        "url": og_url.get("content", "") if og_url else "",
        "product_id": btn.get("order_id", ""),
        "license": _text(soup.select_one(".type"), "free").lower(), "price": price,
        "author": {"name": author_name, "profile_url": author_url, "followers": followers},
        "previews": previews,
        "files": [{
            "software_version": pd.get("Format") or tbl.get("Version", ""),
            "formats": formats,
            "export_formats": [x.strip() for x in pd.get("Export", "").split(",") if x.strip()],
            "renderer": pd.get("Render") or tbl.get("Render", ""),
            "polygons": _int(pd.get("Polys")) or _int(tbl.get("Polygons")) or 0,
            "vertices": _int(pd.get("Verts")) or _int(tbl.get("Vertices")) or 0,
            "material_classes": [x.strip() for x in pd.get("Matclasses", "").split(",") if x.strip()],
            "units": pd.get("Units", ""), "dimensions": dimensions,
            "style": tbl.get("Style", ""),
            "low_poly": "low poly" in tbl.get("Opt. Standards", "").lower(),
            "material": tbl.get("Material", ""), "colors": colors, "size": tbl.get("Size", ""),
            "archive": {"url": btn.get("url", ""), "nonce": btn.get("nonce", ""), "path": ""},
        }],
        "publication": {
            "date": tbl.get("Date", ""), "date_published": date_published or "",
            "views": _int(tbl.get("Views")) or 0, "likes": likes, "bookmarks": bookmarks,
            "category": category[0] if isinstance(category, list) and category else (category or ""),
        },
        "metadata": {
            "manufacturer": pd.get("Manufacturer", ""),
            "product_url": pd.get("Product_url") or tbl.get("Product link", ""),
            "tags": tags if isinstance(tags, list) else [],
        },
    }


def _parse_meta_desc(soup: BeautifulSoup) -> dict[str, str]:
    tag = soup.select_one('meta[name="description"]')
    if not tag:
        return {}
    desc = tag.get("content", "")
    keys = ["Name:", "Format:", "Export:", "Render:", "Polys:", "Verts:", "Matclasses:", "Units:", "Dimension:", "Manufacturer:", "Product_url:", "Link:"]
    found = []
    for k in keys:
        idx = desc.find(k)
        if idx != -1:
            found.append({"key": k.replace(":", ""), "pos": idx, "len": len(k)})
    found.sort(key=lambda x: x["pos"])
    r = {}
    for i, f in enumerate(found):
        start = f["pos"] + f["len"]
        end = found[i + 1]["pos"] if i + 1 < len(found) else len(desc)
        r[f["key"]] = desc[start:end].strip()
    if r.get("Link") and not r.get("Product_url"):
        r["Product_url"] = r["Link"]
    return r


def _parse_table(soup: BeautifulSoup) -> dict[str, str]:
    table = soup.find("table", id="3dbrutecode01")
    if not table:
        return {}
    r = {}
    for tr in table.select("tr"):
        cells = tr.select("td")
        if len(cells) == 2:
            label = cells[0].text.strip().rstrip(":")
            r[label] = cells[1].text.strip()
    return r


def _parse_ldjson(soup: BeautifulSoup) -> dict | None:
    script = soup.select_one('script[type="application/ld+json"].yoast-schema-graph')
    if not script:
        return None
    try:
        return json.loads(script.text)
    except (json.JSONDecodeError, ValueError):
        return None


def _ld_val(ld: dict | None, type_name: str, field: str) -> Any:
    if not ld or "@graph" not in ld:
        return None
    for g in ld["@graph"]:
        if isinstance(g, dict) and g.get("@type") == type_name:
            val = g.get(field)
            if val is not None:
                return val
    return None


def _parse_download_button(soup: BeautifulSoup) -> dict[str, str]:
    btn = soup.select_one(".download-button-free")
    if not btn:
        return {}
    return {"url": btn.get("data-file-urls", ""), "nonce": btn.get("data-nonce", ""), "order_id": btn.get("data-order-id", "")}


def _parse_previews(soup: BeautifulSoup) -> list[dict[str, str]]:
    previews = []
    for img in soup.select("img[alt]"):
        alt = img.get("alt", "")
        if "Image" in alt and "Thumbnail" not in alt:
            parent = img.find_parent("a")
            if parent and parent.get("href"):
                previews.append({"url": parent["href"], "alt": alt})
    return previews


def _parse_author(soup: BeautifulSoup, ld: dict | None) -> tuple[str, str]:
    name = _ld_val(ld, "Person", "name") or ""
    url = _ld_val(ld, "Person", "url") or ""
    if name and url:
        return name, url
    link = soup.select_one('.info-column a[href*="/author/"]')
    if link:
        name = link.text.strip().rstrip("\u2026").strip()
        url = link.get("href", "")
    return name or "", url or ""


def _text(el: Tag | None, fallback: str = "") -> str:
    return el.text.strip() if el else fallback


def _int(v: Any) -> int:
    if v is None:
        return 0
    if isinstance(v, Tag):
        v = v.text
    if isinstance(v, str):
        m = re.search(r"\d+", v)
        return int(m[0]) if m else 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def _float(v: Any) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0
