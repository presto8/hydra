import argparse
import fcntl
import os
import signal
import subprocess
import sys
import threading
import time
import yaml
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import NamedTuple, Optional
from . import jobs


def yaml_to_jobgroup(yamlstr: str) -> jobs.JobGroup:
    y = yaml.safe_load(yamlstr)

    jobgroup_name = y['jobgroup']['name']
    jobs = []

    for name, info in y['jobs'].items():
        required_fields = "cwd cmd".split()
        missing = [x for x in required_fields if x not in info]
        if missing:
            raise Fail(f"required fields not present: {missing}")

        if isinstance(info['cmd'], str):
            info['cmd'] = info['cmd'].split()

        after = info.get('after', None)
        if isinstance(after, str):
            after = after.split()
        max_time = info.get('max_time', None)

        job = jobs.Job(name=name, cwd=info['cwd'], command=info['cmd'], after=after, max_time=max_time)
        jobs.append(job)

    if not jobgroup_name:
        raise Fail("required configuration for [jobgroup] not found")

    return jobs.JobGroup(name=jobgroup_name, jobs=jobs)


def create_test_jobs_yaml():
    return """
# Config file uses YAML syntax. cwd and cmd must be specified. cmd is split on
# whitespace; use list syntax [] to include spaces in arguments.

jobgroup: test

jobs:
  missing:
    cwd: /tmp
    cmd: asdfasdfadsf
  notexec:
    cwd: /tmp
    cmd: /etc/motd
  echo:
    cwd: /tmp
    cmd: echo hi
  "true":
    cwd: /tmp
    cmd: "true"
  "false":
    cwd: /tmp
    cmd: "false"
    after: "true"
  sleep20:
    cwd: /tmp
    cmd: sleep 20
    after:
  sleep 3:
    cwd: /tmp
    cmd: sleep 3
    after:
  timeout:
    cwd: /tmp
    cmd: sleep 100
    after:
    maxtime: 5
  final:
    cwd: /tmp
    cmd: ["echo", "all done"]
    after: [sleep20, "sleep 3"]
"""


def main():
    fail_if_already_running()

    if ARGS.test:
        yamlstr = create_test_jobs_yaml()
        test_job_group = yaml_to_jobgroup(yamlstr)

        jobgroups = [test_job_group]
    else:
        jobgroups = []
        for path in ARGS.jobfiles:
            with open(path, "r") as f:
                jobgroup = yaml_to_jobgroup(f.read())
                jobgroups.append(jobgroup)

    failed_jobs = 0
    for jobgroup in jobgroups:
        jobgroup.run()
        failed_jobs += jobgroup.failed_jobs
        print_results(jobgroup)

    if failed_jobs > 0:
        raise Fail()


def print_results(jobgroup):
    fmt_results = jobgroup.format_results()
    if not ARGS.quiet:
        print()
        print(fmt_results)
    jobgroup.write_summary()


class Fail(Exception):
    pass


def info(*args):
    if not ARGS.quiet:
        print(*args)


def fail_if_already_running():
    this_script = os.path.realpath(__file__)
    lockfd = os.open(this_script, os.O_RDONLY)
    try:
        fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise Fail("another process is running")


class SigtermInterrupt(Exception):
    pass


def register_sigterm():
    def exit_gracefully(*args):
        raise SigtermInterrupt()
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)
