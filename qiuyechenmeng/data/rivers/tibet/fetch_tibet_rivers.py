"""Fetch small, selected modern OSM river stretches for the reading map.

No raw regional extracts, catchments, interpolated vertices or gap filling.
Run from any directory with Python 3 and curl. Only this folder is written.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
API = "https://www.openstreetmap.org/api/0.6"
ATTRIBUTION = "© OpenStreetMap contributors, ODbL 1.0"
WAY_RIVERS = {
    398373303: ("yigong", "易贡藏布"),
    26407649: ("palong", "帕隆藏布"), 26407650: ("palong", "帕隆藏布"),
    26407652: ("palong", "帕隆藏布"), 67605162: ("palong", "帕隆藏布"),
    398222751: ("nyang", "尼洋河／尼洋曲"), 30960786: ("nyang", "尼洋河／尼洋曲"),
    26303813: ("angqu", "昂曲"), 401337798: ("zaqu", "扎曲"),
    26303815: ("lancang", "澜沧江"),
}
GROUPS = {
    "yigong_tongmai": {
        "name": "易贡藏布：易贡湖—通麦汇流口上游",
        "purpose": "通麦两支水系及易贡方向的现代地理参照；不认定古渡点",
        "rectangles_lonlat": [[94.73, 30.085, 95.085, 30.33]],
        "way_ids": [398373303],
        "gaps": ["未覆盖易贡湖北方完整上游与南方全河段。",
                 "汇流口以下way67604115仍标易贡藏布；异名未核清，最终GeoJSON排除该对象，不据此裁断历史薄藏布江所指。"],
    },
    "palong_tongmai_bomi": {
        "name": "帕隆藏布：通麦汇流区—波密",
        "purpose": "与易贡藏布分支同时显示的现代河道参照；不认定古渡点",
        "rectangles_lonlat": [[95.05, 29.79, 95.86, 30.12]],
        "way_ids": [26407649, 26407650, 26407652, 67605162],
        "relation_id": 15708490,
        "gaps": ["波密以东帕隆藏布完整上游未纳入。"],
    },
    "nyang_gongbo": {
        "name": "尼洋河／尼洋曲：太昭—工布江达—阿沛方向",
        "purpose": "现代方位参照；不标示作者确切渡河处",
        "rectangles_lonlat": [[93.00, 29.87, 93.36, 30.06]],
        "way_ids": [398222751, 30960786],
        "relation_id": 399036,
        "gaps": ["只取太昭至工布江达附近；未覆盖全尼洋河。"],
    },
    "lancang_chamdo": {
        "name": "昌都昂曲、扎曲及会合后的澜沧江",
        "purpose": "昌都现代汇流区的方位参照；不认定正文西藏桥或俄洛桥位置",
        "rectangles_lonlat": [[97.11, 31.085, 97.23, 31.18]],
        "way_ids": [26303813, 401337798, 26303815],
        "gaps": ["只取昌都短河段；昂曲、扎曲分别保留名称，未将会合前两支统称澜沧江。"],
    },
}


def fetch(way_id):
    url = f"{API}/way/{way_id}/full"
    result = subprocess.run(
        ["curl", "--fail", "--location", "--silent", "--show-error",
         "--max-time", "45", "--max-filesize", "2500000", "--retry", "1",
         "--user-agent", "QiuyeReadingMap/1.0 (personal reading map)", url],
        stdout=subprocess.PIPE, check=True)
    tree = ET.fromstring(result.stdout)
    nodes = {n.get("id"): [float(n.get("lon")), float(n.get("lat"))]
             for n in tree.findall("node")}
    way = next(w for w in tree.findall("way") if w.get("id") == str(way_id))
    refs = [n.get("ref") for n in way.findall("nd")]
    tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
    if tags.get("waterway") != "river":
        raise ValueError(f"Unexpected non-river way {way_id}: {tags}")
    return way_id, {
        "url": url, "xml_bytes": len(result.stdout),
        "xml_sha256": hashlib.sha256(result.stdout).hexdigest(),
        "osm_version": int(way.get("version")),
        "osm_timestamp": way.get("timestamp"), "node_refs": refs,
        "coordinates": [nodes[r] for r in refs], "tags": tags,
    }


def inside(point, rectangles):
    x, y = point
    return any(a <= x <= c and b <= y <= d for a, b, c, d in rectangles)


def select_original_runs(coords, rectangles):
    """Retain original adjacent pairs when either original vertex is inside.

    Adjacent selected pairs stay in one run. No boundary interpolation or
    simplification: even outside end vertices remain original OSM nodes.
    """
    selected = [inside(p, rectangles) for p in coords]
    start = end = None
    runs = []
    for i in range(len(coords) - 1):
        if selected[i] or selected[i + 1]:
            if start is None:
                start = i
            end = i + 1
        elif start is not None:
            runs.append((start, end))
            start = end = None
    if start is not None:
        runs.append((start, end))
    return runs


def bounds(coords):
    return [min(p[0] for p in coords), min(p[1] for p in coords),
            max(p[0] for p in coords), max(p[1] for p in coords)]


def main():
    way_ids = [wid for group in GROUPS.values() for wid in group["way_ids"]]
    fetched = dict(ThreadPoolExecutor(max_workers=2).map(fetch, way_ids))
    now = datetime.now(timezone.utc).isoformat()
    features = []
    groups = []
    for group_id, group in GROUPS.items():
        summary = dict(group, id=group_id)
        summary["feature_count"] = 0
        summary["vertex_count"] = 0
        coverage = []
        for wid in group["way_ids"]:
            source = fetched[wid]
            for part, (start, end) in enumerate(select_original_runs(
                    source["coordinates"], group["rectangles_lonlat"]), 1):
                coords = source["coordinates"][start:end + 1]
                refs = source["node_refs"][start:end + 1]
                properties = {
                    "river_group": group_id,
                    "river_id": WAY_RIVERS[wid][0], "name": WAY_RIVERS[wid][1],
                    "display_name": WAY_RIVERS[wid][1],
                    "note": group["purpose"],
                    "osm_name": source["tags"]["name"],
                    "waterway": "river", "osm_type": "way", "osm_id": wid,
                    "osm_part": part, "osm_version": source["osm_version"],
                    "osm_timestamp": source["osm_timestamp"],
                    "source_url": source["url"],
                    "source_relation_ids": [group["relation_id"]]
                    if "relation_id" in group else [],
                    "original_node_index_range_zero_based": [start, end],
                    "original_way_vertex_count": len(source["coordinates"]),
                    "first_osm_node_id": int(refs[0]),
                    "last_osm_node_id": int(refs[-1]),
                    "historical_crossing": "unlocated",
                    "purpose": group["purpose"], "osm_tags": source["tags"],
                }
                features.append({"type": "Feature", "properties": properties,
                                 "geometry": {"type": "LineString", "coordinates": coords}})
                summary["feature_count"] += 1
                summary["vertex_count"] += len(coords)
                coverage.extend(coords)
        summary["actual_bounds_lonlat"] = bounds(coverage) if coverage else None
        groups.append(summary)
    geojson = {"type": "FeatureCollection", "name": "Selected Tibet river centreline context",
               "attribution": ATTRIBUTION, "license": "ODbL-1.0",
               "license_url": "https://www.openstreetmap.org/copyright",
               "retrieved_at_utc": now, "features": features}
    target = OUT / "osm_rivers_tibet.geojson"
    target.write_text(json.dumps(geojson, ensure_ascii=False, separators=(",", ":")) + "\n")
    sources = [{"osm_way_id": wid, **{k: v for k, v in fetched[wid].items()
                if k not in {"node_refs", "coordinates", "tags"}}} for wid in way_ids]
    manifest = {
        "retrieved_at_utc": now, "crs": "WGS84 longitude, latitude (EPSG:4326)",
        "attribution": ATTRIBUTION, "license": "ODbL-1.0",
        "license_url": "https://www.openstreetmap.org/copyright",
        "geometry_file": target.name, "geometry_bytes": target.stat().st_size,
        "feature_count": len(features), "groups": groups, "sources": sources,
        "excluded_geometry": [
            {"osm_way_id": 67604115, "osm_name_observed": "易贡藏布",
             "source_url": f"{API}/way/67604115/full", "checked_date": "2026-10-31",
             "scope": "通麦汇流口以南；原始对象范围95.0129092,29.8748535至95.1323155,30.0960196",
             "reason": "OSM仍标易贡藏布；下游水系称名口径未核清，排除其几何以免河线误名。"}],
        "source_topology_notes": [
            "帕隆藏布way26407650与26407652在95.4333877,29.911948和95.4274543,29.9132891共享原始节点，两点之间两条原始河道线略有不同；保留源数据两支，不将它们重画成单一直线。"],
        "discovery_sources": [
            f"{API}/map?bbox=95.05,30.085,95.08,30.11",
            f"{API}/relation/15708490/full",
            f"{API}/map?bbox=93.24,29.88,93.26,29.90",
            f"{API}/map?bbox=97.172,31.122,97.187,31.134"],
        "method": [
            "Only selected OSM waterway=river ways are fetched; regional XML is not saved.",
            "Keep original adjacent OSM node pairs if either node is within the group's selection rectangle; keep contiguous runs separately.",
            "Every output vertex is an original OSM node coordinate. No interpolation, gap joining, smoothing, simplification, fabricated historical route or projected offset.",
            "Rectangle boundary runs can retain one adjacent original node outside the rectangle; actual bounds are recorded per group.",
            "OSM names describe the current dataset, not a resolution of historical river names or crossing locations."],
        "historical_limits": [
            "汤买／汤木与薄藏布江渡河有文本关联；古桥在通麦汇流口哪一支、哪一位置未由这些现代中心线证实。",
            "现代通麦桥不能直接充作古藤桥位置。河道迁移、2000年易贡事件及现代工程影响未重建。",
            "尼洋河与昌都澜沧江数据只作地理参照，不新增正文渡河断言。",
            "怒江南源阿克与穆鲁乌苏／通天河古渡点均未在本包定位或画出。"],
        "missing_geometry": [
            {"subject": "怒江南源阿克／哈喇乌苏", "status": "not_downloaded",
             "reason": "当前任务未取得可核验河段与古称对应；保留未定位。"},
            {"subject": "穆鲁乌苏／通天河渡点", "status": "not_downloaded",
             "reason": "未核实具体河段及古渡点；不以现代桥代替。"}],
        "rebuild": "python3 data/rivers/tibet/fetch_tibet_rivers.py",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"geojson_bytes": target.stat().st_size,
                      "feature_count": len(features),
                      "groups": [{k: g[k] for k in ["id", "feature_count", "vertex_count", "actual_bounds_lonlat"]} for g in groups]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
