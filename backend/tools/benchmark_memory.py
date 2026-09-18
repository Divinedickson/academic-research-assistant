import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def process_tree_rss(process):
    try:
        parent = psutil.Process(process.pid)
        return parent.memory_info().rss + sum(
            child.memory_info().rss for child in parent.children(recursive=True)
        )
    except psutil.Error:
        return 0


def main():
    process = subprocess.Popen(
        [sys.executable, str(BACKEND_ROOT / 'tools' / 'benchmark_worker.py')],
        cwd=BACKEND_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    state = {'stage': 'startup', 'peak': 0, 'overall_peak': 0}
    peaks = {}

    def sample():
        while process.poll() is None:
            rss = process_tree_rss(process)
            state['peak'] = max(state['peak'], rss)
            state['overall_peak'] = max(state['overall_peak'], rss)
            time.sleep(0.02)

    monitor = threading.Thread(target=sample, daemon=True)
    monitor.start()
    for line in process.stdout:
        event = json.loads(line)
        peaks[state['stage']] = state['peak']
        state['stage'] = event['stage']
        state['peak'] = process_tree_rss(process)
        event['rss_after_mb'] = round(state['peak'] / 1024 / 1024, 2)
        print(json.dumps(event))

    stderr = process.stderr.read()
    return_code = process.wait()
    monitor.join()
    peaks[state['stage']] = state['peak']
    print(json.dumps({
        'peak_by_completed_stage_mb': {
            key: round(value / 1024 / 1024, 2) for key, value in peaks.items()
        },
        'overall_peak_mb': round(state['overall_peak'] / 1024 / 1024, 2),
        'return_code': return_code,
    }, indent=2))
    if stderr:
        print(stderr, file=sys.stderr)
    raise SystemExit(return_code)


if __name__ == '__main__':
    main()
