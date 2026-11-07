"""Build geometry-free reading cards for Renjinbang and Katuo."""
from pathlib import Path
import csv
import html
import json
import xml.etree.ElementTree as ET
import zipfile

from build_jiamiqingbo import NS, el, paragraph, source_links, view
from output_paths import output_path

ROOT = Path(__file__).resolve().parents[1]
NAME = "艽野尘梦_仁进邦与卡拖"
DATA = ROOT / "data/place_checks/仁进邦与卡拖核对.json"


def overview(node, data):
    camera = data["look_at"]
    view(node, camera["lon"], camera["lat"], camera["range_m"])


def make(data):
    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}kml")
    doc = el(root, "Document", id="renjinbang_katuo_unlocated")
    el(doc, "name", data["title"])
    el(doc, "open", 1)
    el(doc, "description", paragraph("范围", data["scope"]) +
       paragraph("行动者与先后", data["sequence"]) + source_links(data))
    overview(doc, data)
    for item in data["cards"]:
        pm = el(doc, "Placemark", id=item["id"])
        el(pm, "name", item["name"])
        body = "<h3>" + html.escape(item["name"]) + "</h3>"
        body += "".join("<p>" + html.escape(line) + "</p>" for line in item["paragraphs"])
        body += paragraph("镜头与定位", data["look_at"]["note"]) + source_links(data)
        el(pm, "description", body)
        overview(pm, data)
        metadata = el(pm, "ExtendedData")
        el(el(metadata, "Data", name="geometry_role"), "value", "无几何说明卡；现代确址待考")
        el(el(metadata, "Data", name="narrative_actor"), "value", "王孚招降林噶后返回；不当陈本人经仁进邦的轨迹")
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    payload = make(data)
    (output_path('maps', NAME + ".kml")).write_bytes(payload)
    with zipfile.ZipFile(output_path('maps', NAME + ".kmz"), "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", payload)
    with (output_path('tables', "仁进邦与卡拖_距离耗时.csv")).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["口径", "起点或地点", "终点或事项", "耗时或日序", "km", "依据和限制"])
        for row in data["time_entries"]:
            writer.writerow([row["type"], row["from"], row["to"], row["time"], "", row["note"]])
    note = [data["title"], "", data["scope"], "", data["sequence"], ""]
    for item in data["cards"]:
        note.extend([item["name"], *item["paragraphs"], ""])
    note.extend(["镜头与定位", data["look_at"]["note"], "", "时间与距离口径"])
    note.extend(row["type"] + "：" + row["from"] + "→" + row["to"] + "；" +
                row["time"] + "；km未载。" + row["note"] for row in data["time_entries"])
    note.extend(["", "来源与限度"])
    for source in data["sources"]:
        note.extend([source["title"], source["supports"], source["url"], ""])
    (output_path('docs', "仁进邦与卡拖核对说明.txt")).write_text("\n".join(note).rstrip() + "\n", encoding="utf-8")
    print(f"Created {NAME}.kml/.kmz: {len(data['cards'])} geometry-free cards, no point, route or area")


if __name__ == "__main__":
    main()
