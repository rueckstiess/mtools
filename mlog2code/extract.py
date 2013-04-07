import os
import re
import sys
import commands
import subprocess
import cPickle

from collections import defaultdict, OrderedDict

class LogCodeLine(object):
    def __init__(self, pattern):
        self.pattern = pattern
        self.occurences = []

    def addOccurence(self, version, filename, lineno, loglevel):
        self.occurences.append((version, filename, lineno, loglevel))

    def __str__(self):
        s = "%s\n"%(" <var> ".join(self.pattern))
        for version, filename, lineno, loglevel in self.occurences:
            s += "{:>10}: in {}:{}, loglevel {}\n".format(version, filename, lineno, loglevel)
        s += '\n'
        return s

mongodb_directory = "/Users/tr/Documents/code/mongo/"

def source_files(mongodb_directory):
    for root, dirs, files in os.walk(mongodb_directory):
        for filename in files:
            if filename.endswith(('.cpp', '.c', '.h')):
                yield os.path.join(root, filename)

def get_all_versions():
    pr = subprocess.Popen("/usr/local/bin/git checkout master", 
                          cwd = mongodb_directory, 
                          shell = True, 
                          stdout = subprocess.PIPE, 
                          stderr = subprocess.PIPE)
    pr.communicate()

    pr = subprocess.Popen("/usr/local/bin/git tag", 
                          cwd = mongodb_directory, 
                          shell = True, 
                          stdout = subprocess.PIPE, 
                          stderr = subprocess.PIPE)

    (out, error) = pr.communicate()

    versions = out.split()

    # only newer than 1.8.0
    versions = versions[versions.index("r1.8.0"):]

    # remove release candidates
    versions = [v for v in versions if "rc" not in v]

    # remove developer versions
    versions = [v for v in versions if re.search(r'\.[02468]\.', v)]

    return versions


def switch_version(version):
    pr = subprocess.Popen("/usr/local/bin/git checkout %s"%version, 
                          cwd = os.path.dirname( mongodb_directory ), 
                          shell = True, 
                          stdout = subprocess.PIPE, 
                          stderr = subprocess.PIPE)

    (out, error) = pr.communicate()
    print error


def extract_logs(log_code_lines, current_version):
    log_templates = set()

    for filename in source_files(mongodb_directory):
        f = open(filename, 'r')
        for lineno, line in enumerate(f):
            if "log()" in line or "LOG(" in line or "warning()" in line or "error()" in line:
                line = line.strip()
                matches = re.findall(r"\"(.+?)\"", line)
                matches = [re.sub(r'(\\t)|(\\n)', '', m).strip() for m in matches]

                # remove empty tokens
                matches = [m for m in matches if m]

                if len(matches) == 0:
                    continue

                loglevel = re.match(r'LOG\(([0-9])\)', line)
                if loglevel:
                    loglevel = int(loglevel.group(1))
                else:
                    loglevel = 0


                # # special case: remove "query:"
                # matches = [m for m in matches if "query:" not in m]

                matches = tuple(matches)

                # add to log_code_lines dict
                if not matches in log_code_lines:
                    log_code_lines[matches] = LogCodeLine(matches)

                log_code_lines[matches].addOccurence(current_version, filename, lineno, loglevel)
                log_templates.add(matches)

        f.close()

    return log_templates





if __name__ == '__main__':

    versions = get_all_versions()

    log_code_lines = {}
    logs_versions = defaultdict(list)

    for v in versions:
        switch_version(v)
        logs = extract_logs(log_code_lines, v)
        print v
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
        logs_by_word[lbw] = sorted(logs_by_word[lbw], key=lambda x: len(x), reverse=True)

    cPickle.dump((versions, logs_versions, logs_by_word, log_code_lines), open('logs_versions.pickle', 'wb'), -1)

    for lcl in log_code_lines:
        print log_code_lines[lcl]


