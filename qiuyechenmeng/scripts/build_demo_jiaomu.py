"""Build the chapter-seven Demo to Jiaomu two-day reading-map supplement."""
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
DATA = ROOT / "data/place_checks/德摩至脚木宗两日核对.json"
NAME = "艽野尘梦_德摩至脚木宗两日"


def distance_km(places):
    a, b = places
    p, q = math.radians(a["lat"]), math.radians(b["lat"])
    d = math.radians(b["lon"] - a["lon"])
    h = math.sin((q - p) / 2) ** 2 + math.cos(p) * math.cos(q) * math.sin(d / 2) ** 2
    return 12742.0176 * math.asin(math.sqrt(min(1, max(0, h))))


def overview(node, data):
    camera = data["look_at"]
    view(node, camera["lon"], camera["lat"], camera["range_m"])


def details(data):
    return (paragraph("正文行程", data["sequence"])
            + paragraph("耗时口径", data["duration_note"])
            + paragraph("代表点直距", f'{distance_km(data["places"]):.1f} km')
            + paragraph("距离口径", data["distance_note"])
            + paragraph("示意限制", data["direction_note"]))


def make(data, bundled=False):
    root = ET.Element(f"{{{NS}}}kml")
    doc = el(root, "Document", id="demo_jiaomu_chapter7")
    el(doc, "name", data["title"])
    el(doc, "open", 1)
    el(doc, "description", paragraph("阅读范围", data["scope"]) + details(data) + source_links(data))
    overview(doc, data)
    for kind, color in [("reference", (155, 171, 183)), ("candidate", (255, 179, 71))]:
        style = el(doc, "Style", id="demo_jiaomu_" + kind)
        icon = el(style, "IconStyle")
        el(icon, "color", "ffffffff" if bundled else "ff" + "".join(f"{c:02x}" for c in reversed(color)))
        el(icon, "scale", 0.9)
        el(el(icon, "Icon"), "href", f"icons/{kind}.png" if bundled else
           "https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png")
        label = el(style, "LabelStyle")
        el(label, "scale", 0.85)
    style = el(doc, "Style", id="demo_jiaomu_direction_style")
    line_style = el(style, "LineStyle")
    el(line_style, "color", "d047b3ff")
    el(line_style, "width", 3)
    for place in data["places"]:
        pm = el(doc, "Placemark", id=place["id"])
        el(pm, "name", place["name"])
        el(pm, "visibility", int(place["visible"]))
        body = paragraph("地区身份", place["note"]) + paragraph("坐标性质", place["coordinate_method"])
        body += paragraph("本段时间", place["timing"]) + details(data) + source_links(data)
        el(pm, "description", body)
        overview(pm, data)
        el(pm, "styleUrl", "#demo_jiaomu_" + place["kind"])
        pt = el(pm, "Point")
        el(pt, "altitudeMode", "clampToGround")
        el(pt, "coordinates", f'{place["lon"]:.8f},{place["lat"]:.8f},0')
    pm = el(doc, "Placemark", id="demo_jiaomu_two_days_direction")
    el(pm, "name", f'德摩→脚木宗候选｜行2日；代表点直距{distance_km(data["places"]):.1f} km〔方向示意〕')
    el(pm, "description", details(data) + paragraph("点位显示", data["point_visibility_note"]) + source_links(data))
    overview(pm, data)
    el(pm, "styleUrl", "#demo_jiaomu_direction_style")
    multi = el(pm, "MultiGeometry")
    a, b = data["places"]
    for i in range(12):
        line = el(multi, "LineString")
        el(line, "tessellate", 1)
        el(line, "altitudeMode", "clampToGround")
        coords = []
        for t in [i / 12, (i + 0.55) / 12]:
            lon = a["lon"] + (b["lon"] - a["lon"]) * t
            lat = a["lat"] + (b["lat"] - a["lat"]) * t
            coords.append(f"{lon:.8f},{lat:.8f},0")
        el(line, "coordinates", " ".join(coords))
    for item in data["cards"]:
        pm = el(doc, "Placemark", id=item["id"])
        el(pm, "name", item["name"])
        body = "".join("<p>" + html.escape(s) + "</p>" for s in item["paragraphs"])
        el(pm, "description", body + details(data) + source_links(data))
        overview(pm, data)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    (output_path('maps', NAME + ".kml")).write_bytes(make(data))
    with zipfile.ZipFile(output_path('maps', NAME + ".kmz"), "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", make(data, True))
        archive.writestr("icons/reference.png", icon_png((155, 171, 183)))
        archive.writestr("icons/candidate.png", icon_png((255, 179, 71)))
    with (output_path('tables', "德摩至脚木宗_距离耗时.csv")).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["口径", "起点", "终点或事项", "耗时", "km", "限制"])
        writer.writerow(["正文行军", "德摩", "脚木宗", "2日", "未载", data["duration_note"]])
        writer.writerow(["正文留宿", "脚木宗到达当晚", "次日晨早出发", "宿一夜", "", "不另加整一日；前次驻半月另计。"])
        writer.writerow(["现代代表点对照", "现德木寺地区参照", "觉木／Qomo候选地区", "不适用", f'{distance_km(data["places"]):.1f}', data["distance_note"]])
    note = [data["title"], "", data["quote"], data["scope"], data["sequence"], "", data["duration_note"], data["distance_note"], data["direction_note"], data["point_visibility_note"], ""]
    for place in data["places"]:
        note.extend([place["name"], place["note"], place["coordinate_method"], place["timing"], ""])
    for item in data["cards"]:
        note.extend([item["name"], *item["paragraphs"], ""])
    note.append("来源与限度")
    for source in data["sources"]:
        note.extend([source["title"], source["supports"], source["url"], ""])
    (output_path('docs', "德摩至脚木宗两日核对说明.txt")).write_text("\n".join(note).rstrip() + "\n", encoding="utf-8")
    print(f"Created {NAME}.kml/.kmz: 2 hidden reference points, 1 direction (12 strokes), 2 cards; {distance_km(data['places']):.1f} km straight comparison, 2 days from text")


if __name__ == "__main__":
    main()
