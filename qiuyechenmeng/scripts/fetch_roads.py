"""Fetch selected OSM road relations from the official read-only API.

No routing, interpolation, or inferred road geometry is added.  Each GeoJSON
feature retains the original OSM way ID and the source relation references.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "roads"
CACHE = Path("/tmp/qiuye-road-osm-cache")
RELATIONS = {
    "G108": 554657,
    "G109": 153104,
    "G214": 358995,
    "G248": 13902178,
    "G317": 215491,
    "G318:Sichuan": 20295422,
    "G318:Xizang": 20295421,
    "G349": 13088685,
    "G350:Sichuan": 20295532,
    "S434": 14953102,
    "S303": 8426861,
}
SELECTED_REFS = {r.split(":")[0] for r in RELATIONS} | {"S434", "S303", "S205"}
# Lon/lat rectangles. These select context only; the build script may further
# clip the corridors used in the reading map.
BOUNDS = [(92.0, 29.0, 104.4, 32.6), (94.3, 35.7, 104.1, 37.3)]


def get_relation(item):
    ref, rid = item
    ref = ref.split(":")[0]
    path = CACHE / f"{rid}.osm"
    url = f"https://www.openstreetmap.org/api/0.6/relation/{rid}/full"
    if not path.exists():
        subprocess.run(["curl", "--fail", "--location", "--silent",
                        "--show-error", "--max-time", "100", "--retry", "1",
                        "--user-agent", "QiuyeReadingMap/1.0 (personal reading map)",
                        "--output", str(path), url], check=True)
    tree = ET.parse(path).getroot()
    # Standard /full supplies way members and their nodes. Child relations,
    # if encountered, are recorded rather than assumed to be resolved.
    children = [m.get("ref") for r in tree.findall("relation")
                for m in r.findall("member") if m.get("type") == "relation"]
    print(ref, path.stat().st_size, "bytes", flush=True)
    return ref, rid, url, tree, children


def inside(lon, lat):
    return any(a <= lon <= c and b <= lat <= d for a, b, c, d in BOUNDS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    results = list(ThreadPoolExecutor(max_workers=2).map(get_relation, RELATIONS.items()))
    nodes, ways, memberships, sources = {}, {}, {}, []
    for ref, rid, url, tree, children in results:
        sources.append({"ref": ref, "relation_id": rid, "url": url,
                        "unresolved_child_relations": children})
        for n in tree.findall("node"):
            nodes[n.get("id")] = [float(n.get("lon")), float(n.get("lat"))]
        for w in tree.findall("way"):
            ways[w.get("id")] = w
        rel = next(r for r in tree.findall("relation") if r.get("id") == str(rid))
        for m in rel.findall("member"):
            if m.get("type") == "way":
                memberships.setdefault(m.get("ref"), set()).add(ref)
    features = []
    for wid, way in ways.items():
        tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
        if "highway" not in tags:
            continue
        coords = [nodes[n.get("ref")] for n in way.findall("nd")]
        if not any(inside(*p) for p in coords):
            continue
        refs = set(tags.get("ref", "").replace(" ", "").split(";"))
        relation_refs = memberships.get(wid, set())
        if not (refs | relation_refs) & SELECTED_REFS:
            continue
        features.append({"type": "Feature", "properties": {
            "osm_id": int(wid), "ref": tags.get("ref", ""),
            "name": tags.get("name", ""), "highway": tags["highway"],
            "source_relation_refs": sorted(relation_refs),
            **{k: tags[k] for k in ["bridge", "tunnel", "access", "construction", "proposed"] if k in tags},
        }, "geometry": {"type": "LineString", "coordinates": coords}})
    now = datetime.now(timezone.utc).isoformat()
    data = {"type": "FeatureCollection", "name": "Selected modern road context",
            "attribution": "© OpenStreetMap contributors, ODbL 1.0",
            "source": "https://www.openstreetmap.org/copyright",
            "retrieved_at_utc": now, "features": features}
    (OUT / "osm_roads.geojson").write_text(json.dumps(data, ensure_ascii=False,
                                                         separators=(",", ":")) + "\n")
    manifest = {"retrieved_at_utc": now, "crs": "WGS84 longitude, latitude",
                "license": "ODbL-1.0", "attribution": data["attribution"],
                "license_url": data["source"], "sources": sources,
                "relation_index": "https://wiki.openstreetmap.org/wiki/China/Transport/National_Highways",
                "province_relation_discovery_sources": [
                    "https://www.openstreetmap.org/api/0.6/map?bbox=101.55,30.15,101.85,30.35",
                    "https://www.openstreetmap.org/api/0.6/map?bbox=94.75,30.12,95.05,30.42",
                    "https://www.openstreetmap.org/api/0.6/map?bbox=92.95,30.0,93.3,30.4"],
                "selection_rectangles_lonlat": BOUNDS,
                "feature_count": len(features),
                "limits": ["OSM completeness and road references may lag official road changes.",
                           "S434 and S303 are directly sourced route relations. No S205-tagged geometry was found in the sampled Niangpu/Taizhao area; OSM still labels that corridor S303.",
                           "No gap is joined or filled. Full original ways intersecting the selection rectangles are retained."]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print("Wrote", len(features), "road ways", flush=True)


if __name__ == "__main__":
    main()
