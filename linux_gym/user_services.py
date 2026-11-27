"""Transient systemd exercises in the learner's existing user manager."""
import re
import secrets
import subprocess
from functools import lru_cache

OPERATIONS = {'service_start', 'service_stop', 'timer_run'}
UNIT_PATTERN = re.compile(r'gym-practice-[a-f0-9]{12}')


def systemctl(*args):
    return subprocess.run(['systemctl', '--user', *args], capture_output=True,
                          text=True, timeout=8)


@lru_cache(maxsize=1)
def available():
    try:
        return systemctl('show-environment').returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def prepare(task, root):
    unit = 'gym-practice-' + secrets.token_hex(6)
    task['unit'] = unit
    (root / '.user-unit').write_text(unit)
    op = task['operation']
    if op == 'timer_run':
        return (f'Create a transient user timer {unit}.timer, due once in 10 to 30 seconds. '
                f'Have its service create the marker {root / "fired"} with /usr/bin/touch. '
                'Allow the timer to elapse before you check.')
    if op == 'service_start':
        return (f'Run /usr/bin/sleep 1200 as a transient user service named {unit}.service. '
                f'Set its working directory to {root} and leave it running.')
    subprocess.run(
        ['systemd-run', '--user', '--quiet', '--unit', unit,
         '--working-directory', str(root), '/usr/bin/sleep', '1200'],
        capture_output=True, timeout=8, check=True,
    )
    return f'Stop the running transient user service {unit}.service using systemctl.'


def check(task, root):
    unit = task['unit']
    op = task['operation']
    if op == 'timer_run':
        timer = systemctl('show', '--property=LastTriggerUSec', '--value', unit + '.timer')
        return (timer.returncode == 0 and timer.stdout.strip() not in ('', 'n/a', '0')
                and (root / 'fired').is_file())
    if op == 'service_stop':
        state = systemctl('show', '--property=ActiveState', '--value', unit + '.service')
        return state.returncode == 0 and state.stdout.strip() == 'inactive'
    state = systemctl('show', '--property=ActiveState,MainPID,WorkingDirectory,ExecStart',
                      unit + '.service')
    fields = dict(line.split('=', 1) for line in state.stdout.splitlines() if '=' in line)
    return (
        state.returncode == 0 and fields.get('ActiveState') == 'active'
        and int(fields.get('MainPID', '0')) > 1
        and fields.get('WorkingDirectory') == str(root)
        and 'argv[]=/usr/bin/sleep 1200 ;' in fields.get('ExecStart', '')
    )


def cleanup(workspace):
    for marker in workspace.glob('ex[0-9][0-9]/.user-unit'):
        try:
            unit = marker.read_text()
            if UNIT_PATTERN.fullmatch(unit):
                systemctl('stop', unit + '.timer', unit + '.service')
        except (OSError, subprocess.TimeoutExpired):
            continue
