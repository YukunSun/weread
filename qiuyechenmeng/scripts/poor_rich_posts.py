"""Source-labelled, deliberately approximate poor/rich post-road comparison."""
from pathlib import Path
import csv
import html
import json
import math
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/postroads/穷富八站.json'
KML = 'http://www.opengis.net/kml/2.2'
NAME = '艽野尘梦_穷八站与富八站'
LIMIT = ('虚线只连接可定位的代表锚点，表示大致方向，不是古道轨迹、现代公路或完整驿站段。'
         '锚点直距不是历史实走里程；不据站数、旧里数或直距推算行走日数。'
         '凝多塘位置及穷富分界未定，未把直线上的任何位置认定为凝多塘。')


def load():
    cfg = json.loads(DATA.read_text(encoding='utf-8'))
    if isinstance(cfg['sources'], dict):
        cfg['sources'] = [dict(source, id=sid) for sid, source in cfg['sources'].items()]
    places = {p['id']: p for p in cfg['places']}
    if len(places) != len(cfg['places']):
        raise ValueError('穷富八站地名 ID 重复')
    sources = {s['id']: s for s in cfg['sources']}
    for p in places.values():
        for sid in p.get('sources', []):
            if sid not in sources:
                raise ValueError(f'穷富八站地名 {p["id"]} 引用了未知来源 {sid}')
    for route in cfg['routes']:
        for pid in route['ids']:
            if pid not in places:
                raise ValueError(f'穷富八站路线 {route["id"]} 引用了未知地点 {pid}')
    return cfg, places, sources


def located(place):
    return all(isinstance(place.get(k), (int, float)) and
               math.isfinite(place[k]) for k in ('lon', 'lat'))


def km(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians,
                               (a['lon'], a['lat'], b['lon'], b['lat']))
    h = (math.sin((lat2 - lat1) / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(h)))


def prose(value):
    """Keep supplied interpretation text readable without treating it as HTML."""
    if value is None:
        return ''
    if isinstance(value, dict):
        return '\n'.join(f'{k}：{prose(v)}' for k, v in value.items())
    if isinstance(value, list):
        return '\n'.join(prose(v) for v in value)
    return str(value)


def paragraphs(value):
    return ''.join('<p>' + html.escape(line) + '</p>'
                   for line in prose(value).splitlines() if line.strip())


def source_html(sources):
    body = '<h3>依据与来源</h3>'
    for source in sources:
        body += ('<p><a href="' + html.escape(source['url'], quote=True) + '">' +
                 html.escape(source['title']) + '</a><br/>' +
                 html.escape(prose(source.get('supports', ''))) + '</p>')
    return body


def overview_html(cfg):
    body = '<h3>校注二十一：穷八站与富八站</h3>'
    body += '<p><b>核对日期：</b>' + html.escape(cfg['checked_at']) + '</p>'
    body += '<blockquote>' + html.escape(prose(cfg['quote'])).replace('\n', '<br/>') + '</blockquote>'
    body += paragraphs(cfg['interpretation'])
    body += '<h3>清代《西藏记》八站顺序对读</h3>'
    for i, station in enumerate(cfg['poor_station_order'], 1):
        body += ('<p><b>' + str(i) + ' ' + html.escape(station['name']) + '</b><br/>' +
                 html.escape(prose(station.get('note', ''))) + '</p>')
    body += ('<p>以上为文字顺序对读，不表示八个旧站已全部定位。'
             '富八站保留校注的概称，不用今村名或其他时期站表硬凑八站。</p>')
    body += paragraphs(LIMIT)
    return body + source_html(cfg['sources'])


def _styles(parent, el, kcolor, bundled, routes):
    styles = []
    for sid, color, uncertain in (('point', '#8ad4ff', False),
                                   ('uncertain', '#ffc66d', True)):
        style = el(parent, 'Style', id='poor_rich_' + sid)
        styles.append(style)
        icon_style = el(style, 'IconStyle')
        el(icon_style, 'color', 'ffffffff' if bundled else kcolor(color))
        el(icon_style, 'scale', 1.15 if uncertain else 1.0)
        icon = el(icon_style, 'Icon')
        href = ('icons/post_' + sid + '.png' if bundled else
                'https://maps.google.com/mapfiles/kml/shapes/' +
                ('open-diamond.png' if uncertain else 'placemark_circle.png'))
        el(icon, 'href', href)
        label = el(style, 'LabelStyle')
        el(label, 'color', 'ffffffff')
        el(label, 'scale', 0.95)
    for route in routes:
        style = el(parent, 'Style', id='poor_rich_line_' + route['id'])
        styles.append(style)
        line = el(style, 'LineStyle')
        el(line, 'color', kcolor(route['color'], 'e0'))
        el(line, 'width', 4)
    # Feature properties precede child Features, even when appended to an existing Folder.
    feature_tags = {f'{{{KML}}}{tag}' for tag in ('Folder', 'Document', 'Placemark', 'NetworkLink')}
    for style in styles:
        parent.remove(style)
    insertion = next((i for i, child in enumerate(parent) if child.tag in feature_tags), len(parent))
    for style in styles:
        parent.insert(insertion, style)
        insertion += 1


def _view_places(parent, places, view):
    known = [p for p in places if located(p)]
    if not known:
        return
    lon = (min(p['lon'] for p in known) + max(p['lon'] for p in known)) / 2
    lat = (min(p['lat'] for p in known) + max(p['lat'] for p in known)) / 2
    center = {'lon': lon, 'lat': lat}
    distance = max(90000, max(km(center, p) for p in known) * 2400)
    view(parent, lon, lat, round(distance))


def add_poor_rich_posts(parent, el, view, kcolor, bundled=False,
                       include_existing=False, reuse_ids=None):
    cfg, places, sources = load()
    _styles(parent, el, kcolor, bundled, cfg['routes'])
    top = el(parent, 'Folder', id='poor_rich_posts')
    el(top, 'name', '11H 穷八站与富八站｜锚点方向示意，凝多未定位')
    el(top, 'open', 1)
    el(top, 'visibility', 1)
    el(top, 'description', overview_html(cfg))
    _view_places(top, cfg['places'], view)
    overview = el(top, 'Placemark', id='poor_rich_overview')
    el(overview, 'name', '校注、八站文字顺序与定位限制〔点击阅读〕')
    el(overview, 'description', overview_html(cfg))
    point_folder = el(top, 'Folder', id='poor_rich_places')
    el(point_folder, 'name', '地点｜甲贡为候选，凝多无坐标' +
       ('，含全部已知锚点' if include_existing else '，已有地点复用主图'))
    el(point_folder, 'open', 1)
    known_folder = None
    if include_existing:
        known_folder = el(point_folder, 'Folder', id='poor_rich_known_anchors')
        el(known_folder, 'name', '已有地区锚点｜叠加旧图时可整组隐藏')
        el(known_folder, 'open', 0)
    for place in cfg['places']:
        has_coordinate = located(place)
        reuse = bool(place.get('existing')) and not include_existing
        if reuse_ids is not None:
            reuse = place['id'] in reuse_ids
        suffix = '【未定位，无几何】' if not has_coordinate else '【复用主图原点】' if reuse else ''
        target = known_folder if known_folder is not None and place.get('existing') else point_folder
        pm = el(target, 'Placemark', id='poor_rich_place_' + place['id'])
        el(pm, 'name', place['name'] + suffix)
        body = ('<h3>' + html.escape(place['name']) + '</h3><p><b>今名／定位对象：</b>' +
                html.escape(prose(place.get('modern', ''))) + '<br/><b>定位性质：</b>' +
                html.escape(place['certainty']) + '</p>')
        body += paragraphs(place['note'])
        if has_coordinate:
            body += (f'<p>区域／代表点坐标：{place["lon"]:.4f}°E，{place["lat"]:.4f}°N。'
                     '小数位是存储格式，不代表旧驿站或营地已精确定位。</p>')
        else:
            body += '<p>此条不含坐标和地图几何，不在两锚点之间插值造点。</p>'
        if reuse:
            body += '<p>本图层复用完整阅读地图原有地点；此条仅为对读说明，点击主图原点查看位置。</p>'
        body += paragraphs(LIMIT)
        body += source_html([sources[sid] for sid in place.get('sources', [])])
        el(pm, 'description', body)
        if has_coordinate and not reuse:
            uncertain = (not place.get('existing') or
                         any(word in place['certainty'] for word in ('推定', '候选', '待考')))
            el(pm, 'visibility', 1)
            el(pm, 'styleUrl', '#poor_rich_' + ('uncertain' if uncertain else 'point'))
            view(pm, place['lon'], place['lat'], 85000)
            point = el(pm, 'Point')
            el(point, 'altitudeMode', 'clampToGround')
            el(point, 'coordinates', f'{place["lon"]},{place["lat"]},0')
    routes_folder = el(top, 'Folder', id='poor_rich_routes')
    el(routes_folder, 'name', '三段方向示意｜灰色过渡带不确定穷富分界')
    el(routes_folder, 'open', 1)
    for route in cfg['routes']:
        sequence = [places[pid] for pid in route['ids']]
        anchors = [p for p in sequence if located(p)]
        body = '<h3>' + html.escape(route['name']) + '</h3>' + paragraphs(route['note'])
        body += '<p><b>文字顺序：</b>' + ' → '.join(html.escape(p['name']) for p in sequence) + '</p>'
        if len(anchors) >= 2:
            body += '<h3>可定位锚点的直距</h3>'
            for a, b in zip(anchors, anchors[1:]):
                body += ('<p>' + html.escape(a['name']) + ' → ' + html.escape(b['name']) +
                         f'：锚点直距约 {km(a, b):.0f} km。</p>')
        body += paragraphs(LIMIT)
        body += source_html(cfg['sources'])
        pm = el(routes_folder, 'Placemark', id='poor_rich_route_' + route['id'])
        el(pm, 'name', route['name'])
        el(pm, 'description', body)
        if len(anchors) < 2:
            continue
        _view_places(pm, anchors, view)
        el(pm, 'visibility', 1)
        el(pm, 'styleUrl', '#poor_rich_line_' + route['id'])
        geometry = el(pm, 'MultiGeometry')
        for a, b in zip(anchors, anchors[1:]):
            count = max(2, math.ceil(km(a, b) / 6))
            for i in range(count):
                line = el(geometry, 'LineString')
                el(line, 'tessellate', 1)
                el(line, 'altitudeMode', 'clampToGround')
                ends = (i / count, (i + 0.52) / count)
                el(line, 'coordinates', ' '.join(
                    f'{a["lon"] + (b["lon"] - a["lon"]) * t:.6f},'
                    f'{a["lat"] + (b["lat"] - a["lat"]) * t:.6f},0' for t in ends))
    return cfg


def _el(parent, tag, text=None, **attrs):
    node = ET.SubElement(parent, f'{{{KML}}}{tag}', attrs)
    if text is not None:
        node.text = str(text)
    return node


def _view(parent, lon, lat, distance=90000):
    look = _el(parent, 'LookAt')
    for tag, value in (('longitude', lon), ('latitude', lat), ('altitude', 0),
                       ('heading', 0), ('tilt', 0), ('range', distance),
                       ('altitudeMode', 'clampToGround')):
        _el(look, tag, value)


def _kcolor(rgb, alpha='ff'):
    rgb = rgb.lstrip('#')
    return alpha + rgb[4:6] + rgb[2:4] + rgb[:2]


def _standalone(bundled=False):
    ET.register_namespace('', KML)
    root = ET.Element(f'{{{KML}}}kml')
    doc = _el(root, 'Document', id='poor_rich_supplement')
    _el(doc, 'name', '《艽野尘梦》穷八站与富八站｜大致方位')
    _el(doc, 'open', 1)
    _el(doc, 'description', '独立补充图含甲贡候选、拉里、江达与拉萨锚点及边坝辖境背景点，凝多仅作无坐标文字条目。'
        '与新版完整阅读地图的11H层二选一显示；叠加旧图时可隐藏重复的已有地点。' + LIMIT)
    add_poor_rich_posts(doc, _el, _view, _kcolor, bundled, True)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_poor_rich_files():
    cfg, _, sources = load()
    # The main map is written before post-road indexes. Reuse its established icons.
    icon_paths = ('icons/post_point.png', 'icons/post_uncertain.png')
    with zipfile.ZipFile(ROOT / '艽野尘梦_阅读地图.kmz') as archive:
        icons = {name: archive.read(name) for name in icon_paths}
    (ROOT / (NAME + '.kml')).write_bytes(_standalone())
    with zipfile.ZipFile(ROOT / (NAME + '.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', _standalone(True))
        for name, data in icons.items():
            archive.writestr(name, data)
    with (ROOT / '穷富八站_地名坐标.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['id', '地名', '现代定位对象', '经度', '纬度', '定位性质',
                         '复用已有地点', '说明', '来源标题', '来源链接'])
        for place in cfg['places']:
            refs = [sources[sid] for sid in place.get('sources', [])]
            writer.writerow([place['id'], place['name'], prose(place.get('modern', '')),
                             place['lon'] if located(place) else '',
                             place['lat'] if located(place) else '', place['certainty'],
                             '是' if place.get('existing') else '否', prose(place['note']),
                             '；'.join(s['title'] for s in refs), '；'.join(s['url'] for s in refs)])
    guide = ('《艽野尘梦》穷八站与富八站\n核对日期：' + cfg['checked_at'] + '\n\n'
             '校注二十一\n' + prose(cfg['quote']) + '\n\n' + prose(cfg['interpretation']) + '\n\n'
             '11H以三段断续虚线表示方向：甲贡候选至拉里；拉里至江达为灰色过渡带；江达至拉萨。'
             '凝多位置与穷富分界未定，灰色过渡带不归为已落实的穷段或富段。\n' + LIMIT + '\n\n'
             '完整阅读地图11H复用拉里、江达、拉萨原有点，只为甲贡候选增加橙色空心点；'
             '已有地点的对读条目不重复放点。凝多始终无坐标、无几何。\n'
             '独立“' + NAME + '.kmz”含所有可定位锚点，可单独打开。'
             '与新版完整图11H二选一显示；叠加旧图时隐藏重复的原有点，避免重复标注。\n\n'
             '清代《西藏记》八站顺序对读\n')
    for i, station in enumerate(cfg['poor_station_order'], 1):
        guide += f'{i}. {station["name"]}：{prose(station.get("note", ""))}\n'
    guide += '\n此顺序不表示各旧站均已落点；富八站不以今村名或其他时期站表硬凑八个地点。\n\n地名与定位\n'
    for place in cfg['places']:
        coordinate = f'{place["lon"]}°E，{place["lat"]}°N' if located(place) else '无坐标，不造点'
        guide += (place['name'] + '｜' + place['certainty'] + '｜' + coordinate + '\n' +
                  prose(place['note']) + '\n\n')
    guide += '来源\n' + '\n\n'.join(s['title'] + '\n' + prose(s.get('supports', '')) +
                                    '\n' + s['url'] for s in cfg['sources']) + '\n'
    (ROOT / '穷富八站说明.txt').write_text(guide, encoding='utf-8')


if __name__ == '__main__':
    write_poor_rich_files()
