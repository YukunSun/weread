"""Chapter 4 place candidates, kept separate from confirmed itinerary geometry."""
from pathlib import Path
import csv
import html
import json

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / 'data/place_checks/工布安抚三地核对.json'
LAYER_NAME = '15 工布安抚｜曲巴、增巴、脚木宗'


def load():
    return json.loads(DATA_FILE.read_text(encoding='utf-8'))


def unlocated_entries():
    return [
        ('第4章', '曲巴〔古今对应待考〕', '15层保留无坐标文字条目；现代对应、相邻段方向和里程未定，不据列举顺序插值造点。'),
        ('第4章', '增巴〔两处现代同名候选，书中对应未定〕', '15层并列百巴镇、米瑞乡两个增巴村参照点；尚未选定书中对应，不表示作者到过两处。'),
        ('第3—4章', '脚木宗古今对应、旧驻地及窝冗噶伽', '15层已补觉木／Qomo地区作脚木宗候选，与校注27“牙丕附近”说的差异仍待核；候选不共用牙披坐标。脚木宗的具体营地、寺院及窝冗噶伽仍待考。'),
    ]


def sources_html(config, source_ids):
    return '<br/>'.join(
        '<a href="' + html.escape(config['sources'][key]['url'], quote=True) + '">' +
        html.escape(config['sources'][key]['title']) + '</a>'
        for key in source_ids
    )


def overview_html(config):
    body = '<h3>工布安抚：曲巴、增巴、脚木宗</h3>'
    body += '<p><b>原句：</b>' + html.escape(config['quote']) + '</p>'
    for key in ['scope', 'route_note', 'timing_note', 'coordinate_note']:
        body += '<p>' + html.escape(config[key]) + '</p>'
    body += '<p>橙色空心点为候选；牙披为蓝色驻地背景参照，默认隐藏。曲巴没有几何坐标。</p>'
    body += '<p>新版完整阅读地图已包含15层；已有云端旧图可单独叠加“艽野尘梦_工布安抚三地.kmz”，两种版本选择一份显示。</p>'
    if config.get('google_earth_import'):
        body += '<p><b>云端核验：</b>' + html.escape(config['google_earth_import']['note']) + '</p>'
    return body + '<p>' + sources_html(config, ['text', 'annotation27', 'knab', 'qomo_research', 'two_zengba']) + '</p>'


def place_html(config, place):
    body = '<h3>' + html.escape(place['label']) + '</h3>'
    body += '<p><b>书中名：</b>' + html.escape(place['book_name'])
    body += '<br/><b>现代参照：</b>' + html.escape(place['modern'])
    body += '<br/><b>定位性质：</b>' + html.escape(place['certainty']) + '</p>'
    body += '<p>' + html.escape(place['note']) + '</p>'
    body += '<p><b>耗时：</b>' + html.escape(place['timing']) + '</p>'
    if place['lon'] is None:
        body += '<p>本条无坐标，仅在图层列表保留说明。</p>'
    else:
        body += f'<p><b>地区参照坐标：</b>{place["lon"]:.5f}°E，{place["lat"]:.5f}°N。' + html.escape(config['coordinate_note']) + '</p>'
    return body + '<p>' + sources_html(config, place['source_ids']) + '</p>'


def add_gongbu_pacification(doc, el, view, kcolor, bundled=False):
    config = load()
    styles = []
    for sid, color, hollow in [('gongbu_candidate', '#ffb347', True), ('gongbu_reference', '#89d8ff', False)]:
        style = el(doc, 'Style', id=sid)
        iconstyle = el(style, 'IconStyle')
        el(iconstyle, 'color', 'ffffffff' if bundled else kcolor(color))
        el(iconstyle, 'scale', 1.1 if hollow else 0.9)
        icon = el(iconstyle, 'Icon')
        el(icon, 'href', 'icons/' + sid + '.png' if bundled else 'https://maps.google.com/mapfiles/kml/shapes/' + ('open-diamond.png' if hollow else 'placemark_circle.png'))
        label = el(style, 'LabelStyle')
        el(label, 'color', 'ffffffff')
        el(label, 'scale', 0.9)
        styles.append(style)
    # Document styles precede its Features for the KML schema.
    children = list(doc)
    first_feature = next((i for i, child in enumerate(children) if child.tag.rsplit('}', 1)[-1] in ['Folder', 'Placemark']), len(children))
    for offset, style in enumerate(styles):
        doc.remove(style)
        doc.insert(first_feature + offset, style)
    folder = el(doc, 'Folder', id='gongbu_pacification')
    el(folder, 'name', LAYER_NAME)
    el(folder, 'open', 1)
    el(folder, 'description', overview_html(config))
    view(folder, 93.98, 29.73, 190000)
    guide = el(folder, 'Placemark', id='gongbu_pacification_guide')
    el(guide, 'name', '本段说明｜安抚约2月；候选与待考分开')
    el(guide, 'description', overview_html(config))
    ref_folder = el(folder, 'Folder', id='gongbu_residence_background')
    el(ref_folder, 'name', '驻地背景参照｜牙披，默认隐藏')
    el(ref_folder, 'visibility', 0)
    el(ref_folder, 'open', 0)
    for place in config['places']:
        parent = ref_folder if place['id'] == 'apei_background' else folder
        pm = el(parent, 'Placemark', id='gongbu_' + place['id'])
        el(pm, 'name', place['label'])
        el(pm, 'visibility', 1)
        el(pm, 'description', place_html(config, place))
        if place['lon'] is not None:
            view(pm, place['lon'], place['lat'], 45000)
            el(pm, 'styleUrl', '#gongbu_reference' if place['id'] == 'apei_background' else '#gongbu_candidate')
            extended = el(pm, 'ExtendedData')
            for key, value in [('book_name', place['book_name']), ('modern_name', place['modern']), ('certainty', place['certainty']), ('timing', place['timing'])]:
                data = el(extended, 'Data', name=key)
                el(data, 'value', value)
            point = el(pm, 'Point')
            el(point, 'altitudeMode', 'clampToGround')
            el(point, 'coordinates', f'{place["lon"]},{place["lat"]},0')
    return folder


def write_gongbu_indexes():
    config = load()
    text = '工布安抚三地核对\n核对日期：' + config['checked_at'] + '\n\n'
    text += config['quote'] + '\n\n'
    text += '\n\n'.join(config[key] for key in ['scope', 'route_note', 'timing_note', 'coordinate_note']) + '\n\n'
    text += '地图：完整阅读地图的15层与独立“艽野尘梦_工布安抚三地.kmz”含相同内容，二选一显示；牙披背景参照默认隐藏，以免与08层重复。\n\n'
    for place in config['places']:
        text += place['label'] + '\n' + place['certainty'] + '\n' + place['note'] + '\n耗时：' + place['timing'] + '\n'
        if place['lon'] is not None:
            text += f'现代地区参照：{place["lon"]}°E，{place["lat"]}°N。\n'
        text += '\n'
    text += '来源与证据限度\n'
    for source in config['sources'].values():
        text += '\n' + source['title'] + '\n' + source['supports'] + '\n' + source['url'] + '\n'
    if config.get('google_earth_import'):
        text += '\nGoogle Earth核验\n' + config['google_earth_import']['note'] + '\n'
        if config['google_earth_import'].get('screenshot'):
            text += '核验截图：' + config['google_earth_import']['screenshot'] + '\n'
    (ROOT / '工布安抚三地核对说明.txt').write_text(text, encoding='utf-8')
    fields = ['id', '书中名', '地图标签', '现代参照', '经度', '纬度', '定位性质', '说明', '耗时', '来源']
    with (ROOT / '工布安抚三地对照.csv').open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for place in config['places']:
            writer.writerow(dict(zip(fields, [place['id'], place['book_name'], place['label'], place['modern'], place['lon'], place['lat'], place['certainty'], place['note'], place['timing'], '；'.join(config['sources'][key]['url'] for key in place['source_ids'])])))
    return text
