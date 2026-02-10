#!/usr/bin/env python3

import argparse
import importlib
import json
import logging
import os
import pathlib
import pkgutil
import platform
import sys

import benchmark


def run_benchmarks(search_dirs):
    # Step 1: Load from search dirs and then transform into a set of benchmarks to run
    benchmarks = set()
    for finder, name, is_pkg in pkgutil.iter_modules(search_dirs):
        try:
            sys.path.insert(0, finder.path)
            mod = importlib.import_module(name)
            for k, v in mod.__dict__.items():
                if isinstance(v, type):
                    logging.info("{}: {}".format(k, v))
                    benchmarks.add(v)
            sys.path = sys.path[1:]
        except Exception as e:
            logging.error("Failed to import module {}: {}".format(name, e))

    # @TODO: Filter benchmarks
    # @TODO: How many times should each be run.
    results = dict()
    for benchmark in benchmarks:
        results[benchmark.__name__] = run_benchmark(benchmark)

    print(json.dumps(results))


def run_benchmark(cls):
    benchmark = cls()
    metrics = cls.metrics()
    metadata = get_generic_metadata() | cls.metadata()
    config = {
        "runs": 10,
    }
    run_results = list()
    # @TODO: params & config
    benchmark.setup()
    for i in range(0, config["runs"]):
        logging.info("Running {} iter {}".format(cls, i + 1))
        benchmark.pre_run()
        run_results.append(benchmark.run())
        benchmark.post_run()

    benchmark.teardown()
    flat_result = dict()
    for result in run_results:
        for k, v in result.items():
            if k not in metrics:
                logging.warning(
                    "{} iter {} returned a metric '{}' not described by metrics classback".format(
                        cls, iter, k
                    )
                )

            if k not in flat_result:
                flat_result[k] = list()

            flat_result[k].append(v)

    return {
        "version": cls.version,
        "metrics": metrics,
        "metadata": metadata,
        "data": flat_result,
        "config": config,
    }


def get_generic_metadata():
    return {
        "platform": dict(
            zip(
                ("system", "node", "release", "version", "machine", "processor"),
                platform.uname(),
            )
        ),
        "processor": get_processor(),
        "nproc": os.cpu_count(),
        "cpu_online": get_cpu_online(),
        "cpu_possible": get_cpu_possible(),
        "memory_MiB": get_memory(),
        "os-release": get_os_release(),
    }


def get_cpu_possible():
    with open("/sys/devices/system/cpu/possible") as f:
        return f.readlines()[0].strip()


def get_cpu_online():
    with open("/sys/devices/system/cpu/online") as f:
        return f.readlines()[0].strip()


def get_processor():
    with open("/proc/cpuinfo", "r") as f:
        for line in f.readlines():
            if line.startswith("model name"):
                return line.split(":")[1].strip()


def get_memory():
    with open("/proc/meminfo") as f:
        for line in f.readlines():
            if line.startswith("MemTotal:"):
                return int(line.split(":")[1].strip().split(" ")[0]) / 1024.0


def get_os_release():
    data = dict()
    with open("/etc/os-release") as f:
        for line in f.readlines():
            k, v = line.strip().split("=")
            data[k] = v.strip('"')

    return data


if __name__ == "__main__":
    logging.basicConfig()
    sys.exit(run_benchmarks([pathlib.Path("benchmarks").absolute()]))
