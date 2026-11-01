"""Build the three unlocated mountain-name cards and modern context references."""
from pathlib import Path
import csv
import html
import json
import xml.etree.ElementTree as ET
import zipfile

from build_jiamiqingbo import NS, el, view, paragraph, source_links, icon_png

ROOT = Path(__file__).resolve().parents[1]
NAME = "艽野尘梦_京中树枝央噶"
DATA = ROOT / "data/place_checks/京中树枝央噶核对.json"
TITLE = "《艽野尘梦》京中—树枝—央噶｜三日越岭，确址待考"


def overview(node):
    view(node, 94.95, 30.0, 130000)


def card(doc, item_id, name, body):
    pm = el(doc, "Placemark", id=item_id)
    el(pm, "name", name)
    el(pm, "description", body)
    overview(pm)
    metadata = el(pm, "ExtendedData")
    el(el(metadata, "Data", name="geometry_role"), "value", "无几何说明卡；未定位旧山名或行程解释")
    return pm


def make(data, bundled=False):
    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}kml")
    doc = el(root, "Document", id="three_mountains_unlocated")
    el(doc, "name", TITLE)
    el(doc, "open", 1)
    el(doc, "description", paragraph("范围", data["scope"]) + paragraph("正文顺序", data["sequence"]) + source_links(data))
    overview(doc)
    style = el(doc, "Style", id="three_mountains_context")
    iconstyle = el(style, "IconStyle")
    el(iconstyle, "color", "ffffffff" if bundled else "ffd0c6be")
    el(iconstyle, "scale", 0.85)
    el(el(iconstyle, "Icon"), "href", "icons/context.png" if bundled else
       "https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png")
    labelstyle = el(style, "LabelStyle")
    el(labelstyle, "color", "ffffffff")
    el(labelstyle, "scale", 0.85)
    for mountain in data["mountains"]:
        body = "<h3>" + html.escape(mountain["name"]) + "</h3>"
        body += paragraph("地望", mountain["note"]) + paragraph("时间口径", mountain["timing"])
        body += paragraph("距离", data["distance_policy"]) + paragraph("标识性质", "本条为无几何说明卡，没有山峰、山口或营地坐标。")
        card(doc, mountain["id"], mountain["name"], body + source_links(data))
    body = paragraph("顺序", data["sequence"])
    body += "<ul>" + "".join("<li>" + html.escape(row["role"] + "：" + row["time"] + "。" + row["note"]) + "</li>"
                              for row in data["time_entries"][3:]) + "</ul>"
    body += paragraph("日数解释", "三山整体三日不机械分配每山一天；商旅六日是另一通行情境；收葬半日停留与下山后半日行军分别保留，不换算精确小时或虚构逐日宿营点。")
    body += paragraph("距离", data["distance_policy"])
    comparison = data["historical_distance_comparison"]
    body += paragraph("1913年反向旧路测程对照", comparison["note"]) + paragraph("另一调查队日期", comparison["timing"])
    card(doc, "three_mountains_sequence_time", "八浪登→京中→树枝→央噶→汤买｜三日、六日与两处半日分读", body + source_links(data))
    body = paragraph("现代对应", data["modern_name_status"]) + paragraph("旧报告对照", data["historical_comparison"])
    body += paragraph("海拔口径", data["elevation_policy"]) + paragraph("地图限制", data["scope"])
    card(doc, "three_mountains_evidence_limits", "定位证据限制｜约4000m为组概述；旧山名不强行套点", body + source_links(data))
    for place in data["modern_references"]:
        pm = el(doc, "Placemark", id=place["id"])
        el(pm, "name", place["name"])
        el(pm, "description", paragraph("参照性质", place["note"]) + paragraph("坐标依据", place["source_coordinate"]) +
           paragraph("距离", data["distance_policy"]) + source_links(data))
        view(pm, place["lon"], place["lat"], 70000)
        el(pm, "styleUrl", "#three_mountains_context")
        metadata = el(pm, "ExtendedData")
        el(el(metadata, "Data", name="coordinate_role"), "value", "现代地区参照；不是旧山名、营地、寨址或旧桥址")
        point = el(pm, "Point")
        el(point, "altitudeMode", "clampToGround")
        el(point, "coordinates", f'{place["lon"]:.8f},{place["lat"]:.8f},0')
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    (ROOT / (NAME + ".kml")).write_bytes(make(data))
    with zipfile.ZipFile(ROOT / (NAME + ".kmz"), "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", make(data, True))
        archive.writestr("icons/context.png", icon_png((190, 198, 208)))
    with (ROOT / "京中树枝央噶_距离耗时.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["口径", "起点或地点", "终点或事项", "耗时", "km", "依据和限制"])
        for row in data["time_entries"]:
            writer.writerow([row["role"], row["from"], row["to"], row["time"], "", "原文公里数未载；" + row["note"]])
        comparison = data["historical_distance_comparison"]
        writer.writerow(["1913年另一调查队反向旧路测程对照", comparison["from"], comparison["to"], comparison["timing"],
                         f'{comparison["km"]:.1f}', comparison["note"]])
    note = [TITLE, "", data["scope"], "", data["sequence"], ""]
    for mountain in data["mountains"]:
        note.extend([mountain["name"], mountain["note"], mountain["timing"], ""])
    note.extend(["时间分读"])
    note.extend(row["role"] + "：" + row["time"] + "。" + row["note"] for row in data["time_entries"][3:])
    note.extend(["", "距离", data["distance_policy"], comparison["note"], comparison["timing"], "", "定位证据与海拔", data["historical_comparison"], data["modern_name_status"], data["elevation_policy"], "", "现代地区参照"])
    for place in data["modern_references"]:
        note.extend([place["name"], place["source_coordinate"], place["note"], ""])
    note.append("来源")
    note.extend(source["title"] + "\n" + source["url"] for source in data["sources"])
    (ROOT / "京中树枝央噶核对说明.txt").write_text("\n".join(note) + "\n", encoding="utf-8")
    print(f"Created {NAME}.kml/.kmz: 2 modern reference points, 5 geometry-free cards, no route or area")


if __name__ == "__main__":
    main()
