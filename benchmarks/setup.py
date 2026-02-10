#!/usr/bin/env python3

import pathlib
import signal
import subprocess
import sys
import time

sys.path.insert(0, pathlib.Path(__file__).parents[1] / "src")
import benchmark


class FirstCommand(benchmark.BenchmarkBase):

    version = 1

    def __init__(self):
        self.time_started = None
        self.time_sig_received = None

    def metrics():
        return {
            "time_to_sigusr1": {
                "unit": "seconds",
                "interpretation": "lower is better",
                "description": "The time between starting lttng-sessiond and when the parent process receives SIGUSR1 to signal that the sessiond daemon is ready",
            }
        }

    def handle_sigusr1(self, signum, frame):
        self.time_sig_received = time.monotonic()

    def pre_run(self):
        signal.signal(signal.SIGUSR1, self.handle_sigusr1)

    def post_run(self):
        signal.signal(signal.SIGUSR1, signal.SIG_DFL)

    def run(self):
        self.time_sig_received = None
        self.time_started = time.monotonic()
        # Likely it is better to drop into a C~ helper binary here to avoid
        # measuring the python subprocess overhead.
        proc = subprocess.Popen(["lttng-sessiond", "--sig-parent"])
        while self.time_sig_received is None:
            continue

        proc.terminate()
        proc.wait()
        return {
            "time_to_sigusr1": self.time_sig_received - self.time_started,
        }


class SessionSetupTime(benchmark.BenchmarkBase):
    version = 1

    def __init__(self):
        self.sessiond = None

    def metrics():
        return {
            "session_load_time": {
                "unit": "seconds",
                "interpretation": "lower is better",
                "description": "The time it takes to execute `lttng load` with all sessions from the input file",
            }
        }

    def handle_sigusr1(self, signum, frame):
        self.ready = True

    def pre_run(self):
        self.ready = False
        signal.signal(signal.SIGUSR1, self.handle_sigusr1)
        self.sessiond = subprocess.Popen(["lttng-sessiond", "--sig-parent"])
        while not self.ready:
            continue
        signal.signal(signal.SIGUSR1, signal.SIG_DFL)

    def post_run(self):
        if self.sessiond:
            self.sessiond.terminate()
            self.sessiond.wait()
            self.sessiond = None

    def run(self, session_file=pathlib.Path(__file__).parents[0] / "data/session.lttng"):
        t0 = time.monotonic()
        p = subprocess.Popen(
            ["lttng", "load", "--input-path", str(session_file), "--all"], stdout=sys.stderr)
        p.wait()
        t1 = time.monotonic()
        return {
            'session_load_time': t1 - t0,
        }


class SessionStartTime(benchmark.BenchmarkBase):
    pass
