"""Live exercises whose kernel changes are confined to a throwaway namespace."""
import json
import os
import shlex
import stat
import subprocess
from functools import lru_cache

OPERATIONS = {'network_addrs', 'network_routing', 'tmpfs_mount'}
UNSHARE = ['unshare', '--user', '--map-root-user', '--mount', '--net', '--fork', '--kill-child']
OUTPUT_MARKER = '--- exercise outcome ---'


@lru_cache(maxsize=1)
def available():
    try:
        return subprocess.run(
            [*UNSHARE, '/usr/bin/true'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=3,
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def prepare(task, root):
    n = task['number']
    op = task['operation']
    script = root / 'exercise.sh'
    script.write_text('#!/bin/sh\n# Add your commands below.\n')
    prefix = shlex.join([*UNSHARE, '/bin/sh', str(script)])
    if op == 'tmpfs_mount':
        target = root / 'mount'
        target.mkdir()
        task['size'] = n
        goal = (f'Mount a tmpfs at {target} with size {n} MiB and nosuid,nodev. '
                f'While it is mounted, create {target / "ready"} containing "ready".')
    else:
        task['ipv4'] = [f'192.0.2.{n}/24', f'198.51.100.{n}/25']
        goal = (f'Bring up lo and assign the IPv4 addresses {task["ipv4"][0]} and {task["ipv4"][1]} '
                'to it, preserving the existing 127.0.0.1 address. No default route is required.')
        if op == 'network_routing':
            task['subnet'] = '203.0.113.0/26'
            task['ipv4'] = task['ipv4'][:1]
            goal = (f'Bring up lo with {task["ipv4"][0]} and route {task["subnet"]} through lo, '
                    f'using 192.0.2.{n} as its preferred source. Preserve 127.0.0.1.')
    return (f'{goal} Put the commands in {script}; Gym runs them in a fresh private namespace. '
            f'To try it yourself, use: {prefix}')


def check(task, root):
    script = root / 'exercise.sh'
    if not stat.S_ISREG(script.lstat().st_mode):
        return False
    op = task['operation']
    if op == 'tmpfs_mount':
        target = root / 'mount'
        probe = (
            'findmnt --json -o FSTYPE,OPTIONS --mountpoint "$2" && '
            'df --output=size -k "$2" | tail -n1 && cat "$2/ready"'
        )
    else:
        target = root
        probe = 'ip -j -4 addr show dev lo && ip -j -4 route show table main'
    # Set up and inspect from the same namespace. The namespace disappears
    # when the grading command exits, including after timeouts.
    result = subprocess.run(
        [*UNSHARE, '/bin/sh', '-ec',
         f'/bin/sh "$1" >/dev/null; printf "%s\\n" {shlex.quote(OUTPUT_MARKER)}; {probe}',
         'gym-probe', os.fspath(script), os.fspath(target)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=12,
    )
    if result.returncode:
        return False
    marker, _, output = result.stdout.partition(OUTPUT_MARKER + '\n')
    if marker or not output:
        return False
    decoder = json.JSONDecoder()
    data, end = decoder.raw_decode(output)
    trailing = output[end:].strip()
    if op == 'tmpfs_mount':
        entry, = data['filesystems']
        options = set(entry['options'].split(','))
        size, content = trailing.splitlines()
        return (
            entry['fstype'] == 'tmpfs' and {'nosuid', 'nodev'} <= options
            and int(size) == task['size'] * 1024 and content == 'ready'
        )
    loopback, = data
    routes = json.loads(trailing)
    actual = {f'{entry["local"]}/{entry["prefixlen"]}' for entry in loopback['addr_info']}
    if 'UP' not in loopback['flags'] or actual != {'127.0.0.1/8', *task['ipv4']}:
        return False
    if any(route.get('dst') == 'default' for route in routes):
        return False
    if op == 'network_addrs':
        return True
    return any(route.get('dst') == task['subnet'] and route.get('dev') == 'lo'
               and route.get('prefsrc') == task['ipv4'][0].split('/')[0] for route in routes)
