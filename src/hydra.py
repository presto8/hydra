import fcntl
import os
import signal
import time
import yaml
from .jobs import Job, JobGroup


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


def config_to_jobgroup(y) -> JobGroup:
    jobgroup_name = y['hydra']['name']
    jobs = []

    backups = []
    for name, backup in y['backups'].items():
        backup['name'] = name
        storage = y['storages'][backup['storage']]
        backup['storage'] = storage
        backup['env'] = configure_backup_runtime(backup)
        print(backup)
        backups.append(backup)

    for phase in "backup verify maintain".split():
        for backup in backups:
            cmd = y['methods'][backup['method']][phase]
            cmd = cmd.split()
            try:
                path_idx = cmd.index('{}')
                cmd = cmd[:path_idx] + y['files']['paths'] + cmd[path_idx + 1:]
            except ValueError:
                pass
            job = Job(name=f"{name}-{phase}", cwd="/tmp", command=cmd, env=backup['env'])
            jobs.append(job)

    for j in jobs:
        print(j)

    return JobGroup(name=jobgroup_name, jobs=jobs)


def configure_backup_runtime(backup):
    storage = backup['storage']
    if backup['method'] == 'restic':
        name = get_ephemeral_name()
        env = configure_storage_runtime(name, storage)
        env.update(configure_restic_runtime(name, backup))
        return env

    raise Fail('unsupported', backup['method'])


def get_ephemeral_name():
    time_ms = int(time.time() * 1000)
    return f"HYDRA{time_ms}"


def configure_storage_runtime(name, storage):
    env = {}
    if 'rclone' in storage:
        r = storage['rclone']
        env[f"RCLONE_CONFIG_{name}_TYPE"] = r['type']
        env[f"RCLONE_CONFIG_{name}_TOKEN"] = r['token']
    return env


def configure_restic_runtime(name, backup):
    env = {}
    env["RESTIC_REPOSITORY"] = f"rclone:{name}:{backup['storage_path']}"
    env["RESTIC_PASSWORD"] = backup['password']
    return env
