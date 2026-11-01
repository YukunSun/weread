"""Build Peng Risheng's separately sourced northern campaign supplement."""
from pathlib import Path
import csv
import html
import json
import math
import xml.etree.ElementTree as ET
import zipfile
from build_jiamiqingbo import NS, el, view, paragraph, source_links, icon_png

ROOT = Path(__file__).resolve().parents[1]
NAME = "艽野尘梦_彭日升北路入波"
DATA = ROOT / "data/place_checks/彭日升硕板多入波核对.json"
COLORS = {"reference": (137, 216, 255), "candidate": (255, 179, 71), "context": (190, 198, 208)}


def haversine(a, b):
    p, q = math.radians(a["lat"]), math.radians(b["lat"])
    dlon = math.radians(b["lon"] - a["lon"])
    h = math.sin((q-p)/2)**2 + math.cos(p)*math.cos(q)*math.sin(dlon/2)**2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def overview(node):
    view(node, 95.4, 30.45, 200000)


def card(parent, item_id, name, body):
    pm = el(parent, "Placemark", id=item_id)
    el(pm, "name", name)
    el(pm, "description", body)
    overview(pm)


def make(data, bundled=False):
    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}kml")
    doc = el(root, "Document", id="peng_north_campaign")
    el(doc, "name", "《艽野尘梦》彭日升北路入波｜硕板多—春多山—中波密")
    el(doc, "open", 1)
    el(doc, "description", paragraph("范围", data["scope"]) + paragraph("地理骨架", data["geographic_sequence"]))
    overview(doc)
    for kind in COLORS:
        style = el(doc, "Style", id="peng_" + kind)
        iconstyle = el(style, "IconStyle")
        el(iconstyle, "color", "ffffffff" if bundled else "ff" + "".join(f"{c:02x}" for c in reversed(COLORS[kind])))
        el(iconstyle, "scale", 0.9)
        el(el(iconstyle, "Icon"), "href", f"icons/{kind}.png" if bundled else
           "https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png")
        labelstyle = el(style, "LabelStyle")
        el(labelstyle, "color", "ffffffff")
        el(labelstyle, "scale", 0.85)
    style = el(doc, "Style", id="peng_direction")
    linestyle = el(style, "LineStyle")
    el(linestyle, "color", "c047b3ff")
    el(linestyle, "width", 3)
    places = {p["id"]: p for p in data["places"]}
    kilometers = haversine(places["peng_shobando"], places["peng_qundo"])
    for p in data["places"]:
        pm = el(doc, "Placemark", id=p["id"])
        el(pm, "name", p["name"])
        body = "<h3>" + html.escape(p["name"]) + "</h3>"
        body += paragraph("含义", p["note"]) + paragraph("点位性质", p["coordinate_method"])
        body += paragraph("彭军耗时", data["timing"])
        if p["kind"] == "candidate":
            body += paragraph("点位差异", data["coordinate_discrepancy"]["note"])
        if p["id"] in ["peng_shobando", "peng_qundo"]:
            body += paragraph("距离对照", f"硕督—倾多代表点直线约{kilometers:.0f} km。" + data["distance_note"])
        el(pm, "description", body + source_links(data))
        view(pm, p["lon"], p["lat"], 70000)
        el(pm, "styleUrl", "#peng_" + p["kind"])
        metadata = el(pm, "ExtendedData")
        for key in ["kind", "coordinate_method", "note"]:
            el(el(metadata, "Data", name=key), "value", p[key])
        el(el(metadata, "Data", name="timing"), "value", "本支线完整耗时未载；经月、迟四日均属陈部或罗部")
        point = el(pm, "Point")
        el(point, "altitudeMode", "clampToGround")
        el(point, "coordinates", f'{p["lon"]:.8f},{p["lat"]:.8f},0')
    direction = data["direction"]
    pm = el(doc, "Placemark", id="peng_north_direction")
    el(pm, "name", direction["name"])
    el(pm, "description", paragraph("示意性质", direction["note"]) + paragraph("距离", data["distance_note"]))
    el(pm, "styleUrl", "#peng_direction")
    geometry = el(pm, "MultiGeometry")
    a, b = places[direction["from"]], places[direction["to"]]
    # Short separated strokes indicate a strategic direction, never an old-road trace.
    for n in range(16):
        coords = []
        for t in [n/16, (n+0.52)/16]:
            coords.append(f'{a["lon"]+(b["lon"]-a["lon"])*t:.8f},{a["lat"]+(b["lat"]-a["lat"])*t:.8f},0')
        line = el(geometry, "LineString")
        el(line, "tessellate", 1)
        el(line, "altitudeMode", "clampToGround")
        el(line, "coordinates", " ".join(coords))
    body = paragraph("部署", data["deployment_vs_event"]) + paragraph("时间", data["timing"])
    card(doc, "peng_schedule", "约期会攻与实际进攻｜彭军全程耗时未载", body + source_links(data))
    units = data["units"]
    body = paragraph("来源口径", units["basis"]) + paragraph("调度", units["coordinator"])
    body += "<ul>" + "".join("<li>" + html.escape(p["person"] + "：" + p["unit"]) + "</li>"
                            for p in units["three_battalions"]) + "</ul>"
    body += paragraph("另一路", units["separate_column"])
    card(doc, "peng_units", "三营构成〔据校注32〕｜彭日升、顾占文、牛运隆", body + source_links(data))
    card(doc, "peng_middle_region", "中波密是地区｜彝贡属其中，倾多为上波北谷", paragraph("区域", places["peng_yigong_context"]["note"]) + source_links(data))
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    (ROOT / (NAME + ".kml")).write_bytes(make(data))
    with zipfile.ZipFile(ROOT / (NAME + ".kmz"), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", make(data, True))
        for kind, color in COLORS.items():
            z.writestr(f"icons/{kind}.png", icon_png(color))
    p = {p["id"]: p for p in data["places"]}
    km = haversine(p["peng_shobando"], p["peng_qundo"])
    with (ROOT / "彭日升北路_地点距离耗时.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["名称", "经度", "纬度", "定位性质", "距离或耗时", "依据和限制"])
        for place in data["places"]:
            writer.writerow([place["name"], place["lon"], place["lat"], place["kind"], "本支线完整耗时未载", place["coordinate_method"]])
        writer.writerow(["硕督—倾多代表点直距", "", "", "球面距离对照", f"{km:.0f} km", data["distance_note"]])
    note = [data["title"], "", data["scope"], data["geographic_sequence"], "", data["deployment_vs_event"],
            data["timing"], "", data["distance_note"], "", units_text(data), ""]
    for place in data["places"]:
        note.extend([place["name"], place["note"], place["coordinate_method"], ""])
    note.extend([data["coordinate_discrepancy"]["note"], "", "来源"])
    note.extend(s["title"] + "\n" + s["url"] for s in data["sources"])
    (ROOT / "彭日升北路入波核对说明.txt").write_text("\n".join(note) + "\n", encoding="utf-8")
    print(f"Created {NAME}.kml/.kmz: 4 points, 1 schematic direction, 3 explanation cards; {km:.0f} km reference")


def units_text(data):
    u = data["units"]
    return u["basis"] + "\n" + u["coordinator"] + "\n" + "；".join(p["person"] + "：" + p["unit"] for p in u["three_battalions"]) + "\n" + u["separate_column"]


if __name__ == "__main__":
    main()
