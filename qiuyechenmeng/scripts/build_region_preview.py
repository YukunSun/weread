"""Build a static, source-labelled area overview without browser dependencies."""
from pathlib import Path
import html
import json
import math
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1440, 1100
WEST, EAST, SOUTH, NORTH = 78.0, 105.0, 26.0, 39.5
LEFT, TOP, MAP_WIDTH = 72, 150, 1296
COS = math.cos(math.radians(33))
SCALE = MAP_WIDTH / ((EAST - WEST) * COS)
MAP_HEIGHT = (NORTH - SOUTH) * SCALE
BOTTOM = TOP + MAP_HEIGHT


def xy(lon, lat):
    return LEFT + (lon - WEST) * COS * SCALE, TOP + (NORTH - lat) * SCALE


def e(value):
    return html.escape(str(value), quote=True)


def path_data(geometry):
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    parts = []
    for rings in polygons:
        for ring in rings:
            points = [xy(*p[:2]) for p in ring]
            parts.append('M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in points) + ' Z')
    return ' '.join(parts)


def label(x, y, title, subtitle, color, width, target=None):
    if target:
        tx, ty = xy(*target)
        yield f'<path d="M{tx:.1f},{ty:.1f} L{x:.1f},{y:.1f}" fill="none" stroke="#738292" stroke-width="1.2"/>'
        yield f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="2.5" fill="{color}" stroke="#fff"/>'
    yield f'<rect x="{x-width/2:.1f}" y="{y-25:.1f}" width="{width}" height="61" rx="8" fill="#ffffff" fill-opacity=".91" stroke="{color}" stroke-opacity=".85"/>'
    yield f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-size="23" font-weight="650" fill="#273b4c">{e(title)}</text>'
    yield f'<text x="{x:.1f}" y="{y+23:.1f}" text-anchor="middle" font-size="16" fill="#546575">{e(subtitle)}</text>'


def main():
    config = json.loads((ROOT/'data/regions/分区口径.json').read_text())
    admin = {str(f['id']): f for f in json.loads((ROOT/'data/regions/admin_regions_wgs84.geojson').read_text())['features']}
    culture = [r for r in config['ranges'] if r['group'] == 'culture']
    parts = [f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">藏区地理分区｜现代政区作概略参照</title>
<desc id="desc">依据指定知乎回答的地理分区说明，将卫、藏、康、安多、工布、阿里和阿坝交错区用现代政区组合呈现。色块只是较宽的阅读参照，不是历史疆界、文化界或人口分布界。</desc>
<metadata>Source article: {e(config['article']['url'])}; Geometry: DataV administrative data; inferred GCJ02 transformed to approximate WGS84; administrative snapshot date unspecified. Preview generated 2026-10-31. Projection: simple equirectangular, longitude scaled by cos(33 degrees). Individual source links and qualifications: data/regions/分区口径.json and manifest.json.</metadata>
<defs><clipPath id="mapClip"><rect x="{LEFT}" y="{TOP}" width="{MAP_WIDTH}" height="{MAP_HEIGHT:.1f}"/></clipPath></defs>
<style>text{{font-family:'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif}} .city{{font-size:15px;fill:#33495e;paint-order:stroke;stroke:#fff;stroke-width:5px;stroke-linejoin:round}} .gridLabel{{font-size:13px;fill:#7a8794}}</style>
<rect width="1440" height="1100" fill="#fff"/>
<text x="72" y="57" font-size="32" font-weight="650" fill="#23384b">藏区地理分区｜现代政区作概略参照</text>
<text x="72" y="92" font-size="17" fill="#627183">仅预览 10A 文化地理层 · 每套分法可在 KML 中单独开关 · 色块不是史界、文化界或人口分布界</text>
<text x="72" y="120" font-size="15" fill="#7c8794">行政数据含旧名旧码，时点未明；坐标按 GCJ-02 推定逆算为近似 WGS84。核对日期：2026-10-31</text>
<rect x="{LEFT}" y="{TOP}" width="{MAP_WIDTH}" height="{MAP_HEIGHT:.1f}" fill="#f8f9fb" stroke="#d6dde5"/>
''']
    # A quiet coordinate graticule makes the substrate self-contained.
    for lon in [80, 85, 90, 95, 100, 105]:
        x, _ = xy(lon, SOUTH)
        parts.append(f'<path d="M{x:.1f},{TOP}V{BOTTOM:.1f}" stroke="#e4e9ee" stroke-width="1"/>')
        parts.append(f'<text class="gridLabel" x="{x:.1f}" y="{BOTTOM+19:.1f}" text-anchor="middle">{lon}°E</text>')
    for lat in [28, 30, 32, 34, 36, 38]:
        _, y = xy(WEST, lat)
        parts.append(f'<path d="M{LEFT},{y:.1f}H{LEFT+MAP_WIDTH}" stroke="#e4e9ee" stroke-width="1"/>')
        parts.append(f'<text class="gridLabel" x="{LEFT-11}" y="{y+4:.1f}" text-anchor="end">{lat}°N</text>')
    parts.append('<g clip-path="url(#mapClip)">')
    for r in culture:
        for code in r['members']:
            parts.append(f'<path d="{path_data(admin[code]["geometry"])}" fill="{r["color"]}" fill-opacity=".56" stroke="{r["color"]}" stroke-opacity=".6" stroke-width=".8" fill-rule="evenodd"/>')
    outline_codes = ['540100', '540200', '540300', '540400', '540500', '540600', '542500', '630000', '513300', '513200', '533400', '623000']
    for code in outline_codes:
        parts.append(f'<path d="{path_data(admin[code]["geometry"])}" fill="none" stroke="#8795a3" stroke-opacity=".75" stroke-width="1.1"/>')
    # Labels deliberately distinguish an uncoloured northern administrative area.
    x, y = xy(89.6, 33.3)
    parts.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-size="18" fill="#8894a2">那曲</text>')
    parts.append(f'<text x="{x:.1f}" y="{y+24:.1f}" text-anchor="middle" font-size="14" fill="#8d99a5">羌塘自然地理另层显示</text>')
    for name, lon, lat, dx, dy in [
        ('拉萨', 91.132, 29.65, 7, -8),
        ('日喀则', 88.88, 29.27, 7, -8),
        ('昌都', 97.178, 31.143, -42, 21),
        ('西宁', 101.778, 36.617, 7, -8),
        ('康定', 101.955, 30.002, 7, 20),
    ]:
        x, y = xy(lon, lat)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#3f5265" stroke="#fff" stroke-width="1.2"/>')
        parts.append(f'<text class="city" x="{x+dx:.1f}" y="{y+dy:.1f}">{name}</text>')
    layout = {
        'ngari': (82.1, 32.3, '阿里', '现代地区参照', 190, None),
        'tsang': (86.4, 28.9, '藏／后藏核心', '日喀则政区参照', 226, [87.8, 29.3]),
        'wei': (90.6, 27.8, '卫／前藏核心', '拉萨、山南参照', 208, [91.6, 29.3]),
        'gongbo': (95.4, 27.8, '工布核心', '巴宜、工布江达、米林', 230, [93.9, 29.6]),
        'kham': (98.9, 32.6, '康／康巴', '昌都、甘孜、玉树、迪庆', 260, None),
        'amdo': (99.0, 36.0, '安多｜较宽政区参照', '青海除玉树 ＋ 甘南', 290, None),
        'aba_transition': (102.7, 33.6, '阿坝交错区', '现代州域参照', 208, [102.5, 32.2]),
    }
    for r in culture:
        lon, lat, title, subtitle, width, target = layout[r['id']]
        x, y = xy(lon, lat)
        parts.extend(label(x, y, title, subtitle, r['color'], width, target))
    parts.append('</g>')
    # Scale is only approximate at the reference latitude, like the projection.
    sx, sy = 105, BOTTOM - 26
    length = (500/111.195) * SCALE
    parts.append(f'<path d="M{sx},{sy}H{sx+length:.1f} M{sx},{sy-5}V{sy+5} M{sx+length:.1f},{sy-5}V{sy+5}" stroke="#5e6d7a" stroke-width="2"/>')
    parts.append(f'<text x="{sx+length/2:.1f}" y="{sy-10}" text-anchor="middle" font-size="13" fill="#637381">约 500 km（33°N）</text>')
    legend_y = 975
    legend = [('wei', '卫／前藏'), ('tsang', '藏／后藏'), ('kham', '康'), ('amdo', '安多'), ('gongbo', '工布'), ('ngari', '阿里'), ('aba_transition', '阿坝交错区')]
    colors = {r['id']: r['color'] for r in culture}
    for i, (key, title) in enumerate(legend):
        x = 80 + i*183
        parts.append(f'<rect x="{x}" y="{legend_y-14}" width="23" height="15" fill="{colors[key]}" stroke="#9ca7b2" stroke-width=".5"/>')
        parts.append(f'<text x="{x+32}" y="{legend_y}" font-size="15" fill="#617180">{title}</text>')
    parts.append('<text x="72" y="1012" font-size="15" fill="#647383">范围边缘沿现代政区数据，仅为阅读定位；工布未覆盖全林芝，阿坝未整州并入康或安多，安多参照较宽。</text>')
    parts.append('<text x="72" y="1040" font-size="14" fill="#7b8793">原文的前后藏、元明地域称谓及羌塘另有独立图层；此图不复原历代政权边界，也不表示完整藏族分布。</text>')
    parts.append(f'<a xlink:href="{e(config["article"]["url"])}"><text x="72" y="1074" font-size="14" fill="#53728d">指定知乎回答 · 数据：DataV 行政几何 · 核查：中国藏学研究中心、地方志及西藏自治区公开资料</text></a>')
    parts.append('</svg>')
    output = ROOT/'藏区地理范围_概览.svg'
    output.write_text('\n'.join(parts), encoding='utf-8')
    ET.parse(output)
    print(output, output.stat().st_size, 'bytes', f'{WIDTH}×{HEIGHT}')


if __name__ == '__main__':
    main()
