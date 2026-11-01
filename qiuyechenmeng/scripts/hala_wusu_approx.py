"""A visible regional reading reference for the unlocated historical Hala Wusu stop."""
from pathlib import Path
import html
import json
import xml.etree.ElementTree as ET
import zipfile

from build_jiamiqingbo import el as standalone_el, view as standalone_view, icon_png

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'
NAME = '艽野尘梦_哈喇乌苏大概位置'
ICON_PATH = 'icons/hala_wusu_approx.png'
STYLE_ID = 'hala_wusu_approx_style'


def load():
    return json.loads((ROOT/'data/place_checks/哈喇乌苏大概位置.json').read_text(encoding='utf-8'))


def reference_icon():
    return icon_png((255, 153, 51))


def point_html(cfg):
    body = '<h3>'+html.escape(cfg['point']['name'])+'</h3>'
    for text in [cfg['summary'], cfg['coordinate_note'], cfg['route_note']]:
        body += '<p>'+html.escape(text)+'</p>'
    body += '<p><b>大概地区参照：</b>93.10°E，31.54°N。</p>'
    return body+'<p>'+'<br/>'.join(
        '<a href="'+html.escape(s['url'], quote=True)+'">'+html.escape(s['title'])+'</a>'
        for s in cfg['sources'])+'</p>'


def add_hala_wusu_approx(doc, el, view):
    cfg = load()
    point = cfg['point']
    folder = el(doc, 'Folder', id='hala_wusu_approx_context')
    el(folder, 'name', cfg['layer_name'])
    el(folder, 'visibility', 1)
    el(folder, 'open', 1)
    el(folder, 'description', cfg['summary'])
    view(folder, point['lon'], point['lat'], cfg['camera_range_m'])
    style = el(folder, 'Style', id=STYLE_ID)
    iconstyle = el(style, 'IconStyle')
    el(iconstyle, 'color', 'ffffffff')
    el(iconstyle, 'scale', 1.2)
    el(el(iconstyle, 'Icon'), 'href', ICON_PATH)
    labelstyle = el(style, 'LabelStyle')
    el(labelstyle, 'color', 'ffffffff')
    el(labelstyle, 'scale', 0.95)
    placemark = el(folder, 'Placemark', id=point['id'])
    el(placemark, 'name', point['name'])
    el(placemark, 'visibility', 1)
    el(placemark, 'description', point_html(cfg))
    view(placemark, point['lon'], point['lat'], cfg['camera_range_m'])
    el(placemark, 'styleUrl', '#'+STYLE_ID)
    metadata = el(placemark, 'ExtendedData')
    for name, value in [('coordinate_role', point['coordinate_role']),
                        ('historical_identity', '阿克河谷、台站与宿处具体对应待考'),
                        ('coordinate_method', cfg['coordinate_note'])]:
        el(el(metadata, 'Data', name=name), 'value', value)
    geometry = el(placemark, 'Point')
    el(geometry, 'altitudeMode', 'clampToGround')
    el(geometry, 'coordinates', f'{point["lon"]:.2f},{point["lat"]:.2f},0')
    return folder


def make_supplement():
    cfg = load()
    root = ET.Element('{'+KML+'}kml')
    doc = standalone_el(root, 'Document', id='hala_wusu_approx_supplement')
    standalone_el(doc, 'name', '《艽野尘梦》'+cfg['title'])
    standalone_el(doc, 'open', 1)
    standalone_el(doc, 'description', cfg['summary'])
    standalone_view(doc, cfg['point']['lon'], cfg['point']['lat'], cfg['camera_range_m'])
    add_hala_wusu_approx(doc, standalone_el, standalone_view)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_index():
    cfg = load()
    lines = [cfg['title'], '核对日期：'+cfg['checked_at'], '', cfg['point']['name'],
             cfg['summary'], cfg['coordinate_note'], cfg['route_note'],
             '大概地区参照坐标：93.10°E，31.54°N；镜头200km。', '',
             '完整阅读地图和独立单点包含同一个默认显示的橙色空心地区参照点，选择一份显示。'
             '本补层只有1个Point，无路线、范围或边界几何。原校注44五卡层无需重复导入。', '',
             '来源与限度']
    for source in cfg['sources']:
        lines += [source['title'], source['url'], source['supports'], '']
    if cfg.get('google_earth_import'):
        record = cfg['google_earth_import']
        lines += ['Google Earth核验', record['note']]
        if record.get('screenshot'):
            lines += ['核验截图：'+record['screenshot']]
    note = '\n'.join(lines).rstrip()+'\n'
    (ROOT/'哈喇乌苏大概位置说明.txt').write_text(note, encoding='utf-8')
    return note


def write_hala_wusu_approx_outputs():
    ET.register_namespace('', KML)
    raw = make_supplement()
    (ROOT/(NAME+'.kml')).write_bytes(raw)
    icon = reference_icon()
    (ROOT/ICON_PATH).parent.mkdir(exist_ok=True)
    (ROOT/ICON_PATH).write_bytes(icon)
    with zipfile.ZipFile(ROOT/(NAME+'.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', raw)
        archive.writestr(ICON_PATH, icon)
    return write_index()


if __name__ == '__main__':
    write_hala_wusu_approx_outputs()
