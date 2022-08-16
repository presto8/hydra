import builtins
import inspect
import os
import shutil
import sys
import time
from collections import Counter, OrderedDict
from typing import Optional


def dprint(*args, **kwargs):
    caller = inspect.stack()[1]
    builtins.print(f'\r<{caller.function}:{caller.lineno}>', *args, '\033[K', **kwargs, file=sys.stderr)


def timestamp(path: os.PathLike) -> int:
    return os.lstat(path).st_ctime_ns


class OrderedCounter(Counter, OrderedDict):
    'Counter that remembers the order elements are first encountered'

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, OrderedDict(self))

    def __reduce__(self):
        return self.__class__, (OrderedDict(self),)


class StatusKeeper:
    """A Counter that displays ephemeral status messages for all counter
    operations as well as permanent messages for certain counter types. In
    printzero mode, only paths are printed and ephemeral messages are not
    shown."""
    def __init__(self, preseed=None, total_files_expected=None, log=None, print0=False, ephemeral_reasons=""):
        self.log = log
        self.print0 = print0
        self.c = OrderedCounter()
        if preseed:
            self.preseed(preseed)
        self.total_files_expected = total_files_expected
        self.progress_count = 0
        self.ephemeral_reasons = ephemeral_reasons.split()
        self.is_tty = sys.stdout.isatty()
        self.tty_cols, _ = shutil.get_terminal_size()
        self.time_start = time.time()

    def preseed(self, preseed: list):
        self.c.update({x: 0 for x in preseed})

    def __call__(self, reason, path, highlight=None, flags="", extra: Optional[str] = None, coverage=None):
        self.c[reason] += 1
        try:
            path.encode()
        except UnicodeEncodeError:
            path = path.encode('utf8', 'surrogateescape')
        if self.print0:
            self.print(path, end='\0')
            return
        if '\r' in path:
            path = path.replace('\r', r"$'\r'")
        if '\n' in path:
            path = path.replace('\n', r"$'\n'")
        # if highlight and self.is_tty:
        #     path = utils.highlight(path, highlight)
        extra = f" {extra}" if extra else ""
        cov = f"[{coverage}] " if coverage is not None else ""
        mesg = f"{reason:<16.16} {cov}{path}{extra}"
        if flags:
            mesg += " " + flags
        if reason in self.ephemeral_reasons:
            self.ephemeral(mesg, log=True)
        else:
            self.ephemeral()
            self.print(mesg)

    def print(self, mesg, ephemeral=False, log=True, **nargs):
        if ephemeral:
            print('\r' + mesg + '\033[K\r', end='', flush=True, file=sys.stderr)
            stderr = True
        else:
            print(mesg, **nargs)
            stderr = nargs.get('file', None) == sys.stderr
        if log and self.log:
            self.log(stderr, mesg)

    def ephemeral(self, *args, log=False):
        mesg = " ".join(args)
        if self.is_tty:
            mesg = mesg[:self.tty_cols - 1]
            self.print(mesg, ephemeral=True, log=log)

    def progress(self, path, step=1):
        self.progress_count += step
        last = f"/{self.total_files_expected}" if self.total_files_expected else ""
        self.ephemeral(f"[{self.progress_count}{last}] {path}")

    def progress_percent(self, step=1, mesg=None):
        self.progress_count += step
        pct = 100 * self.progress_count / self.total_files_expected
        mesg = " " + mesg if mesg else ""
        self.ephemeral(f"[{self.progress_count}/{self.total_files_expected}] {pct:0.1f}%{mesg}", log=False)

    def progress_rate(self, mesg=None):
        self.progress_count += 1
        rate = self.progress_count / (time.time() - self.time_start)
        self.ephemeral(f"[{self.progress_count}][{int(rate)} files/sec] {mesg}", log=False)

    def print_stats(self):
        if self.total_files_expected:
            self.c['files'] = self.total_files_expected
            remaining = self.total_files_expected - self.progress_count
            if remaining > 0:
                self.c['unprocessed'] = remaining

        for ok_reason in "stat-updated fault-cleared found".split():
            if self.c[ok_reason]:
                self.c['ok'] += self.c[ok_reason]

        if num_faults := self.num_faults():
            self.c['faulted'] = num_faults

        s = []
        for label, count in self.c.items():
            s.append(f"{count:,} {label}")

        if not sys.stdout.isatty():
            fault_conditions = ['changed' in self.c, 'missing' in self.c]
            if not any(fault_conditions):
                return

        self.ephemeral()
        self.print("; ".join(s), file=sys.stderr)

    def __del__(self):
        if self.c:
            self.print_stats()

    def num_faults(self, exclude_unknown=False):
        fault_list = "hash-changed missing lost".split()
        if not exclude_unknown:
            fault_list.append("unknown")
        return sum([self.c[x] for x in fault_list])
