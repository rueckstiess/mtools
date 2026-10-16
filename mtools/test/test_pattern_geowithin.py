from mtools.util.logevent import LogEvent
from mtools.util.pattern import json2pattern


GEO = ('{ organizationId: 453003085614996, status: "A", '
       'address.gisLocation: { $geoWithin: { $geometry: { type: "Polygon", '
       'coordinates: [[[-65.62804, 21.715168], [-65.644209, 21.716755], '
       '[-65.62804, 21.715168]]] } } } }')


def test_string_geowithin_coordinates_collapse_to_one():
    pattern = json2pattern(GEO)
    assert pattern == (
        '{"address.gisLocation": {"$geoWithin": {"$geometry": '
        '{"coordinates": 1, "type": 1}}}, "organizationId": 1, "status": 1}'
    )
    assert '-65.62804' not in pattern
    assert '21.715168' not in pattern


def test_dict_geowithin_coordinates_collapse_to_one():
    doc = {
        'address.gisLocation': {
            '$geoWithin': {
                '$geometry': {
                    'type': 'MultiPolygon',
                    'coordinates': [[[[-65.6, 21.7], [-65.6, 21.8]]]],
                }
            }
        },
        'organizationId': 453003085614996,
    }
    pattern = json2pattern(doc)
    assert '"coordinates": 1' in pattern
    assert '-65.6' not in pattern
    assert '21.7' not in pattern


def test_geointersects_geometry_uses_the_same_placeholder():
    pattern = json2pattern(
        '{loc: {$geoIntersects: {$geometry: {type: "Point", '
        'coordinates: [-65.6, 21.7]}}}}')
    assert pattern == (
        '{"loc": {"$geoIntersects": {"$geometry": '
        '{"coordinates": 1, "type": 1}}}}'
    )


def test_coordinates_field_outside_geometry_is_left_in_place():
    assert json2pattern('{coordinates: [10, 20]}') == '{"coordinates": [1, 20]}'


def test_non_geo_operators_keep_their_placeholders():
    assert json2pattern('{a: {$in: [1, 2]}, b: "x"}') == '{"a": 1, "b": 1}'


def test_find_log_line_pattern_hides_polygon_vertices():
    line = (
        '2019-06-09T02:18:02.194+0000 I COMMAND  [conn1] command db.contact '
        'command: find { find: "contact", filter: %s } '
        'planSummary: IXSCAN keysExamined:10 docsExamined:10 nreturned:0 '
        '100ms' % GEO
    )
    pattern = LogEvent(line).pattern
    assert '"coordinates": 1' in pattern
    assert '-65.62804' not in pattern


def test_geometry_collection_coordinates_collapse_to_one():
    doc = {
        'loc': {
            '$geoIntersects': {
                '$geometry': {
                    'type': 'GeometryCollection',
                    'geometries': [
                        {'type': 'Point', 'coordinates': [-65.6, 21.7]},
                        {'type': 'LineString',
                         'coordinates': [[-65.6, 21.7], [-65.5, 21.8]]},
                    ],
                }
            }
        }
    }
    pattern = json2pattern(doc)
    assert '-65.6' not in pattern
    assert '21.7' not in pattern
    assert pattern.count('"coordinates": 1') == 2


def test_geometry_collection_string_coordinates_collapse_to_one():
    pattern = json2pattern(
        '{loc: {$geoWithin: {$geometry: {type: "GeometryCollection", '
        'geometries: [ {type: "Point", coordinates: [-65.6, 21.7]} ]}}}}')
    assert pattern == (
        '{"loc": {"$geoWithin": {"$geometry": {"geometries": '
        '[{"coordinates": 1, "type": 1}], "type": 1}}}}')
