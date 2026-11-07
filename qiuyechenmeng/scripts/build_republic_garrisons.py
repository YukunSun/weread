"""Build the early-Republic garrison comparison with modern representative points."""
from pathlib import Path
import csv
import html
import json
import math
import xml.etree.ElementTree as ET
import zipfile

from build_jiamiqingbo import NS, el, view, paragraph, source_links, icon_png
from output_paths import output_path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/place_checks/民初边军驻防核对.json"
NAME = "艽野尘梦_民初边军驻防"
COLORS = {"garrison": (82, 164, 255), "aid": (184, 125, 241)}


def haversine(a, b):
    """Spherical straight distance between two modern representative points, in km."""
    p, q = math.radians(a["lat"]), math.radians(b["lat"])
    dlon = math.radians(b["lon"] - a["lon"])
    h = math.sin((q - p) / 2) ** 2 + math.cos(p) * math.cos(q) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def overview(node):
    view(node, 97.7, 30.6, 600000)


def support_text(source):
    value = source["supports"]
    return "；".join(value) if isinstance(value, list) else str(value)


def sources_html(data):
    body = source_links(data)
    body += "<ul>" + "".join(
        "<li>" + html.escape(s["title"] + "：" + support_text(s)) + "</li>"
        for s in data["sources"]
    ) + "</ul>"
    return body


def distances_html(data, place_id=None):
    places = {p["id"]: p for p in data["places"]}
    pairs = [p for p in data["distance_pairs"]
             if place_id is None or place_id in [p["from"], p["to"]]]
    rows = "".join(
        "<tr><td>" + html.escape(p["label"]) + "</td><td>"
        + f'{haversine(places[p["from"]], places[p["to"]]):.1f} km'
        + "</td></tr>" for p in pairs)
    return ('<p><b>现代代表点球面直距</b></p><table border="1" cellpadding="4">'
            + rows + "</table><p>仅供空间对照；历史实走公里数与耗时未载。</p>")


def validate(data):
    places = {p["id"]: p for p in data["places"]}
    if len(data["places"]) != 4 or len(places) != 4:
        raise ValueError("Expected four distinct modern representative points")
    for p in data["places"]:
        if p["kind"] not in COLORS:
            raise ValueError(f'Unknown point kind: {p["kind"]}')
        if not (-180 <= p["lon"] <= 180 and -90 <= p["lat"] <= 90):
            raise ValueError(f'Invalid coordinates: {p["id"]}')
    for pair in [*data["distance_pairs"], data["direction"]]:
        if pair["from"] not in places or pair["to"] not in places:
            raise ValueError("Distance or direction references an unknown point")
    ids = list(places) + [c["id"] for c in data["cards"]] + ["republic_aid_direction"]
    if len(ids) != len(set(ids)):
        raise ValueError("Placemark IDs must be unique")


def make(data, bundled=False):
    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}kml")
    doc = el(root, "Document", id="republic_garrisons")
    el(doc, "name", data["title"])
    el(doc, "open", 1)
    el(doc, "description", paragraph("范围", data["scope"])
       + paragraph("时间口径", data["chronology_note"])
       + paragraph("距离口径", data["distance_note"]) + distances_html(data))
    overview(doc)
    for kind, color in COLORS.items():
        style = el(doc, "Style", id="republic_" + kind)
        iconstyle = el(style, "IconStyle")
        el(iconstyle, "color", "ffffffff" if bundled else
           "ff" + "".join(f"{c:02x}" for c in reversed(color)))
        el(iconstyle, "scale", 0.9)
        el(el(iconstyle, "Icon"), "href", f"icons/{kind}.png" if bundled else
           "https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png")
        labelstyle = el(style, "LabelStyle")
        el(labelstyle, "color", "ffffffff")
        el(labelstyle, "scale", 0.85)
    style = el(doc, "Style", id="republic_direction")
    linestyle = el(style, "LineStyle")
    el(linestyle, "color", "c0f17db8")
    el(linestyle, "width", 3)

    sources = sources_html(data)
    places = {p["id"]: p for p in data["places"]}
    for p in data["places"]:
        pm = el(doc, "Placemark", id=p["id"])
        el(pm, "name", p["name"])
        body = "<h3>" + html.escape(p["name"]) + "</h3>"
        body += paragraph("含义", p["note"])
        body += paragraph("点位性质", p["coordinate_method"])
        body += distances_html(data, p["id"])
        body += paragraph("时间口径", data["chronology_note"])
        body += paragraph("距离口径", data["distance_note"])
        el(pm, "description", body + sources)
        view(pm, p["lon"], p["lat"], 80000)
        el(pm, "styleUrl", "#republic_" + p["kind"])
        metadata = el(pm, "ExtendedData")
        values = {key: p[key] for key in ["kind", "note", "coordinate_method"]}
        values.update(chronology_note=data["chronology_note"], distance_note=data["distance_note"])
        for key, value in values.items():
            el(el(metadata, "Data", name=key), "value", value)
        point = el(pm, "Point")
        el(point, "altitudeMode", "clampToGround")
        el(point, "coordinates", f'{p["lon"]:.8f},{p["lat"]:.8f},0')

    direction = data["direction"]
    direction_km = haversine(places[direction["from"]], places[direction["to"]])
    pm = el(doc, "Placemark", id="republic_aid_direction")
    el(pm, "name", direction["name"] + f"｜代表点直距{direction_km:.1f} km")
    el(pm, "description", paragraph("示意性质", direction["note"])
       + paragraph("现代代表点直距", f"{direction_km:.1f} km；历史实走里程未载。")
       + paragraph("时间口径", data["chronology_note"])
       + paragraph("距离口径", data["distance_note"]) + sources)
    overview(pm)
    el(pm, "styleUrl", "#republic_direction")
    geometry = el(pm, "MultiGeometry")
    a, b = places[direction["from"]], places[direction["to"]]
    # Disjoint short strokes show an aid direction, without inventing a battle site or road.
    for n in range(16):
        coords = []
        for t in [n / 16, (n + 0.52) / 16]:
            coords.append(f'{a["lon"] + (b["lon"] - a["lon"]) * t:.8f},'
                          f'{a["lat"] + (b["lat"] - a["lat"]) * t:.8f},0')
        line = el(geometry, "LineString")
        el(line, "tessellate", 1)
        el(line, "altitudeMode", "clampToGround")
        el(line, "coordinates", " ".join(coords))

    for item in data["cards"]:
        pm = el(doc, "Placemark", id=item["id"])
        el(pm, "name", item["name"])
        body = "".join("<p>" + html.escape(p) + "</p>" for p in item["paragraphs"])
        el(pm, "description", body + sources)
        overview(pm)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    validate(data)
    places = {p["id"]: p for p in data["places"]}
    distances = [(pair, haversine(places[pair["from"]], places[pair["to"]]))
                 for pair in data["distance_pairs"]]
    (output_path('maps', NAME + ".kml")).write_bytes(make(data))
    with zipfile.ZipFile(output_path('maps', NAME + ".kmz"), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", make(data, bundled=True))
        for kind, color in COLORS.items():
            z.writestr(f"icons/{kind}.png", icon_png(color))

    with (output_path('tables', "民初边军驻防_距离耗时.csv")).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["条目", "起点", "终点", "现代代表点球面直距(km)",
                         "历史实走距离(km)", "历史耗时", "依据和限制"])
        for pair, km in distances:
            writer.writerow([pair["label"], places[pair["from"]]["name"],
                             places[pair["to"]]["name"], f"{km:.1f}", "未载", "未载",
                             "现代代表点之间的球面直距；" + data["distance_note"]])
        direction = data["direction"]
        writer.writerow([direction["name"], places[direction["from"]]["name"],
                         places[direction["to"]]["name"], "", "未载", "未载", direction["note"]])

    note = [data["title"], "", data["scope"], data["chronology_note"], data["distance_note"], ""]
    for p in data["places"]:
        note.extend([p["name"], f'现代代表点：{p["lon"]:.8f}, {p["lat"]:.8f}',
                     p["note"], p["coordinate_method"], ""])
    note.extend([direction["name"], direction["note"], "历史实走距离与耗时：未载。", ""])
    for item in data["cards"]:
        note.extend([item["name"], *item["paragraphs"], ""])
    note.append("距离对照（现代代表点球面直距）")
    for pair, km in distances:
        note.append(f'{pair["label"]}：{km:.1f} km；历史实走距离与耗时未载。')
    note.extend(["", "来源"])
    for source in data["sources"]:
        note.extend([source["title"], source["url"], "支持内容：" + support_text(source), ""])
    (output_path('docs', "民初边军驻防核对说明.txt")).write_text("\n".join(note).rstrip() + "\n", encoding="utf-8")
    print(f'Created {NAME}.kml/.kmz: {len(places)} representative points, '
          f'1 direction (16 strokes), {len(data["cards"])} cards, {len(distances)} distance comparisons')


if __name__ == "__main__":
    main()
