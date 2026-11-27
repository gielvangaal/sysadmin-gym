"""Offline configuration recovery with real Linux tools and isolated paths."""
import configparser
import ipaddress
import re
import shlex
import subprocess
from pathlib import Path

# These fixtures represent configuration captured from a lab machine.
RECOVERY_FILES = {
    'journal': (
        'journald.conf', '[Journal]\nStorage=volatile\nMaxRetentionSec=0\n',
        'Configure persistent journal storage and cap retention at {number} days.',
        {'Journal': {'Storage': 'persistent', 'MaxRetentionSec': '{number}day'}},
    ),
    'journal_rotation': (
        'journald.conf', '[Journal]\nStorage=persistent\nSystemMaxUse=4G\nSystemMaxFileSize=512M\n',
        'Maintain persistent storage, limit journal disk usage to {number}M, '
        'and rotate individual journal files at 8M.',
        {'Journal': {'Storage': 'persistent', 'SystemMaxUse': '{number}M', 'SystemMaxFileSize': '8M'}},
    ),
    'timer': (
        'audit.timer', '[Timer]\nOnCalendar=weekly\nPersistent=false\n',
        'Schedule audit.service daily at 03:{number:02d}:00 and catch up on missed runs.',
        {'Timer': {'OnCalendar': '*-*-* 03:{number:02d}:00', 'Persistent': 'true',
                   'Unit': 'audit.service'}},
    ),
    'nfs_mount': (
        'fstab', 'archive.invalid:/reports /mnt/reports nfs ro,vers=3 0 0\n',
        'Repair the read-only /mnt/reports entry for NFSv4 from archive.invalid:/reports. '
        'Mark it as requiring network access. Set dump and pass to zero.',
        'archive.invalid:/reports /mnt/reports nfs ro,vers=4,_netdev 0 0',
    ),
    'swap_fstab': (
        'fstab', 'UUID=5cfd0e5f-9bae-4fce-9897-56f987ce2416 /mnt/scratch xfs defaults 0 0\n',
        'Repair the entry for the existing UUID so it activates as swap at boot with defaults.',
        'UUID=5cfd0e5f-9bae-4fce-9897-56f987ce2416 none swap defaults 0 0',
    ),
    'boot_mount': (
        'fstab', 'LABEL=optional /mnt/archive xfs defaults 0 0\n',
        'Keep the optional XFS archive mount enabled, but allow boot to finish if the disk is absent.',
        'LABEL=optional /mnt/archive xfs defaults,nofail 0 0',
    ),
    'tmpfiles': (
        'scratch.conf', 'd /var/tmp/gym-scratch 0777 root root -\n',
        'Configure systemd-tmpfiles to create /var/tmp/gym-scratch owned by root:root, '
        'with mode 0750 and cleanup after {number} days.',
        'd /var/tmp/gym-scratch 0750 root root {number}d',
    ),
}


def check_recovery_file(path, requirements, number):
    if isinstance(requirements, dict):
        parsed = configparser.ConfigParser(interpolation=None)
        try:
            parsed.read_string(path.read_text())
        except configparser.Error:
            return False
        return all(
            parsed.get(section, key, fallback=None) == value.format(number=number)
            for section, settings in requirements.items()
            for key, value in settings.items()
        )

    records = [
        line.split('#', 1)[0].split()
        for line in path.read_text().splitlines()
    ]
    records = [fields for fields in records if fields]
    expected = requirements.format(number=number).split()
    if path.name == 'fstab' and len(records) == 1 and len(records[0]) == 6:
        records[0][3] = sorted(records[0][3].split(','))
        expected[3] = sorted(expected[3].split(','))
    return records == [expected]


def prepare(t):
    root=Path(t['target']); root.mkdir()
    op=t['operation']; n=t['number']; result=t['result']
    if op in RECOVERY_FILES:
        filename, initial, goal, _ = RECOVERY_FILES[op]
        path = root / filename
        path.write_text(initial)
        instruction = f'{goal.format(number=n)} Edit the offline fixture at {path}.'
    elif op == 'ssh_policy':
        host_key = root / 'ssh_host_ed25519_key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(host_key)],
                       check=True, capture_output=True, timeout=5)
        path = root / 'sshd_config'
        path.write_text(f'HostKey "{host_key}"\nPermitRootLogin yes\nPasswordAuthentication yes\n'
                        'KbdInteractiveAuthentication yes\nPubkeyAuthentication no\n')
        instruction = (f'Repair {path} so regular users can authenticate with public keys. '
                       'Disable direct root login, password and keyboard-interactive authentication. '
                       'Preserve the practice host key and validate the offline configuration.')
    elif op == 'autofs_map':
        (root / 'auto.master').write_text('/srv/old /etc/auto.obsolete\n')
        (root / 'auto.projects').write_text('# Project shares\n')
        t['timeout'] = 40 + n
        instruction = (f'In the offline autofs fixtures in {root}, configure /srv/projects as '
                       f'an indirect mount point using /etc/auto.projects and a {t["timeout"]} second '
                       'idle timeout. Make the build subdirectory mount vault.invalid:/exports/build '
                       'using read-only NFSv4.')
    elif op=='repo':
        repo=root/'repos'; repo.mkdir()
        (root/'mirror').mkdir()
        url=(root/'mirror').as_uri()
        t['url']=url
        if n%2==0:
            (repo/'gym.repo').write_text('[gym-local]\nname=Gym local\nbaseurl=file:///invalid\nenabled=0\ngpgcheck=1\n')
        instruction=f'{"Repair" if n%2==0 else "Create"} a DNF repository definition in {repo} with ID gym-local, name Gym local, baseurl {url}, enabled=1 and gpgcheck=1. Do not change system repositories. This fixture has no package metadata; do not install packages.'
    elif op=='dns':
        (root/'resolv.conf').write_text('nameserver 192.0.2.254\nsearch wrong.invalid\n')
        t['dns']=f'192.0.2.{n+10}'
        instruction=f'A captured resolver configuration in {root}/resolv.conf points to the wrong DNS server and search domain. Repair the file so the only nameserver is {t["dns"]} and the search domain is gym.test. This is an offline configuration exercise; leave the live resolver unchanged.'
    elif op in ('network_dual', 'network_route'):
        host = n + 30
        t['address'] = f'192.0.2.{host}/24'
        t['secondary'] = f'198.51.100.{host}/24'
        t['destination'] = f'203.0.113.{(n % 4) * 64}/26'
        t['gateway'] = '192.0.2.1'
        profile = root / 'repair.nmconnection'
        profile.touch(mode=0o600)
        profile.write_text('[connection]\nid=repair\ntype=ethernet\nautoconnect=false\n\n'
                           '[ipv4]\nmethod=manual\nnever-default=true\n'
                           f'address1={t["address"]}\n')
        if op == 'network_dual':
            goal = f'Assign both {t["address"]} and {t["secondary"]} to the Ethernet profile.'
        else:
            goal = f'Keep {t["address"]} and add a route to {t["destination"]} via {t["gateway"]}.'
        instruction = (f'{goal} Repair {profile}. Keep autoconnect disabled and the default route '
                       'unset. Leave the profile offline.')
    elif op=='network':
        t['address']=f'192.0.2.{n+10}/24'
        instruction=f'Create an inactive NetworkManager keyfile at {root}/gym.nmconnection for an Ethernet profile named gym-training with manual IPv4 address {t["address"]}, no gateway, no DNS, and autoconnect disabled. Do not import or activate the profile. Use mode 600.'
    elif op=='firewall':
        t['port']=18000+n
        instruction=f'Prepare a firewalld zone XML file at {root}/gym.xml allowing TCP port {t["port"]} and the ssh service, and no other ports or services. Do not modify the live firewall.'
    elif op=='service':
        t['port']=18000+n
        (root/'gym.service').write_text('[Unit]\nDescription=Gym service\n[Service]\nType=oneshot\nExecStart=/nonexistent/gym\n[Install]\nWantedBy=multi-user.target\n')
        instruction=f'Repair {root}/gym.service so it is a oneshot service executing /usr/bin/true and is installable under multi-user.target. Do not install or start it on the host.'
    elif op=='fstab':
        (root/'fstab').write_text('# training fixture\n')
        (root/'mount').mkdir()
        t['size']=16+n
        instruction=f'Add an entry to {root}/fstab for a tmpfs mounted at {root}/mount with size={t["size"]}M, nosuid,nodev and mode=0750, dump and pass both 0. Do not modify /etc/fstab or mount anything.'
    else:
        raise ValueError('Unknown configuration exercise')
    t['description']=instruction
    return t

def check(t):
    root=Path(t['target']); op=t['operation']
    if op in RECOVERY_FILES:
        filename, _, _, requirements = RECOVERY_FILES[op]
        return check_recovery_file(root / filename, requirements, t['number'])
    if op == 'ssh_policy':
        path = root / 'sshd_config'
        config = [
            re.split(r'\s*=\s*|\s+', line.strip(), maxsplit=1)
            for line in path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')
        ]
        # Limit this single-profile fixture to global SSH authentication settings.
        allowed = {
            'hostkey', 'permitrootlogin', 'passwordauthentication',
            'kbdinteractiveauthentication', 'challengeresponseauthentication',
            'pubkeyauthentication', 'authenticationmethods', 'usepam',
        }
        if any(len(line) != 2 or line[0].lower() not in allowed for line in config):
            return False
        keys = [shlex.split(value, comments=True) for option, value in config
                if option.lower() == 'hostkey']
        if keys != [[str(root / 'ssh_host_ed25519_key')]]:
            return False
        process = subprocess.run(['sshd', '-T', '-f', str(path)],
                                 capture_output=True, text=True, timeout=5)
        if process.returncode:
            return False
        settings = dict(line.split(None, 1) for line in process.stdout.splitlines() if ' ' in line)
        return (
            settings.get('permitrootlogin') == 'no'
            and settings.get('passwordauthentication') == 'no'
            and settings.get('kbdinteractiveauthentication') == 'no'
            and settings.get('pubkeyauthentication') == 'yes'
            and settings.get('hostbasedauthentication') == 'no'
            and settings.get('gssapiauthentication', 'no') == 'no'
            and settings.get('authenticationmethods') in ('any', 'publickey')
        )
    if op == 'autofs_map':
        records = []
        for filename in ('auto.master', 'auto.projects'):
            lines = [
                line.split('#', 1)[0].split()
                for line in (root / filename).read_text().splitlines()
                if line.strip() and not line.lstrip().startswith('#')
            ]
            entry, = lines
            records.append(entry)
        master, share = records
        if master[:2] != ['/srv/projects', '/etc/auto.projects'] or master[2:] not in (
            [f'--timeout={t["timeout"]}'], ['--timeout', str(t['timeout'])]
        ):
            return False
        return (
            len(share) == 3
            and share[0] == 'build'
            and set(share[1].removeprefix('-').split(',')) in (
                {'ro', 'fstype=nfs4'}, {'ro', 'fstype=nfs', 'vers=4'}, {'ro', 'fstype=nfs', 'nfsvers=4'}
            )
            and share[2] == 'vault.invalid:/exports/build'
        )
    if op=='repo':
        cp=configparser.ConfigParser(interpolation=None)
        cp.read(sorted((root/'repos').glob('*.repo')))
        return cp.has_section('gym-local') and all(cp['gym-local'].get(k)==v for k,v in {'name':'Gym local','baseurl':t['url'],'enabled':'1','gpgcheck':'1'}.items())
    if op=='dns':
        lines=[l.split() for l in (root/'resolv.conf').read_text().splitlines() if l.strip() and not l.lstrip().startswith('#')]
        return [l for l in lines if l[0]=='nameserver']==[['nameserver',t['dns']]] and [l for l in lines if l[0]=='search']==[['search','gym.test']]
    if op in ('network_dual', 'network_route'):
        path = root / 'repair.nmconnection'
        profile = configparser.ConfigParser(interpolation=None)
        try:
            profile.read_string(path.read_text())
        except configparser.Error:
            return False
        connection = profile['connection']
        ipv4 = profile['ipv4']
        if (
            path.stat().st_mode & 0o777 != 0o600
            or connection['type'] not in ('ethernet', '802-3-ethernet')
            or connection.getboolean('autoconnect', fallback=True)
            or ipv4['method'] != 'manual'
            or not ipv4.getboolean('never-default', fallback=False)
            or ipv4.get('gateway')
        ):
            return False
        addresses = [
            str(ipaddress.IPv4Interface(value))
            for key, value in ipv4.items()
            if key.startswith('address') and key.removeprefix('address').isdigit()
        ]
        routes = [
            [field.strip() for field in value.split(',')]
            for key, value in ipv4.items()
            if key.startswith('route') and key.removeprefix('route').isdigit()
        ]
        if op == 'network_dual':
            return sorted(addresses) == sorted([t['address'], t['secondary']]) and not routes
        return (
            addresses == [t['address']]
            and len(routes) == 1
            and routes[0][:2] == [t['destination'], t['gateway']]
            and (len(routes[0]) == 2 or len(routes[0]) == 3 and routes[0][2].isdigit())
        )
    if op=='network':
        p=root/'gym.nmconnection'; cp=configparser.ConfigParser(interpolation=None); cp.read(p)
        return p.stat().st_mode&0o777==0o600 and cp['connection'].get('id')=='gym-training' and cp['connection'].get('type') in ('ethernet','802-3-ethernet') and cp['connection'].get('autoconnect')=='false' and cp['ipv4'].get('method')=='manual' and cp['ipv4'].get('address1')==t['address'] and not cp['ipv4'].get('gateway') and not cp['ipv4'].get('dns')
    if op=='firewall':
        import xml.etree.ElementTree as ET
        try: zone=ET.parse(root/'gym.xml').getroot()
        except ET.ParseError:return False
        return zone.tag=='zone' and zone.get('target','default')=='default' and [e.attrib for e in zone.findall('port')]==[{'port':str(t['port']),'protocol':'tcp'}] and [e.get('name') for e in zone.findall('service')]==['ssh'] and all(e.tag in ('short','description','port','service') for e in zone)
    if op=='service':
        cp=configparser.ConfigParser(interpolation=None); cp.read(root/'gym.service')
        return cp['Service'].get('Type')=='oneshot' and cp['Service'].get('ExecStart')=='/usr/bin/true' and cp['Install'].get('WantedBy')=='multi-user.target'
    if op=='fstab':
        lines=[l.split() for l in (root/'fstab').read_text().splitlines() if l.strip() and not l.lstrip().startswith('#')]
        return len(lines)==1 and len(lines[0])==6 and lines[0][:3]==['tmpfs',str(root/'mount'),'tmpfs'] and set(lines[0][3].split(','))>={f'size={t["size"]}M','nosuid','nodev','mode=0750'} and lines[0][4:]==['0','0']
    return False
