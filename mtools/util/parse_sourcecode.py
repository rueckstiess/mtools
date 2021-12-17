#!/usr/bin/env python3

import pickle
import os
import re
import subprocess
import sys
from collections import defaultdict
from distutils.spawn import find_executable

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from mtools.util.logcodeline import LogCodeLine

# Path to a local git clone from https://github.com/mongodb/mongo.git
mongodb_path = "/usr/local/src/mongo/"

git_path = find_executable('git')
pattern_id = 0


def source_files(mongodb_path):
    """Find source files."""
    for root, dirs, files in os.walk(mongodb_path):
        for filename in files:
            # skip files in dbtests folder
            if 'dbtests' in root:
                continue
            if filename.endswith(('.cpp', '.c', '.h')):
                yield os.path.join(root, filename)


def get_all_versions():
    pr = subprocess.Popen(git_path + " checkout master",
                          cwd=mongodb_path,
                          shell=True,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    pr.communicate()

    pr = subprocess.Popen(git_path + " tag",
                          cwd=mongodb_path,
                          shell=True,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)

    (out, error) = pr.communicate()
    versions = out.split()

    # only newer than 2.4.0
    versions = versions[versions.index("r2.4.0"):]

    # remove release candidates
    versions = [v for v in versions if "rc" not in v]

    # remove developer versions
    versions = [v for v in versions if re.search(r'\.[02468]\.', v)]

    # add master logs
    versions.append('master')

    return versions


def switch_version(version):
    print("Switching to %s" % version)
    pr = subprocess.Popen(git_path + " checkout %s" % version,
                          cwd=os.path.dirname(mongodb_path),
                          shell=True,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)

    (out, error) = pr.communicate()
    print(error)


def output_verbose(version, filename, lineno, line, statement,
                   matches, accepted, why):
    print("%10s %s %s:%s" % ("location:", version, filename, lineno))
    print("%10s %s" % ("line:", line))
    print("%10s %s" % ("statement:", statement))
    print("%10s %s" % ("matches:", matches))
    print("%10s %s" % ("accepted:", accepted))
    print("%10s %s" % ("reason:", why))
    print("----------------------------")
    print("\n")


def extract_logs(log_code_lines, current_version):
    global pattern_id
    log_templates = set()
    log_triggers = ([" log(", " LOG(", " LOGSOME", " warning()",
                     " error()", " out()", " problem()"])

    for filename in source_files(mongodb_path):
        f = open(filename, 'rb')

        # remove parent path
        filename = filename[len(mongodb_path):]

        lines = f.readlines()
        for lineno, line in enumerate(lines):
            trigger = next((t for t in log_triggers if t in line), None)

            if trigger:
                # extend line to wrap over line breaks until ; at end of line
                # is encountered
                statement = line
                current_lineno = lineno

                semicolon_match = None
                while not semicolon_match:
                    current_lineno += 1
                    if current_lineno >= len(lines):
                        break
                    statement += lines[current_lineno]
                    # match semicolon at end of line
                    # (potentially with whitespace between)
                    semicolon_match = re.search(';\s*$', statement,
                                                flags=re.MULTILINE)
                    if semicolon_match:
                        statement = statement[:semicolon_match.start()]
                        break

                # exclude triggers in comments (both // and /* */)
                trigger_pos = statement.find(trigger)
                newline_pos = statement.rfind("\n", 0, trigger_pos)
                if statement.find("//", newline_pos + 1, trigger_pos) != -1:
                    # output_verbose(current_version, filename, lineno,
                    # line, statement, "comment //")
                    continue
                comment_pos = statement.find("/*", 0, trigger_pos)
                if comment_pos != -1:
                    if statement.find("*/", comment_pos + 2,
                                      trigger_pos) == -1:
                        # output_verbose(current_version, filename, lineno,
                        # line, statement, "comment /* */")
                        continue

                statement = statement[statement.find(trigger) +
                                      len(trigger):].strip()

                # unescape strings
                # statement = statement.decode("string-escape")
                # print(statement)

                # remove compiler #ifdef .. #endif directives
                statement = re.sub(r'#ifdef.*?#endif', '',
                                   statement, flags=re.DOTALL)

                # filtering out conditional strings with
                # tertiary operator: ( ... ? ... : ... )
                statement = re.sub(r'\(.*?\?.*?\:.*?\)', '', statement)

                # split into stream tokens
                stream_tokens = statement.split("<<")

                # remove newlines from stream tokens
                stream_tokens = ([re.sub('\n', '', s).strip()
                                  for s in stream_tokens])

                matches = []
                for s in stream_tokens:
                    # match only non-empty strings with single / double quotes
                    match = re.match(r'"(.+?)"', s)
                    if match:
                        match = (re.sub(r'(\\t)|(\\n)|"', '',
                                        match.group(1)).strip())
                        matches.append(match)

                # get all double-quoted strings surrounded by << or ending in ;
                # print("s:::", statement)
                # matches = re.findall(r"<\s*\"(.*?)\"\s*(?:<|;)",
                #                      statement, flags=re.DOTALL)
                # print(matches)

                # remove tabs, double quotes and newlines and strip whitespace
                # from matches
                # matches = [re.sub(r'(\\t)|(\\n)|"', '', m).strip()
                #            for m in matches]
                # print(matches)

                # remove empty tokens
                matches = [m for m in matches if m]

                # skip empty matches
                if len(matches) == 0:
                    # output_verbose(current_version, filename, lineno, line,
                    #                statement, matches, False, "zero matches")
                    continue

                # skip matches with total character length < 3
                if len(''.join(matches)) < 3:
                    continue

                # skip matches consisting of single word, this will discard
                # some valid log lines but overall improves performance
                if len(matches) == 1 and " " not in matches[0]:
                    continue

                # special case causes trouble because of query operation lines
                if matches[0] == "query:":
                    # output_verbose(current_version, filename, lineno, line,
                    #                statement, matches, False,
                    #                "contains 'query:'")
                    continue

                loglevel = re.search(r'LOG\(\s*([0-9])\s*\)', line)
                if loglevel:
                    loglevel = int(loglevel.group(1))

                if trigger == ' log(':
                    loglevel = 0

                pattern = tuple(matches)

                # add to log_code_lines dict
                if pattern not in log_code_lines:
                    log_code_lines[pattern] = LogCodeLine(pattern, pattern_id)
                    pattern_id += 1

                # clean up values
                lineno = lineno + 1
                trigger = trigger.strip()

                log_code_lines[pattern].addMatch(current_version, filename,
                                                 lineno, loglevel, trigger)
                log_templates.add(pattern)

                # output_verbose(current_version, filename, lineno, line,
                #                statement, matches, True, "OK")

        f.close()

    return log_templates


if __name__ == '__main__':

    versions = get_all_versions()

    if len(sys.argv) > 1:
        versions = [sys.argv[1]]

    log_code_lines = {}
    logs_versions = defaultdict(list)
    print("parsing...")
    for v in versions:
        switch_version(v)
        logs = extract_logs(log_code_lines, v)
        print("version %s, %i lines extracted" % (v[1:], len(logs)))
        for l in logs:
            logs_versions[l].append(v)

    switch_version('master')

    # also store hashed by first word for quickly finding the related log lines
    logs_by_word = defaultdict(list)
    for lv in logs_versions:
        first_token = lv[0]
        split_words = first_token.split()
        logs_by_word[split_words[0]].append(lv)

    # now sort by number of tokens
    for lbw in logs_by_word:
        logs_by_word[lbw] = sorted(logs_by_word[lbw], key=lambda x: len(x),
                                   reverse=True)

    # for l in sorted(logs_versions):
    #     print(" <var> ".join(l), "found in:", ", ".join(logs_versions[l]))

    # write out to mongodb
    write_to_db = True
    try:
        mc = MongoClient()
        mc['log2code']['instances'].drop()
    except ConnectionFailure:
        write_to_db = False

    for pattern in log_code_lines:
        lcl = log_code_lines[pattern]

        first_token = pattern[0]
        split_words = first_token.split()

        instance = {
            '_id': lcl.pattern_id,
            'pattern': list(lcl.pattern),
            'first_word': split_words[0],
            'matches': []
        }

        for version in lcl.matches:
            matches = lcl.matches[version]
            for occ in matches:
                instance['matches'].append({
                    'version': version,
                    'file': occ[0],
                    'lineno': occ[1],
                    'loglevel': occ[2],
                    'trigger': occ[3]
                })

        if write_to_db:
            (mc['log2code']['instances']
             .update_one({'pattern': instance['pattern']}, instance,
                     upsert=True)())

    pickle.dump((versions, logs_versions, logs_by_word, log_code_lines),
                 open('log2code.pickle', 'wb'), -1)

    print("%i unique log messages imported and written to log2code.pickle"
          % len(log_code_lines))
