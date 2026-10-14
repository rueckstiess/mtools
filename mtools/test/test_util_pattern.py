"""Tests for converting queries to patterns. See issue #848."""

import json

from mtools.util.logevent import LogEvent
from mtools.util.pattern import json2pattern


def _as_pattern(doc):
    """Dump a document the same way json2pattern does."""
    return json.dumps(doc, sort_keys=True, separators=(', ', ': '),
                      ensure_ascii=False)


def _issue_match():
    """The $match shared by both aggregate pipelines in issue #848."""
    return {
        "$match": {
            "$and": [
                {"$and": [{"brand_id": {"$in": [
                    "ckpwemryo0000w7d26aq4e0m3",
                    "ckq2dv5s40003w7d2250o10uj",
                ]}}]},
                {"$and": [
                    {"brand_id": {"$in": ["ckpwemryo0000w7d26aq4e0m3"]}},
                    {"status": {"$nin": ["solved", "closed"]}},
                    {"form_id": {"$nin": [
                        "ckj1doiw402jssav2v1h52v8o",
                        "ckj1doiw402jrsav2oao00uyn",
                    ]}},
                    {"custom_fields": {"$elemMatch": {
                        "id": "ckjfymwqt06inylv2ozjr8t27",
                        "value": {"$in": ["accounting_module"]},
                    }}},
                ]},
            ]
        }
    }


def _project_stage():
    fields = [
        "id", "subject", "status", "created_at", "requester", "assignee",
        "jira", "jira_status", "priority", "type", "updated_by", "updated_at",
        "unread_comment_count", "last_comment_unread_at", "custom_fields",
        "form_id", "brand_id", "metric.resolution_time",
    ]
    shape = {field: 1 for field in fields}
    shape["_id"] = 0
    return {"$project": shape}


def _string_match():
    """String-path shape: $in collapses, $nin and $elemMatch stay."""
    return {
        "$match": {
            "$and": [
                {"$and": [{"brand_id": 1}]},
                {"$and": [
                    {"brand_id": 1},
                    {"status": {"$nin": 1}},
                    {"form_id": {"$nin": 1}},
                    {"custom_fields": {"$elemMatch": {"id": 1, "value": 1}}},
                ]},
            ]
        }
    }


def _parsed_match():
    """List-path shape: operator arrays stay, with each scalar as 1."""
    return {
        "$match": {
            "$and": [
                {"$and": [{"brand_id": {"$in": [1, 1]}}]},
                {"$and": [
                    {"brand_id": {"$in": [1]}},
                    {"status": {"$nin": [1, 1]}},
                    {"form_id": {"$nin": [1, 1]}},
                    {"custom_fields": {"$elemMatch": {
                        "id": 1,
                        "value": {"$in": [1]},
                    }}},
                ]},
            ]
        }
    }


def _project_pattern():
    fields = [
        "_id", "assignee", "brand_id", "created_at", "custom_fields",
        "form_id", "id", "jira", "jira_status", "last_comment_unread_at",
        "metric.resolution_time", "priority", "requester", "status",
        "subject", "type", "unread_comment_count", "updated_at",
        "updated_by",
    ]
    return {"$project": {field: 1 for field in fields}}


def test_aggregate_strings_from_issue_848():
    """A pipeline string with several quoted arrays returns a pattern."""
    project = [_issue_match(), _project_stage(),
               {"$sort": {"created_at": -1}}, {"$skip": 0}, {"$limit": 25}]
    group = [_issue_match(), {"$group": {"_id": 1, "n": {"$sum": 1}}}]

    project_pattern = [
        _string_match(), _project_pattern(),
        {"$sort": {"created_at": 1}}, {"$skip": 1}, {"$limit": 1},
    ]
    group_pattern = [
        _string_match(), {"$group": {"_id": 1, "n": {"$sum": 1}}},
    ]

    assert json2pattern(json.dumps(project)) == _as_pattern(project_pattern)
    assert json2pattern(json.dumps(group)) == _as_pattern(group_pattern)


def test_parsed_aggregates_keep_operator_arrays():
    """A pipeline that is already a list keeps $in, $nin, and $elemMatch."""
    project = [_issue_match(), _project_stage(),
               {"$sort": {"created_at": -1}}, {"$skip": 0}, {"$limit": 25}]
    group = [_issue_match(), {"$group": {"_id": 1, "n": {"$sum": 1}}}]

    project_pattern = [
        _parsed_match(), _project_pattern(),
        {"$sort": {"created_at": 1}}, {"$skip": 1}, {"$limit": 1},
    ]
    group_pattern = [
        _parsed_match(), {"$group": {"_id": 1, "n": {"$sum": 1}}},
    ]

    assert json2pattern(project) == _as_pattern(project_pattern)
    assert json2pattern(group) == _as_pattern(group_pattern)


def test_two_sibling_in_arrays_keep_both_keys():
    """The second quoted array is part of the pattern."""
    text = '{"a": {"$in": ["one", "two"]}, "b": {"$in": ["three"]}}'
    assert json2pattern(text) == '{"a": 1, "b": 1}'
    assert json2pattern(json.loads(text)) == (
        '{"a": {"$in": [1, 1]}, "b": {"$in": [1]}}')


def test_single_in_collapses_on_the_string_path():
    """One $in array still collapses to 1, as existing patterns do."""
    text = '{"a": {"$in": ["only"]}}'
    assert json2pattern(text) == '{"a": 1}'
    assert json2pattern(json.loads(text)) == '{"a": {"$in": [1]}}'


def test_bracket_and_url_values_stay_in_their_arrays():
    """A ] or a URL inside a quoted value does not end the array early."""
    text = '{"a": ["nnn://aaa.bbb"], "b": ["keep]this", "x"]}'
    assert json2pattern(text) == '{"a": [1], "b": [1]}'
    assert json2pattern('{"name": ["foo]bar"]}') == '{"name": [1]}'


def test_plain_string_arrays_become_one_placeholder():
    """Each array of strings becomes a single 1, and later keys remain."""
    text = '{"attrib": ["val1", "val2", "3"], "other": ["x"]}'
    assert json2pattern(text) == '{"attrib": [1], "other": [1]}'


def test_shell_notation_with_two_string_arrays():
    """Legacy shell text and mlogfilter --pattern take the string path."""
    text = ('{brand_id: {$in: ["one", "two"]}, '
            'status: {$nin: ["solved", "closed"]}}')
    assert json2pattern(text) == '{"brand_id": 1, "status": {"$nin": 1}}'


def test_legacy_query_line_with_two_string_arrays():
    """A legacy query line yields a pattern when the query has two arrays."""
    line = (
        '2014-03-18T18:34:30.435+1100 [conn10] query test.new '
        'query: { brand_id: { $in: [ "one", "two" ] }, '
        'status: { $nin: [ "solved", "closed" ] } } nreturned:1 2ms'
    )
    assert LogEvent(line).pattern == '{"brand_id": 1, "status": {"$nin": 1}}'


def test_logv2_aggregate_keeps_the_parsed_pattern():
    """logv2 passes the pipeline list through, so $in arrays stay."""
    pipeline = [_issue_match(), {"$group": {"_id": 1, "n": {"$sum": 1}}}]
    line = json.dumps({
        "t": {"$date": "2022-02-22T23:17:30.970+00:00"},
        "s": "I",
        "c": "COMMAND",
        "id": 51803,
        "ctx": "conn258",
        "msg": "Slow query",
        "attr": {
            "type": "command",
            "ns": "support_portal.tickets",
            "command": {"aggregate": "tickets", "pipeline": pipeline},
            "durationMillis": 202,
        },
    })
    pattern = LogEvent(line).pattern
    assert pattern == json2pattern(pipeline)
    assert pattern == _as_pattern([
        _parsed_match(), {"$group": {"_id": 1, "n": {"$sum": 1}}},
    ])
