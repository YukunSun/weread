"""Build the standalone historical-candidate supplement without modifying shared maps."""
from pathlib import Path
import csv
import html
import json
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib
from output_paths import output_path

ROOT = Path(__file__).resolve().parents[1]
NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", NS)
DATA = ROOT / "data/place_checks/甲米青波与纳衣当噶核对.json"
NAME = "艽野尘梦_甲米青波与纳衣当噶候选"


def el(parent, tag, text=None, **attrs):
    node = ET.SubElement(parent, f"{{{NS}}}{tag}", attrs)
    if text is not None:
        node.text = str(text)
    return node


def view(node, lon=94.96, lat=30.0, distance=65000):
    look = el(node, "LookAt")
    for tag, value in [("longitude", lon), ("latitude", lat), ("altitude", 0),
                       ("heading", 0), ("tilt", 0), ("range", distance),
                       ("altitudeMode", "clampToGround")]:
        el(look, tag, value)


def paragraph(label, value):
    return f"<p><b>{html.escape(label)}：</b>{html.escape(value)}</p>"


def source_links(data):
    return "<p>" + "<br/>".join(
        f'<a href="{html.escape(s["url"], quote=True)}">{html.escape(s["title"])}</a>'
        for s in data["sources"]) + "</p>"


def distance_html(data):
    rows = "".join(f'<tr><td>{html.escape(d["from"])} → {html.escape(d["to"])}</td>'
                   f'<td>{d["miles"]:g}</td><td>{d["km"]:.1f}</td></tr>'
                   for d in data["comparison_distances"])
    return (paragraph("距离性质", data["distance_policy"]) +
            '<table border="1" cellpadding="5"><tr><th>1913年报告旧路分段</th>'
            '<th>英里</th><th>km</th></tr>' + rows + "</table>" +
            paragraph("换算", data["miles_conversion"]))


def icon_png(color=(255, 179, 71)):
    size = 32
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            radius2 = (x - 15.5) ** 2 + (y - 15.5) ** 2
            row.extend((*color, 255) if 8**2 <= radius2 <= 12**2 else (0, 0, 0, 0))
        rows.append(bytes(row))
    def chunk(kind, data):
        return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!2I5B", size, size, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b""))


def make(data, bundled):
    root = ET.Element(f"{{{NS}}}kml")
    doc = el(root, "Document", id="jiami_nayi_candidates")
    el(doc, "name", "《艽野尘梦》甲米青波与纳衣当噶｜旧道候选约位")
    el(doc, "open", 1)
    el(doc, "description", paragraph("阅读范围", data["scope"]) + source_links(data))
    view(doc)
    style = el(doc, "Style", id="candidate")
    icon_style = el(style, "IconStyle")
    el(icon_style, "color", "ffffffff" if bundled else "ff47b3ff")
    el(icon_style, "scale", 1)
    el(el(icon_style, "Icon"), "href", "icons/candidate.png" if bundled else
       "https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png")
    label_style = el(style, "LabelStyle")
    el(label_style, "color", "ffffffff")
    el(label_style, "scale", 0.85)
    for place in data["places"]:
        pm = el(doc, "Placemark", id=place["id"])
        el(pm, "name", place["name"])
        info = "<h3>" + html.escape(place["name"]) + "</h3>"
        info += paragraph("点位性质", data["scope"])
        for label, key in [("判断", "strength"), ("耗时与日序", "timing"),
                           ("依据", "evidence"), ("坐标性质", "coordinate_method"),
                           ("定位限制", "limits")]:
            info += paragraph(label, place[key])
        info += distance_html(data) + paragraph("原书撤退里数", data["withdrawal_distance_note"]) + source_links(data)
        el(pm, "description", info)
        view(pm, place["lon"], place["lat"], 45000)
        el(pm, "styleUrl", "#candidate")
        metadata = el(pm, "ExtendedData")
        for key in ["historical_candidate", "strength", "coordinate_method", "timing", "limits"]:
            el(el(metadata, "Data", name=key), "value", place[key])
        el(el(metadata, "Data", name="coordinate_role"), "value", "编辑候选阅读中心；非古址测绘")
        pt = el(pm, "Point")
        el(pt, "altitudeMode", "clampToGround")
        el(pt, "coordinates", f'{place["lon"]:.2f},{place["lat"]:.2f},0')
    for item_id, title, body in [
        ("jiami_nayi_days", "宿营日序｜冬九→纳衣当噶→甲米青波→八浪登", "<ol>" + "".join(
            "<li>" + html.escape(line) + "</li>" for line in data["narrative_sequence"]) + "</ol>"),
        ("jiami_nayi_distance", "距离对照｜1913年旧路12.1／9.7 km；非陈军实走里程", distance_html(data)),
        ("jiami_nayi_modern", "冬九寨／桥与现代东久村｜定位对象仍须区分", paragraph("现代参照限制", data["modern_reference_caution"]))]:
        pm = el(doc, "Placemark", id=item_id)
        el(pm, "name", title)
        el(pm, "description", body + source_links(data))
        view(pm)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    (output_path('maps', NAME + ".kml")).write_bytes(make(data, False))
    with zipfile.ZipFile(output_path('maps', NAME + ".kmz"), "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", make(data, True))
        archive.writestr("icons/candidate.png", icon_png())
    with (output_path('tables', "甲米青波与纳衣当噶_距离耗时.csv")).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["类型", "起点", "终点", "原数", "km", "口径"])
        writer.writerow(["陈书宿营", "冬九", "纳衣当噶", "当日", "未记", "本轮第1日，不能换算小时"])
        writer.writerow(["陈书宿营", "纳衣当噶", "甲米青波", "次日", "未记", "本轮第2日；两处身份均为候选"])
        for distance in data["comparison_distances"]:
            writer.writerow(["1913年调查对照", distance["from"], distance["to"],
                             f'{distance["miles"]:g}英里', f'{distance["km"]:.1f}', data["distance_policy"]])
    note = [data["title"], "", data["scope"], ""]
    for place in data["places"]:
        note.extend([place["name"], place["strength"], place["evidence"], place["coordinate_method"],
                     place["timing"], place["limits"], ""])
    note.extend(["日序", *data["narrative_sequence"], "", "距离口径", data["distance_policy"]])
    note.extend(f'{d["from"]} → {d["to"]}：{d["miles"]:g}英里，约{d["km"]:.1f} km'
                for d in data["comparison_distances"])
    note.extend([data["withdrawal_distance_note"], data["modern_reference_caution"], "", "来源"])
    note.extend(s["title"] + "\n" + s["url"] for s in data["sources"])
    (output_path('docs', "甲米青波与纳衣当噶核对说明.txt")).write_text("\n".join(note) + "\n", encoding="utf-8")
    print(f"Created {NAME}.kml/.kmz: 2 candidate reading centers, 3 non-geometric explanation cards")


if __name__ == "__main__":
    main()
