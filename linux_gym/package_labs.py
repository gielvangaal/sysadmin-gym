"""Real package operations with an exercise-local repository and RPM database."""
import configparser
import shutil
import subprocess
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent.parent / 'fixtures' / 'rpm'
OPERATIONS = {'rpm_install', 'rpm_upgrade', 'rpm_remove', 'dnf_repo'}


def dnf_config(root):
    return (
        '[main]\n'
        f'reposdir={root / "repos"}\n'
        f'cachedir={root / "cache"}\n'
        f'persistdir={root / "persist"}\n'
        f'logdir={root / "logs"}\n'
        'plugins=0\n'
    )


def rpm_command(root):
    return ['rpm', '--dbpath', str(root / 'rpmdb'),
            '--define', f'_tmppath {root / "tmp"}']


def run_command(*args, check=True):
    return subprocess.run(args, check=check, text=True, capture_output=True, timeout=30)


def prepare(task, root):
    shutil.copytree(FIXTURE, root / 'repo')
    for name in ('rpmdb', 'tmp', 'payload', 'repos'):
        (root / name).mkdir()
    repo = root / 'repo'
    op = task['operation']
    if op == 'dnf_repo':
        (root / 'dnf.conf').write_text(dnf_config(root))
        (root / 'repos/gym.repo').write_text('[gym-local]\nname=Gym packages\n'
                                             'baseurl=file:///old-path\nenabled=0\n')
        return (f'Repair the DNF repository gym-local in {root / "repos"}. Point it at {repo}, '
                f'enable it, and verify both packages and repository metadata using {repo / "KEY.asc"}. '
                f'Use {root / "dnf.conf"} as the DNF configuration and release version 10. '
                'The repository should list both gym-workload versions.')
    rpm = rpm_command(root)
    run_command('rpmkeys', '--dbpath', str(root / 'rpmdb'), '--import', str(repo / 'KEY.asc'))
    if op != 'rpm_install':
        package = repo / 'gym-workload-1.0-1.noarch.rpm'
        run_command('rpmkeys', '--dbpath', str(root / 'rpmdb'), '--checksig', str(package))
        run_command(*rpm, '-i', '--prefix', str(root / 'payload'), str(package))
    goals = {
        'rpm_install': f'Install the signed gym-workload 1.0 package from {repo}.',
        'rpm_upgrade': f'Upgrade the installed gym-workload to the signed version 2.0 from {repo}.',
        'rpm_remove': 'Remove the installed gym-workload package and its payload.',
    }
    return (f'{goals[op]} Use the RPM database {root / "rpmdb"}, the package prefix '
            f'{root / "payload"}, and {root / "tmp"} for RPM temporary files. '
            'Keep every transaction within this exercise.')


def check(task, root):
    op = task['operation']
    if op == 'dnf_repo':
        if (root / 'dnf.conf').read_text() != dnf_config(root):
            return False
        repo = configparser.ConfigParser(interpolation=None)
        try:
            repo.read(sorted((root / 'repos').glob('*.repo')))
            expected = {'baseurl': (root / 'repo').as_uri(), 'enabled': '1', 'gpgcheck': '1',
                        'repo_gpgcheck': '1', 'gpgkey': (root / 'repo/KEY.asc').as_uri()}
            if repo.sections() != ['gym-local'] or any(
                repo['gym-local'].get(key) != value for key, value in expected.items()
            ):
                return False
            if repo.defaults() or set(repo['gym-local']) - (set(expected) | {'name'}):
                return False
        except configparser.Error:
            return False
        dnf = run_command('dnf', '-q', '-y', '-c', str(root / 'dnf.conf'), '--releasever=10',
                          'repoquery', '--queryformat', '%{version}', 'gym-workload', check=False)
        return dnf.returncode == 0 and set(dnf.stdout.splitlines()) >= {'1.0', '2.0'}

    packages = run_command(*rpm_command(root), '-qa', '--queryformat', '%{NAME} %{VERSION}\n',
                           check=False)
    if packages.returncode:
        return False
    versions = [line.split()[1] for line in packages.stdout.splitlines()
                if line.startswith('gym-workload ')]
    marker = root / 'payload/marker.txt'
    if op == 'rpm_remove':
        return not versions and not marker.exists()
    version = '1.0' if op == 'rpm_install' else '2.0'
    return (
        versions == [version]
        and marker.read_text() == f'gym payload {version}\n'
    )
