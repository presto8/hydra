import os
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import NamedTuple, Optional


class RunResult(NamedTuple):
    command: list[str]
    cwd: str
    start_time: datetime
    end_time: datetime
    elapsed_time: timedelta
    exit_code: int

    def __repr__(self):
        return f'RunResult(exit_code={self.exit_code} elapsed={self.elapsed_time})'


@dataclass
class Job:
    name: str
    cwd: str
    command: list[str]
    result: Optional[RunResult] = None
    logpath: Optional[str] = None
    after: Optional[str] = None
    max_time: Optional[timedelta] = None

    def __repr__(self):
        logpath = f" log={self.logpath}" if self.logpath else ""
        result = f" {self.result}" if self.result else ""
        after = f' after={self.after}' if self.after else ""
        return f'Job("{self.name}"{after}{result}{logpath} cmd={self.command} cwd={self.cwd})'

    def run(self, logf) -> None:
        self.logpath = logf.name
        cmd = ["timeout", str(self.max_time.total_seconds())] if self.max_time else []
        cmd += self.command
        self.result = run_shell(*cmd, outputf=logf, cwd=self.cwd)


@dataclass
class JobGroup:
    name: str
    jobs: list[Job]
    backupdir: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    started_jobs: int = 0
    finished_jobs: int = 0
    failed_jobs: Optional[int] = None

    def __post_init__(self):
        self.mutex = threading.Lock()

    def run(self):
        self.build_dependencies()
        self.start_time = datetime.now()

        finaldir = datetime.now().strftime("%Y-%m-%d_%H.%M.%S_") + self.name
        with in_progress_dir(finaldir) as tempdir:
            self.backupdir = tempdir
            result = self.run_jobs()
        self.backupdir = finaldir

        self.end_time = datetime.now()

        job_results = [x.result for x in self.jobs if x.result is not None]
        self.started_jobs = len(job_results)
        self.failed_jobs = len([x for x in job_results if x.exit_code != 0])

        return result

    def build_dependencies(self):
        prev_job = None
        for job in self.jobs:
            if job.after == [] or prev_job is None:
                job.deps = []
            elif job.after:
                job.deps = [self.get_job(x) for x in job.after]
                if not all(job.deps):
                    raise Exception(f"{job}: unable to find all dependencies")
            elif job.after is None:
                job.deps = [prev_job]
            prev_job = job

    def run_jobs(self):
        threads = []
        for idx, job in enumerate(self.jobs):
            t = threading.Thread(target=self.run_job, args=(job, idx + 1))
            t.start()
            threads.append(t)
        [x.join() for x in threads]
        return sum([x.result.exit_code for x in self.jobs]) > 0

    def run_job(self, job, jobnum):
        next_notify = 0
        with in_progress_file(f"{self.backupdir}/{jobnum}.{job.name}.log") as tlogf:
            def infolog(*args):
                print(f":: [{datetime.now()}]", *args, file=tlogf, flush=True)
            while job_deps := [x for x in job.deps if not x.result]:
                if next_notify == 0:
                    infolog(f"waiting for {[x.name for x in job_deps]} (checking every 1 second)")
                elif int(time.time()) % next_notify == 0:
                    infolog(f"waiting for {[x.name for x in job_deps]} (next update in {next_notify} seconds)")
                next_notify = min(next_notify + 30, 900)  # min freq is 15 min = 900 sec
                time.sleep(1)
            infolog(f"starting job {jobnum}: {job}")
            info(f"{jobnum}: {job}")
            job.run(tlogf)
            infolog(f"finished job {jobnum}: {job}")
        info(f"{jobnum}: {job.result}")
        if job.max_time and job.result == 124:
            info(f":: timeout triggered because job exceeded max time of {job.max_time}")
        self.write_summary()

    def get_job(self, name: str) -> Optional[Job]:
        for job in self.jobs:
            if job.name == name:
                return job
        return None

    def format_results(self) -> str:
        jobs = self.jobs
        out = []
        out.append(f'Summary for Job Group "{self.name}"\n')

        template = "{flag:<4}  {num:>3}  {exit_code:>4}  {elapsed_time:<15}  {name}"
        out.append(template.format(flag="FLAG", num="JOB", name="JOB NAME", exit_code="EXIT", elapsed_time="ELAPSED"))

        for idx, job in enumerate(jobs):
            d = dict(flag='', num=idx + 1, name=job.name)
            if job.result:
                d['elapsed_time'] = str(job.result.elapsed_time)
                d['exit_code'] = job.result.exit_code
                d['flag'] = '!' if job.result.exit_code != 0 else ''
            else:
                d['elapsed_time'] = 'running' if job.logpath else 'queued'
                d['exit_code'] = ''

            out.append(template.format(**d))

        if self.end_time:
            elapsed = self.end_time - self.start_time
            out.append(f"\n{self.started_jobs} jobs total in {str(elapsed)}")
            if self.failed_jobs is None or self.failed_jobs > 0:
                out.append(f"{self.failed_jobs} jobs failed")

        return "\n".join(out)

    def write_summary(self):
        # this function is called asynchronously whenever a job ends, use a mutex to only allow one to write at a time
        with self.mutex:
            with open(f"{self.backupdir}/summary.log", "wt") as f:
                print(self.format_results(), file=f)


def run_shell(*args, echo=False, outputf=subprocess.STDOUT, cwd=None) -> RunResult:
    """Run command. Never raises an exception. Returns -1 exit_code on
    FileNotFound, else returns stdout and stderr combined together as output
    and sets exitcode."""

    def log(*args):
        print(*args, file=outputf)

    result = {}
    result['command'] = [str(x) for x in args]
    result['cwd'] = cwd
    result['start_time'] = datetime.now()

    try:
        proc = subprocess.Popen(result['command'], stdout=outputf, stderr=subprocess.STDOUT, universal_newlines=True, cwd=cwd)
        proc.wait()
        result['exit_code'] = proc.returncode
    except (FileNotFoundError, OSError) as e:
        result['exit_code'] = -1
        log(str(e))

    result['end_time'] = datetime.now()
    result['elapsed_time'] = result['end_time'] - result['start_time']

    log(":: RunResult")
    for k, v in result.items():
        log(f":: {k:<12}: {v}")

    return RunResult(**result)


@contextmanager
def in_progress_file(final_log: str):
    """Creates a temporary called by prepending , to the beginning of
    final_log, then returns file handle. When done, renames temporary log to
    final_log."""
    dirname, basename = os.path.split(final_log)
    basename = "," + basename
    temp_path = os.path.join(dirname, basename)
    f = open(temp_path, "wt")
    try:
        yield f
    finally:
        f.close()
        os.rename(temp_path, final_log)


@contextmanager
def in_progress_dir(final_path: str):
    """Similar to in_progress_file but for directories."""
    dirname, basename = os.path.split(final_path)
    basename += ".running"
    temp_path = os.path.join(dirname, basename)
    os.makedirs(temp_path)
    try:
        yield temp_path
    finally:
        os.rename(temp_path, final_path)
