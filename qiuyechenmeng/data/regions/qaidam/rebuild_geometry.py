#!/usr/bin/env python3
"""Rebuild the 100 m drawing geometry from the preserved public KMZ.

Requires shapely >= 2 and pyproj >= 3. Optional --full-output writes an
unsimplified GeoJSON outside this directory, for independent inspection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import pyproj
import shapely
from pyproj import CRS, Geod, Transformer
from shapely.geometry import Point, Polygon, mapping
from shapely.geometry.polygon import orient
from shapely.ops import transform
from shapely.validation import explain_validity

BASE = Path(__file__).resolve().parent
RAW = BASE / 'raw_QaidamBasinCatchment.kmz'
DERIVED = BASE / 'derived_qaidam_catchment_100m.geojson'
MANIFEST = BASE / 'manifest.json'
NS = {'k': 'http://www.opengis.net/kml/2.2'}
METRIC_PROJ = '+proj=aeqd +lat_0=37 +lon_0=94 +datum=WGS84 +units=m +no_defs'
LABEL = [94.2, 37.5]


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def endpoint_key(coord):
    # KML has two shared endpoints differing only at ~1e-14 degrees.
    # Round for matching only; preserve the first encountered original vertex.
    return tuple(round(v, 9) for v in coord)


def reconstruct():
    with zipfile.ZipFile(RAW) as archive:
        assert archive.testzip() is None, 'KMZ ZIP checksum failure'
        root = ET.fromstring(archive.read('doc.kml'))
    parts = []
    for placemark in root.findall('.//k:Placemark', NS):
        assert len(placemark.findall('.//k:LineString', NS)) == 1
        nodes = placemark.find('.//k:LineString/k:coordinates', NS).text.split()
        coords = [tuple(map(float, node.split(',')[:2])) for node in nodes]
        parts.append((placemark.findtext('k:name', namespaces=NS), coords))
    assert len(parts) == 32
    raw_vertices = sum(len(coords) for _, coords in parts)
    name, ring = parts.pop(0)
    order = [name]
    approximate_joins = []
    while parts:
        matches = []
        for index, (name, coords) in enumerate(parts):
            if endpoint_key(ring[-1]) == endpoint_key(coords[0]):
                matches.append((index, name, coords))
            elif endpoint_key(ring[-1]) == endpoint_key(coords[-1]):
                matches.append((index, name, coords[::-1]))
        assert len(matches) == 1, 'Boundary has branching or disconnected segments'
        index, name, coords = matches[0]
        if ring[-1] != coords[0]:
            approximate_joins.append({'retained': ring[-1], 'duplicate': coords[0]})
        ring.extend(coords[1:])
        order.append(name)
        parts.pop(index)
    assert ring[0] == ring[-1], 'Boundary is not exactly closed'
    original = orient(Polygon(ring), sign=1.0)
    assert original.is_valid, explain_validity(original)
    assert len(original.interiors) == 0
    return original, order, raw_vertices, approximate_joins


def feature_collection(geometry, properties):
    return {'type': 'FeatureCollection', 'features': [{
        'type': 'Feature', 'id': 'qaidam_catchment',
        'properties': properties, 'geometry': mapping(geometry),
    }]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-output', type=Path)
    args = parser.parse_args()
    original, order, raw_vertices, joins = reconstruct()
    local_crs = CRS.from_proj4(METRIC_PROJ)
    forward = Transformer.from_crs(4326, local_crs, always_xy=True).transform
    reverse = Transformer.from_crs(local_crs, 4326, always_xy=True).transform
    projected = transform(forward, original)
    simple_projected = projected.simplify(100, preserve_topology=True)
    simplified = orient(transform(reverse, simple_projected), sign=1.0)
    assert simplified.is_valid, explain_validity(simplified)
    assert simplified.exterior.is_closed
    assert len(simplified.interiors) == 0
    assert original.contains(Point(LABEL)) and simplified.contains(Point(LABEL))
    geod = Geod(ellps='WGS84')
    original_area, original_perimeter = geod.geometry_area_perimeter(original)
    derived_area, derived_perimeter = geod.geometry_area_perimeter(simplified)
    original_area = abs(original_area) / 1e6
    derived_area = abs(derived_area) / 1e6
    properties = {
        'name': '柴达木盆地｜汇水区参照',
        'boundary_nature': '2023年科研数据的盆地汇水区；不是自然地貌盆地边界或官方行政界',
        'source_doi': '10.3974/geodb.2023.10.08.V1',
        'source_title': '柴达木盆地汇水区绿洲、水系及高程分类数据集',
        'source_publication': '2023-10',
        'source_reported_area_km2': 275753.06,
        'unsimplified_geodesic_area_km2': original_area,
        'drawing_geodesic_area_km2': derived_area,
        'drawing_simplification': '当地等距方位投影内100米保拓扑简化，回转WGS84；非原数据精度承诺',
        'coordinate_system': 'WGS84 longitude, latitude',
        'license': 'CC BY 4.0',
        'license_source': 'https://data.dcxjegi.cn/portal/metadata/9da9c5e5-a6f8-41c2-b594-92d0345b7da1',
        'attribution': '桂东伟、林敬梧、王颢霖、李希明、刘闯（2023）；全球变化科学研究数据出版系统；干旱区生态与资源科学数据中心',
        'label_coordinates': LABEL,
    }
    write_json(DERIVED, feature_collection(simplified, properties))
    if args.full_output:
        write_json(args.full_output, feature_collection(original, dict(properties, name='柴达木盆地汇水区｜未简化核验面', drawing_simplification='未简化，仅拼接原32段边界线并合并重复端点')))
    manifest = {
        'title': '柴达木盆地｜汇水区参照',
        'retrieved_on': '2026-11-01',
        'source': {
            'doi': '10.3974/geodb.2023.10.08.V1',
            'publication_date': '2023-10',
            'citation': '桂东伟, 林敬梧, 王颢霖, 李希明, 刘闯. 柴达木盆地汇水区绿洲、水系及高程分类数据集[J/DB/OL]. 全球变化数据仓储电子杂志(中英文), 2023. https://doi.org/10.3974/geodb.2023.10.08.V1.',
            'metadata_url': 'https://geodoi.ac.cn/WebCn/doi.aspx?Id=3414',
            'download_url': 'https://geodoi.ac.cn/webcn/down.aspx?fileID=8476&size=3412600',
            'download_method': 'Normal public download link presented by the dataset page; no login or restricted-access bypass.',
            'raw_filename': RAW.name,
            'raw_bytes': RAW.stat().st_size,
            'raw_sha256': hashlib.sha256(RAW.read_bytes()).hexdigest(),
            'raw_kmz_entries': ['doc.kml'],
            'reported_area_km2': 275753.06,
            'reported_area_projection': 'Albers',
            'source_data_description': 'Based on Google Earth images, ASTER GDEM 30 m and field measurements, according to the institutional metadata. This does not establish boundary positional accuracy.',
        },
        'license': {
            'spdx': 'CC-BY-4.0',
            'url': 'https://creativecommons.org/licenses/by/4.0/',
            'evidence_url': 'https://data.dcxjegi.cn/portal/metadata/9da9c5e5-a6f8-41c2-b594-92d0345b7da1',
            'evidence_verified_on': '2026-11-01',
            'evidence': 'Institutional mirror at Xinjiang Institute of Ecology and Geography, CAS lists this same DOI, matching five file names/sizes, and explicitly applies Creative Commons Attribution 4.0 International License.',
            'evidence_short_quote': '本作品采用 知识共享署名 4.0 国际许可协议进行许可。',
            'attribution': properties['attribution'],
            'mirror_contributors': ['桂东伟', '李伯騛'],
            'changes': 'Reconstructed one closed ring from 32 source LineStrings; merged duplicate joining endpoints, including two floating point tails; simplified for drawing in metric projection and reprojected to WGS84.',
            'no_endorsement': True,
            'general_ten_percent_policy': 'Not used as the authorization basis. A smaller fraction of the source archive size alone is not evidence of compliance with a policy concerning the contents of a new dataset.',
        },
        'boundary_nature': {
            'type': 'basin catchment / 盆地汇水区',
            'not_natural_landform_basin_boundary': True,
            'not_administrative_boundary': True,
            'not_historic_travel_extent': True,
            'context_natural_landform_basin_area_km2_approximate': 250000,
            'context_source': 'https://igsnrr.cas.cn/cbkx/kpyd/zgdl/cndm/202009/t20200910_5692364.html',
            'context_note': 'The broad natural landform basin is commonly described at about 250,000 km². Do not compare areas as if they were the same boundary, or scale this catchment to that number.',
            'unavailable_preferred_dataset': 'NCDC 朱高峰 柴达木盆地矢量边界数据集（2021年）, about 240,000 km²; login to access, not obtained or substituted.',
            'unavailable_preferred_dataset_url': 'https://www.ncdc.ac.cn/portal/metadata/7d5ae51d-7d95-4edd-819d-dbfb528ba991',
        },
        'reconstruction': {
            'coordinate_system': 'WGS84 / EPSG:4326; longitude, latitude; altitude omitted',
            'input_geometry_type': '32 KML LineString features',
            'raw_coordinate_count_including_shared_endpoints': raw_vertices,
            'segment_join_order': order,
            'endpoint_matching': 'Match endpoints rounded to 9 decimal places for comparison only; retain first encountered source coordinate; reverse segments as necessary; omit their duplicate joining endpoint.',
            'approximate_endpoint_joins': joins,
            'full_ring_coordinate_count_including_closure': len(original.exterior.coords),
            'full_ring_valid': original.is_valid,
            'full_ring_exactly_closed': original.exterior.coords[0] == original.exterior.coords[-1],
            'full_ring_holes': len(original.interiors),
            'full_ring_bounds_west_south_east_north': list(original.bounds),
            'full_wgs84_ellipsoidal_area_km2': original_area,
            'full_wgs84_ellipsoidal_perimeter_km': original_perimeter / 1000,
        },
        'drawing': {
            'file': DERIVED.name,
            'sha256': hashlib.sha256(DERIVED.read_bytes()).hexdigest(),
            'feature_count': 1,
            'type': simplified.geom_type,
            'simplification_tolerance_m': 100,
            'preserve_topology': True,
            'method': 'Douglas-Peucker topology-preserving simplification using Shapely in a local Azimuthal Equidistant projection centered at 94°E, 37°N, then transformed back to WGS84.',
            'metric_projection': METRIC_PROJ,
            'not_original_data_accuracy_promise': True,
            'coordinate_count_including_closure': len(simplified.exterior.coords),
            'valid': simplified.is_valid,
            'validity': explain_validity(simplified),
            'exactly_closed': simplified.exterior.coords[0] == simplified.exterior.coords[-1],
            'holes': len(simplified.interiors),
            'wgs84_ellipsoidal_area_km2': derived_area,
            'wgs84_ellipsoidal_perimeter_km': derived_perimeter / 1000,
            'area_change_km2': derived_area - original_area,
            'area_change_percent': (derived_area / original_area - 1) * 100,
            'label_coordinates': LABEL,
            'label_strictly_inside_full': original.contains(Point(LABEL)),
            'label_strictly_inside_simplified': simplified.contains(Point(LABEL)),
            'label_distance_to_simplified_boundary_local_projection_m': simple_projected.boundary.distance(Point(forward(*LABEL))),
            'alternative_representative_point': list(simplified.representative_point().coords[0]),
        },
        'software': {'shapely': shapely.__version__, 'pyproj': pyproj.__version__},
    }
    write_json(MANIFEST, manifest)
    print(json.dumps(manifest['drawing'], ensure_ascii=False))


if __name__ == '__main__':
    main()
