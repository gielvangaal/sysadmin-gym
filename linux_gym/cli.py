#!/usr/bin/env python3
"""Linux Gym v3 — stdlib-only RHEL CLI."""
import argparse, json, os, random, shutil, socket, subprocess, sys, tarfile, tempfile, time, ipaddress, math
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from .catalog import TASKS
from .adaptive import config, read_history, record, weight_for, summary
from .english import prompt_for, hint_for
ROOT=Path(__file__).resolve().parent.parent
WORK=ROOT/'workspace'; BACKUPS=ROOT/'backups'; PROGRESS=ROOT/'progress'/'legacy.json'; SESSION=ROOT/'session.json'
CATEGORIES={'permissions','files','shell','network','observe'}

def run(*cmd):
    return subprocess.run(cmd,capture_output=True,text=True)

def save_json(path,obj):
    temp=path.with_suffix('.tmp'); temp.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n'); temp.replace(path)

def load_json(path,default):
    try:return json.loads(path.read_text())
    except FileNotFoundError:return default

def rand_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0)); return s.getsockname()[1]

def snapshot():
    BACKUPS.mkdir(exist_ok=True)
    dest=BACKUPS/(time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns()%1000000000))
    dest.mkdir(mode=0o700)
    cmds={'ip-address':['ip','-br','address'],'ip-route':['ip','route'], 'dns':['cat','/etc/resolv.conf'], 'nmcli':['nmcli','-t','connection','show'], 'umask':['bash','-c','umask'], 'mounts':['findmnt'],'firewall':['firewall-cmd','--list-all']}
    for name,cmd in cmds.items():
        try:
            p=run(*cmd); (dest/f'{name}.txt').write_text((p.stdout or '')+('\n'+p.stderr if p.stderr else ''))
        except FileNotFoundError:(dest/f'{name}.txt').write_text('command unavailable\n')
    return dest

def seed_workspace():
    WORK.mkdir(exist_ok=True); (WORK/'results').mkdir(exist_ok=True)
    rng=random.Random(int(time.time_ns()))
    (WORK/'access.log').write_text(''.join(f'{rng.choice(["192.0.2.10","192.0.2.20","198.51.100.4","203.0.113.7","192.0.2.10"])} GET /health 200\n' for _ in range(40)))
    (WORK/'application.log').write_text(''.join(f'{s}: message {i}\n' for i,s in enumerate(['INFO','ERROR','WARNING','ERROR','INFO','ERROR','DEBUG','INFO','ERROR','WARNING'])))
    (WORK/'inventory.csv').write_text('alice:admin:100\nbob:user:250\ncharlie:user:180\n')
    (WORK/'source.txt').write_text('Linux Gym practice\n')
    (WORK/'tree').mkdir(exist_ok=True)
    for name in ('report.txt','report.log','notes.txt','archive.log'):(WORK/'tree'/name).write_text(name+'\n')
    (WORK/'tree'/'big.bin').write_bytes(b'X'*(1024*1024+100))
    (WORK/'web').mkdir(exist_ok=True)
    (WORK/'web'/'health.txt').write_text('linux-gym-ok\n')
    (WORK/'numbers.txt').write_text('20\n3\n100\n5\n12\n')

def choose_tasks(count,system):
    cfg=config(ROOT)
    history=read_history(ROOT)
    round_no=history['rounds']+1
    pool=[t for t in TASKS if t['group']!='system' and (not t.get('requires') or shutil.which(t['requires'])) and t['kind'] not in ('cpu','journal','block') and (t['group']!='tls' or shutil.which('openssl')) ]
    modules=cfg['modules']
    selected=[]
    # Explicit per-module quotas, with no duplicate exercise IDs.
    for module in modules:
        if not module.get('enabled',True) or round_no % module.get('every',1):
            continue
        available=[t for t in pool if t['group']==module['name']]
        for _ in range(min(module['count'],len(available))):
            options=[t for t in available if t['id'] not in {x['id'] for x in selected} and (t['kind'] not in ('move','signal') or not any(x['kind']==t['kind'] for x in selected))]
            if not options:break
            selected.append(pick(options,history,cfg))
    if len(selected)>count:
        # Keep explicit network quota and occasional TLS by trimming regular tasks.
        while len(selected)>count:
            idx=next((i for i in range(len(selected)-1,-1,-1) if selected[i]['group'] not in ('network','tls')),len(selected)-1)
            selected.pop(idx)
    while len(selected)<count:
        options=[t for t in pool if t['id'] not in {x['id'] for x in selected} and t['group'] in {m['name'] for m in modules if m.get('enabled',True)} and (t['kind'] not in ('move','signal') or not any(x['kind']==t['kind'] for x in selected))]
        if not options:break
        selected.append(pick(options,history,cfg))
    random.shuffle(selected)
    return selected

def pick(opts,history,cfg):
    weights=[weight_for(t,history,cfg) for t in opts]
    return random.choices(opts,weights=weights,k=1)[0]

def prepare(t,i,port,iface):
    rng=random.Random(i*199+int(time.time_ns()))
    t=dict(t); kind=t['kind']; target=WORK/f'ex{i:02}'
    t['target']=str(target); t['result']=str(WORK/'results'/f'ex{i:02}.txt'); t['port']=port
    t['iface']=iface
    t['variant']=t.get('variant','A')
    desc=t['description']
    if kind in ('copy','move','hardlink','symlink','compare'):
        t['source']=str(WORK/f'ex{i:02}-source.txt')
        Path(t['source']).write_text('Linux Gym practice\n')
    if kind=='practical':
        from .practical import prepare as prepare_practical
        return prepare_practical(t)
    if kind=='config_recovery':
        from .config_recovery import prepare as prepare_config
        return prepare_config(t)
    if kind=='file_audit':
        from .file_audit import prepare as prepare_audit
        return prepare_audit(t)
    if kind in ('mode','symbolic'):
        if t.get('is_dir'):target.mkdir()
        else:target.write_text('practice\n')
        target.chmod(0o777 if target.is_dir() else 0o666)
        desc=desc.format(target=target)
    elif kind=='umask':
        t['file']=str(target/'new.txt');t['directory']=str(target/'newdir'); target.mkdir()
        desc=desc+f'\n   Bestand: {t["file"]}\n   Directory: {t["directory"]}'
    elif kind in ('make_dir','remove_file','empty_file','nested_dir','content_search'):
        if kind=='remove_file':target.write_text('obsolete\n')
        if kind=='empty_file':target.write_text('to be cleared\n')
        if kind=='content_search':
            desc=desc.format(tree=WORK/'tree',result=t['result'])
        else:desc=desc.format(target=target)
    elif t['group']=='files':
        src=Path(t.get('source',WORK/'source.txt')); tree=WORK/'tree'; result=t['result'];
        texts={'copy':f'Kopieer {src} naar {result}.','move':f'Verplaats {src} naar {result}.','hardlink':f'Maak een hardlink {result} naar {src}.','symlink':f'Maak een symbolische link {result} naar {src}.','find_name':f'Zoek onder {tree} alle .log-bestanden en schrijf de BESTANDSNAMEN (één per regel, gesorteerd) naar {result}.','find_size':f'Zoek bestanden onder {tree} groter dan 1 MiB en schrijf hun namen naar {result}.','archive':f'Maak een gzip-tararchief {result} van de directory tree uit workspace.','extract':f'Pak het archief {WORK/"sample.tar.gz"} uit naar {target} (maak de directory eerst).','compare':f'Vergelijk source.txt met copy.txt en sla alleen het woord gelijk of verschillend op in {result}.','count_lines':f'Tel regels in application.log en sla uitsluitend het getal op in {result}.'}
        desc=texts[kind]
        if kind=='extract':
            with tarfile.open(WORK/'sample.tar.gz','w:gz') as archive:archive.add(tree,arcname='tree')
        if kind=='compare':(WORK/'copy.txt').write_text('Linux Gym practice\n')
    elif t['group']=='shell':
        result=t['result']; log=WORK/'application.log'; acc=WORK/'access.log'; inv=WORK/'inventory.csv'
        texts={'grep':f'Schrijf alle ERROR-regels uit {log} naar {result}.','grep_ci':f'Schrijf alle regels die "warning" bevatten (hoofdletterongevoelig) uit {log} naar {result}.','sort':f'Sorteer regels van {inv} alfabetisch naar {result}.','unique':f'Tel per IP het aantal regels in {acc}; schrijf "aantal IP" regels naar {result}, oplopend op IP.','count_error':f'Schrijf alleen het aantal ERROR-regels in {log} naar {result}.','head':f'Schrijf de eerste 5 regels uit {acc} naar {result}.','redirect':f'Laat het woord "stdout" precies eenmaal in {result} terechtkomen met outputredirectie.','append':f'Schrijf "eerste" gevolgd door "tweede" op aparte regels naar {result} (gebruik append).','pipeline':f'Schrijf de 3 meest voorkomende IP-adressen uit {acc} naar {result}, alleen IPs, hoogste frequentie eerst.','cut':f'Haal de eerste kolom (namen) uit {inv} naar {result}.'}
        extra={'regex':f'Bewaar uit {log} uitsluitend de regels die beginnen met ERROR of WARNING in {result}.',
               'tail':f'Bewaar de laatste drie regels uit {log} in {result}.',
               'fields':f'Bewaar de functienamen (kolom 2) uit {WORK/"inventory.csv"} in {result}.',
               'sort_numeric':f'Het bestand {WORK/"numbers.txt"} bevat getallen. Sorteer ze numeriek oplopend in {result}.',
               'count_files':f'Hoeveel gewone bestanden liggen direct onder {WORK/"tree"}? Bewaar alleen het aantal in {result}.'}
        desc=texts.get(kind,extra.get(kind))
    elif kind in ('cidr_network','cidr_hosts','same_subnet','cidr_broadcast','cidr_mask','gateway_subnet'):
        result=t['result']
        samples=[('192.168.44.173',26,'192.168.44.182'),('10.19.7.132',27,'10.19.7.193'),('172.16.8.45',23,'172.16.9.200'),('192.168.30.65',28,'192.168.30.79'),('10.10.3.122',25,'10.10.3.251')]
        a,prefix,b=rng.choice(samples)
        net=ipaddress.IPv4Network(f'{a}/{prefix}',strict=False)
        t.update(address=a,prefix=prefix,other=b)
        instructions={
          'cidr_network':f'Een host gebruikt {a}/{prefix}. Wat is het netwerkadres (zonder /prefix)?',
          'cidr_hosts':f'Hoeveel bruikbare hostadressen bevat een klassiek IPv4-subnet /{prefix}?',
          'same_subnet':f'Vallen {a} en {b} binnen hetzelfde /{prefix}-subnet? Antwoord JA of NEE.',
          'cidr_broadcast':f'Wat is het broadcastadres van {a}/{prefix}?',
          'cidr_mask':f'Welk subnetmasker hoort bij /{prefix} (decimale puntnotatie)?',
          'gateway_subnet':f'Een host heeft {a}/{prefix} en gateway {b}. Bevindt de gateway zich in hetzelfde subnet? Antwoord JA of NEE.'}
        desc=instructions[kind]+f' Bewaar uitsluitend het antwoord in {result}.'
    elif kind in ('tls_subject','tls_issuer','tls_expiry','tls_verify'):
        result=t['result']; cert=WORK/'sample-cert.pem'
        t['cert']=str(cert)
        instructions={'tls_subject':f'Bepaal de Common Name (CN) van het certificaat {cert}.',
          'tls_issuer':f'Bepaal de Common Name (CN) van de uitgever van {cert}.',
          'tls_expiry':f'Bepaal de einddatum van {cert} als YYYY-MM-DD.',
          'tls_verify':f'Is {cert} een geldig PEM X.509-certificaat? Antwoord JA of NEE.'}
        desc=instructions[kind]+f' Schrijf alleen het antwoord naar {result}.'
    elif t['group']=='network':
        result=t['result'];url=f'http://127.0.0.1:{port}/health.txt'
        texts={'health_body':f'Sla de responsebody van {url} op in {result}.','http_code':f'Sla uitsluitend de HTTP-statuscode voor {url} op in {result}.','headers':f'Sla de responseheaders van {url} op in {result}.','tcp':f'Controleer met een TCP-test of 127.0.0.1:{port} bereikbaar is. Schrijf OK in {result} als dat lukt.','status':f'Bepaal of {url} een 2xx-status geeft; schrijf OK in {result} als dat zo is.','resolve':f'Zoek het IPv4-adres van localhost op en schrijf 127.0.0.1 naar {result} als dat overeenkomt.','routes':f'Gebruik ip route en schrijf de default gateway van de VM naar {result} (of GEEN als er geen is).','address':f'Gebruik ip en schrijf het huidige IPv4-adres van de interface met de default route naar {result}, zonder prefix.','listen':f'Controleer met ss welke TCP-poort de oefenwebserver gebruikt; schrijf het poortnummer naar {result}.'}
        extra={'http_missing':f'Het pad /does-not-exist bestaat niet op http://127.0.0.1:{port}. Bewaar de HTTP-statuscode in {result}.',
               'fetch_headers':f'Noteer alleen de Content-Type headerwaarde van http://127.0.0.1:{port}/health.txt in {result}.'}
        desc=texts.get(kind,extra.get(kind))
    elif t['group']=='observe':
        result=t['result'];
        texts={'memory':f'Bepaal met free het totale RAM in KiB en schrijf uitsluitend dat getal naar {result}.','cpu':f'Zoek met ps de PID van het proces met het hoogste %CPU-gebruik en schrijf alleen het PID naar {result}.','uptime':f'Bepaal met uptime het aantal seconden uptime (afronding is toegestaan); schrijf getal naar {result}.','processes':f'Zoek de PID van systemd met ps en schrijf alleen dat PID naar {result}.','signal':f'Beëindig het oefenproces waarvan de PID staat in {WORK/"exercise.pid"}; gebruik SIGTERM.','service':f'Bepaal of sshd actief is en schrijf active of inactive naar {result}.','journal':f'Zoek de laatste 5 regels van het systeemjournal en schrijf ze naar {result}.','disk':f'Zoek met df het gebruikspercentage van / en schrijf uitsluitend het getal (zonder %) naar {result}.','mounts':f'Zoek met findmnt welk filesystem op / is gemount; schrijf het SOURCE-veld naar {result}.','block':f'Schrijf met lsblk de naam van de schijf waarop / staat naar {result} (gebruik een leesbare naam uit lsblk).','largest':f'Bepaal hoeveel KiB directory {WORK/"tree"} gebruikt en schrijf alleen het getal naar {result}.'}
        extra={'kernel':f'Leg de draaiende kernelrelease vast in {result}.',
               'whoami':f'Leg je gebruikersnaam vast in {result}.',
               'hostname':f'Leg de ingestelde hostname vast in {result}.',
               'uid':f'Leg je numerieke user-ID vast in {result}.',
               'service_enabled':f'Controleer of sshd automatisch zal starten na reboot. Noteer enabled of disabled in {result}.',
               'root_fs':f'Noteer het type bestandssysteem waarop / is gemount in {result}.'}
        desc=texts.get(kind,extra.get(kind))
        if kind=='signal':
            proc=subprocess.Popen(['sleep','3600'],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            (WORK/'exercise.pid').write_text(str(proc.pid))
    elif kind=='selinux_context':
        # The user performs any privileged configuration; start only prepares an owned path.
        target.mkdir()
        (target/'index.html').write_text('Hello from Linux Gym\n')
        desc=f'Een webapplicatie moet bestanden onder {target} kunnen lezen. De directory en index.html moeten blijvend het SELinux type httpd_sys_content_t krijgen, ook na opnieuw labelen. Wijzig de globale SELinux-modus niet.'
    elif kind=='fstab_tmpfs':
        target.mkdir()
        desc=f'Een tijdelijke werklocatie {target} moet een tmpfs van 16 MiB krijgen die ook in /etc/fstab staat. Mount dit bestandssysteem nu. Laat overige fstab-regels intact; gebruik geen bestaande schijven of partities.'
    elif kind=='firewall_port':
        desc='Sta TCP/18420 permanent toe in de actieve firewalld-zone, zonder bestaande SSH-toegang aan te passen. Herlaad firewalld. Gebruik de VM-snapshot voor volledig herstel.'
    elif kind=='nmcli_profile':
        desc=f'Configureer interface {iface} met NM-profiel gym-lab, adres 192.0.2.50/24, ipv4.method manual, autoconnect yes, zonder gateway of DNS. Activeer het profiel. Doe dit NOOIT op je SSH-interface.'
    t['description']=desc
    t['description']=prompt_for(t)
    return t

def scenario(t, fallback):
    """Present the desired state, not command syntax/implementation."""
    kind=t['kind']; target=t['target']; result=t['result']; v=t.get('variant','A')
    if kind in ('mode','symbolic'):
        mode=int(t['mode'],8); u=(mode>>6)&7; g=(mode>>3)&7; o=mode&7
        def rights(n):
            parts=[]
            if n&4:parts.append('lezen')
            if n&2:parts.append('schrijven')
            if n&1:parts.append('uitvoeren/doorkruisen')
            return ', '.join(parts) if parts else 'geen toegang'
        extra=[]
        if mode&0o2000:extra.append('nieuwe items moeten de directorygroep erven')
        if mode&0o1000:extra.append('gebruikers mogen onderling geen bestanden verwijderen tenzij ze eigenaar zijn (sticky bit)')
        if mode&0o4000:extra.append('zet het setuid-bit')
        if v=='B':
            intro='Een applicatiebeheerder vraagt om de volgende toegangsregels.'
        else:intro='Een gedeelde werkomgeving moet voldoen aan het toegangsbeleid.'
        return (f'{intro}\n   Pad: {target}\n   Eigenaar: {rights(u)}. Groep: {rights(g)}. Overigen: {rights(o)}.'+('\n   Aanvullend: '+', '.join(extra)+'.' if extra else '')+'\n   Herstel de permissies zodat het object hieraan voldoet.')
    if kind=='umask':
        m=int(t['mask'],8); f=0o666&~m; d=0o777&~m
        return f'Nieuwe gegevens mogen niet meer rechten krijgen dan nodig. Maak {t["file"]} met standaardrechten {f:03o} en {t["directory"]} met standaardrechten {d:03o}, zonder naderhand chmod te gebruiken. Gebruik een eigen subshell om je huidige sessie niet te wijzigen.'
    if kind=='unique':return fallback.replace('Tel per IP','Geef per verschillend IP een frequentieoverzicht; tel per IP')
    if kind=='symbolic':return fallback
    if kind=='cpu':return fallback.replace('Zoek met ps','Zoek').replace('met het hoogste %CPU-gebruik','dat momenteel het meeste CPU gebruikt')
    if kind=='memory':return fallback.replace('Bepaal met free','Bepaal')
    if kind=='uptime':return fallback.replace('Bepaal met uptime','Bepaal')
    if kind=='processes':return fallback.replace(' met ps','')
    if kind=='disk':return fallback.replace('Zoek met df','Bepaal')
    if kind=='block':return fallback.replace('Schrijf met lsblk','Noteer').replace('(gebruik een leesbare naam uit lsblk)','')
    if kind=='mounts':return fallback.replace('Zoek met findmnt','Achterhaal')
    if kind=='redirect':return fallback.replace(' met outputredirectie','')
    if kind=='append':return fallback.replace(' (gebruik append)','')
    if kind=='http_code':return fallback.replace('HTTP-statuscode','HTTP-statuscode')
    if kind=='service':return fallback.replace('sshd','de SSH-serverdienst')
    if kind=='firewall_port':return 'De webapplicatie gebruikt TCP-poort 18420. Clients moeten nu én na een herstart van firewalld toestemming hebben om deze poort te benaderen. Laat alle bestaande firewallregels intact.'
    if kind=='firewall_port':return 'Een applicatie op TCP-poort 18420 moet zowel nu als na een firewallherstart bereikbaar mogen zijn via de actieve firewalld-zone. Bestaande regels moeten behouden blijven. Controleer runtime en permanent beleid.'
    if kind=='nmcli_profile':return (f'Op de extra oefeninterface {t["iface"]} moet een verbinding met naam gym-lab worden ingericht. '
      'De server heeft een vast adres 192.0.2.50 met subnetmasker 255.255.255.0 nodig. '
      'De verbinding moet automatisch actief worden bij een nieuwe start. Stel op deze verbinding geen gateway of DNS-server in.')
    return fallback

def start(args):
    if SESSION.exists():raise SystemExit('A session is already active. Run check or reset first.')
    if WORK.exists():raise SystemExit('A workspace already exists. Run reset first; existing files will not be overwritten.')
    if os.geteuid()==0:raise SystemExit('Run Linux Gym as a regular user; use sudo only when completing tasks.')
    if args.interface:
        p=run('nmcli','-g','GENERAL.DEVICE','device','show',args.interface)
        if p.returncode or args.interface=='lo':raise SystemExit('Invalid practice interface or nmcli is unavailable.')
        # Refuse default-route NIC even when system tasks are selected.
        default=run('ip','-4','route','show','default').stdout
        if any(f'dev {args.interface}' in line.split(' metric ')[0] for line in default.splitlines()):raise SystemExit('REFUSED: this interface provides a default route. Use the secondary NIC.')
    if args.system and not args.interface:raise SystemExit('--system requires --interface SECONDARY_NIC to protect SSH access.')
    if args.lab and not args.system:raise SystemExit('--lab requires --system and --interface.')
    if args.lab and not shutil.which('semanage'):raise SystemExit('SELinux lab requires semanage (policycoreutils-python-utils).' )
    if args.system and (not shutil.which('firewall-cmd') or not shutil.which('nmcli')):raise SystemExit('System labs require NetworkManager and firewalld.')
    if shutil.which('python3') is None:raise SystemExit('python3 is missing.')
    backup=snapshot();seed_workspace()
    if any(t['group']=='tls' for t in TASKS):
        cert=WORK/'sample-cert.pem'
        if shutil.which('openssl'):
            cp=run('openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(WORK/'sample-key.pem'),'-out',str(cert),'-subj','/CN=sysadmin-gym.local','-days','365')
            if cp.returncode:raise SystemExit('Could not generate local TLS exercise certificate: '+cp.stderr)
            (WORK/'sample-key.pem').unlink(missing_ok=True)
        else:
            # TLS module is skipped on systems without OpenSSL.
            pass
    port=rand_port()
    server=subprocess.Popen([sys.executable,'-m','http.server',str(port),'--bind','127.0.0.1','--directory',str(WORK/'web')],stdout=(WORK/'http.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
    (WORK/'http.pid').write_text(str(server.pid))
    selected=choose_tasks(args.count,args.system)
    if not shutil.which('openssl'):selected=[t for t in selected if t['group']!='tls']
    if args.system:
        system_tasks=[t for t in TASKS if t['group']=='system']
        selected[-2:]=system_tasks[:2]
        if args.lab:
            selected=selected[:max(0,args.count-4)]+system_tasks
    tasks=[prepare(t,i,port,args.interface) for i,t in enumerate(selected,1)]
    save_json(SESSION,{'tasks':tasks,'backup':str(backup),'started':time.time(),'port':port,'session_id':str(time.time_ns()),'check_number':0})
    print(f'SYSADMIN GYM v4 development — {len(tasks)} tasks | configuration inventory: {backup.name}\n')
    for i,t in enumerate(tasks,1):print(f'{i}. [{t["group"]}] {t["description"]}\n')
    print('Commands: ./gym.sh check | ./gym.sh hint NUMBER | ./gym.sh reset')
    if args.system:print('WARNING: reset does NOT revert system changes. Restore your VM snapshot if needed.')

def expected(t):
    kind=t['kind']; result=Path(t['result']); target=Path(t['target']); src=Path(t.get('source',WORK/'source.txt'))
    def content():return result.read_text().strip()
    def matches(value):return result.exists() and content()==str(value)
    if kind=='practical':
        from .practical import check as check_practical
        return check_practical(t)
    if kind=='config_recovery':
        from .config_recovery import check as check_config
        return check_config(t)
    if kind=='file_audit':
        from .file_audit import check as check_audit
        return check_audit(t)
    if kind in ('mode','symbolic'):return (target.stat().st_mode&0o7777)==int(t['mode'],8)
    if kind=='umask':
        m=int(t['mask'],8); f=Path(t['file']); d=Path(t['directory']);return f.is_file() and d.is_dir() and (f.stat().st_mode&0o777)==(0o666&~m) and (d.stat().st_mode&0o777)==(0o777&~m)
    if kind=='make_dir':return target.is_dir()
    if kind=='remove_file':return not target.exists()
    if kind=='empty_file':return target.is_file() and target.stat().st_size==0
    if kind=='nested_dir':return (target/'a'/'b'/'c').is_dir()
    if kind=='content_search':return result.exists() and set(result.read_text().splitlines())=={str(WORK/'tree'/'report.txt'),str(WORK/'tree'/'report.log')}
    if kind=='copy':return result.is_file() and src.exists() and result.read_bytes()==src.read_bytes()
    if kind=='move':return result.is_file() and not src.exists() and result.read_text()=='Linux Gym practice\n'
    if kind=='hardlink':return result.exists() and result.stat().st_ino==src.stat().st_ino
    if kind=='symlink':return result.is_symlink() and result.resolve()==src.resolve()
    if kind=='find_name':return result.exists() and content().splitlines()==['archive.log','report.log']
    if kind=='find_size':return result.exists() and content().splitlines()==['big.bin']
    if kind=='archive':
        try:
            with tarfile.open(result,'r:gz') as a:return 'tree/report.txt' in a.getnames()
        except (OSError,tarfile.TarError):return False
    if kind=='extract':return (target/'tree'/'report.txt').is_file()
    if kind=='compare':return matches('identical')
    if kind=='count_lines':return matches('10')
    app=(WORK/'application.log').read_text().splitlines(); acc=(WORK/'access.log').read_text().splitlines(); inv=(WORK/'inventory.csv').read_text().splitlines()
    if kind=='regex':return result.exists() and result.read_text().splitlines()==[s for s in app if s.startswith(('ERROR','WARNING'))]
    if kind=='tail':return result.exists() and result.read_text().splitlines()==app[-3:]
    if kind=='fields':return result.exists() and result.read_text().splitlines()==[x.split(':')[1] for x in inv]
    if kind=='sort_numeric':return result.exists() and result.read_text().splitlines()==['3','5','12','20','100']
    if kind=='count_files':return matches(len([x for x in (WORK/'tree').iterdir() if x.is_file()]))
    if kind=='grep':return result.exists() and result.read_text().splitlines()==[s for s in app if 'ERROR' in s]
    if kind=='grep_ci':return result.exists() and result.read_text().splitlines()==[s for s in app if 'warning' in s.lower()]
    if kind=='sort':return result.exists() and result.read_text().splitlines()==sorted(inv)
    if kind in ('unique','pipeline'):
        from collections import Counter
        counts=Counter(s.split()[0] for s in acc)
        wanted=([f'{n} {ip}' for ip,n in sorted(counts.items())] if kind=='unique' else [ip for ip,n in sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:3]])
        return result.exists() and [' '.join(x.split()) for x in result.read_text().splitlines()]==wanted
    if kind=='count_error':return matches('4')
    if kind=='head':return result.exists() and result.read_text().splitlines()==acc[:5]
    if kind=='redirect':return matches('stdout')
    if kind=='append':return result.exists() and result.read_text().splitlines()==['first','second']
    if kind=='cut':return result.exists() and result.read_text().splitlines()==[x.split(':')[0] for x in inv]
    if kind=='http_missing':return matches('404')
    if kind=='fetch_headers':return matches('text/plain')
    if kind=='kernel':return matches(run('uname','-r').stdout.strip())
    if kind=='whoami':return matches(run('id','-un').stdout.strip())
    if kind=='hostname':return matches(run('hostname').stdout.strip())
    if kind=='uid':return matches(os.getuid())
    if kind=='service_enabled':return matches('enabled' if run('systemctl','is-enabled','--quiet','sshd').returncode==0 else 'disabled')
    if kind in ('cidr_network','cidr_hosts','same_subnet','cidr_broadcast','cidr_mask','gateway_subnet'):
        net=ipaddress.IPv4Network(f"{t['address']}/{t['prefix']}",strict=False)
        answers={'cidr_network':str(net.network_address),'cidr_hosts':str(max(0,net.num_addresses-2)),
          'same_subnet':'YES' if ipaddress.IPv4Address(t['other']) in net else 'NO',
          'cidr_broadcast':str(net.broadcast_address),'cidr_mask':str(net.netmask),
          'gateway_subnet':'YES' if ipaddress.IPv4Address(t['other']) in net else 'NO'}
        return result.exists() and content().upper()==answers[kind]
    if kind.startswith('tls_'):
        cert=t['cert']
        p=run('openssl','x509','-in',cert,'-noout','-subject','-issuer','-enddate')
        if p.returncode:return False
        from datetime import datetime, timezone
        output=p.stdout.splitlines()
        if kind=='tls_verify':answer='YES'
        elif kind=='tls_subject':answer='sysadmin-gym.local'
        elif kind=='tls_issuer':answer='sysadmin-gym.local'
        else:
            expiry=next(x.split('=',1)[1] for x in output if x.startswith('notAfter='))
            answer=datetime.strptime(expiry,'%b %d %H:%M:%S %Y %Z').strftime('%Y-%m-%d')
        return matches(answer)
    if kind=='root_fs':return matches(run('findmnt','-n','-o','FSTYPE','/').stdout.strip())
    if kind=='health_body':return matches('linux-gym-ok')
    if kind=='http_code':return matches('200')
    if kind=='headers':return result.exists() and '200 OK' in result.read_text().splitlines()[0]
    if kind in ('tcp','status','resolve'):return matches('OK') if kind!='resolve' else matches('127.0.0.1')
    if kind=='routes':
        routes=run('ip','-4','route','show','default').stdout.split(); gateway=routes[routes.index('via')+1] if 'via' in routes else 'NONE';return matches(gateway)
    if kind=='address':
        route=run('ip','-4','route','show','default').stdout.split(); dev=route[route.index('dev')+1] if 'dev' in route else None
        addresses=run('ip','-4','-o','addr','show','dev',dev).stdout.split() if dev else []
        return bool(addresses) and matches(addresses[addresses.index('inet')+1].split('/')[0])
    if kind=='listen':return matches(t['port'])
    if kind=='signal':
        pid=int((WORK/'exercise.pid').read_text());p=run('ps','-o','stat=','-p',str(pid));return p.returncode!=0 or not p.stdout.strip() or p.stdout.strip().startswith('Z')
    if kind=='memory':return matches(int(run('free','-k').stdout.splitlines()[1].split()[1]))
    if kind=='uptime':
        try:return result.exists() and abs(float(content())-float(Path('/proc/uptime').read_text().split()[0]))<=120
        except ValueError:return False
    if kind=='processes':return matches('1')
    if kind=='service':return matches('active' if run('systemctl','is-active','--quiet','sshd').returncode==0 else 'inactive')
    if kind=='journal':return result.exists() and len(result.read_text().splitlines())>=3
    if kind=='disk':
        df=run('df','-P','/').stdout.splitlines()[-1].split();return matches(df[4].rstrip('%'))
    if kind=='mounts':return matches(run('findmnt','-n','-o','SOURCE','/').stdout.strip())
    if kind=='block':return result.exists() and bool(content()) # machine dependent, observational
    if kind=='largest':
        try:return matches(run('du','-sk',str(WORK/'tree')).stdout.split()[0])
        except (ValueError,IndexError):return False
    if kind=='cpu':
        try:return result.exists() and int(content())>0
        except ValueError:return False
    if kind=='selinux_context':
        if not shutil.which('getenforce') or run('getenforce').stdout.strip()=='Disabled':return False
        label=run('stat','-c','%C',str(target)).stdout.strip()
        file_label=run('stat','-c','%C',str(target/'index.html')).stdout.strip()
        if 'httpd_sys_content_t' not in label or 'httpd_sys_content_t' not in file_label:return False
        if not shutil.which('semanage'):return False
        rules=run('semanage','fcontext','-l').stdout
        return str(target) in rules and 'httpd_sys_content_t' in rules
    if kind=='fstab_tmpfs':
        try:
            lines=[x.split() for x in Path('/etc/fstab').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
            entry=next((x for x in lines if len(x)>=4 and x[1]==str(target) and x[0]=='tmpfs' and x[2]=='tmpfs'),None)
            if not entry:return False
            mounted=run('findmnt','-n','-o','FSTYPE,OPTIONS','--target',str(target)).stdout.strip()
            return mounted.startswith('tmpfs ') and 'size=16m' in ' '.join(entry[3:]).lower()
        except (OSError,IndexError):return False
    if kind=='firewall_port':
        return run('firewall-cmd','--query-port=18420/tcp').returncode==0 and run('firewall-cmd','--permanent','--query-port=18420/tcp').returncode==0
    if kind=='nmcli_profile':
        profile=run('nmcli','-g','ipv4.addresses,ipv4.method,connection.autoconnect,connection.interface-name','connection','show','gym-lab').stdout.splitlines()
        return len(profile)>=4 and profile[0]=='192.0.2.50/24' and profile[1]=='manual' and profile[2]=='yes' and profile[3]==t['iface']
    return False

def check(args):
    session=load_json(SESSION,None)
    if not session:raise SystemExit('No active session.')
    results=[]
    passed=0
    for i,t in enumerate(session['tasks'],1):
        try:ok=expected(t)
        except (OSError,ValueError,IndexError,KeyError,subprocess.TimeoutExpired):ok=False
        print(f'{"PASS" if ok else "FAIL"} {i}. {t["id"]} ({t["kind"]})')
        passed+=ok
        results.append({'id':t['id'],'group':t['group'],'kind':t['kind'],'ok':bool(ok)})
    session['check_number']=session.get('check_number',0)+1
    session['last_results']=results
    save_json(SESSION,session)
    record(ROOT,{'event':'check','session':session['session_id'],'check_number':session['check_number'],
                 'results':results,'score':passed,'total':len(results)})
    print(f'Score: {passed}/{len(results)}. Check saved to history immediately.')

def hint(args):
    session=load_json(SESSION,None)
    if not session:raise SystemExit('No active session.')
    if not (1<=args.number<=len(session['tasks'])):raise SystemExit('Invalid task number.')
    print(f'HINT {args.number}: {hint_for(session["tasks"][args.number-1])}')

def reset(args):
    session=load_json(SESSION,None)
    if session and any(t['group']=='system' for t in session['tasks']):
        raise SystemExit('System labs make persistent changes. Restore the VM snapshot in virt-manager on the HOST; reset will not undo this lab.')
    if session:
        pid_file=WORK/'http.pid'
        if pid_file.exists():
            try:
                pid=int(pid_file.read_text())
                proc=run('ps','-o','args=','-p',str(pid)).stdout
                if 'http.server' in proc and str(WORK/'web') in proc:os.kill(pid,15)
            except (ValueError,ProcessLookupError):pass
        pid_file=WORK/'exercise.pid'
        if pid_file.exists():
            try:
                pid=int(pid_file.read_text());cmd=run('ps','-o','args=','-p',str(pid)).stdout.strip()
                if cmd=='sleep 3600':os.kill(pid,15)
            except (ValueError,ProcessLookupError):pass
        SESSION.unlink(missing_ok=True)
    if session:
        final=session.get('last_results')
        if final is None:
            final=[{'id':t['id'],'group':t['group'],'kind':t['kind'],'ok':None} for t in session['tasks']]
        record(ROOT,{'event':'reset','session':session['session_id'],'checks':session.get('check_number',0),
                     'results':final})
    (ROOT/'last_check.json').unlink(missing_ok=True)
    if WORK.exists():shutil.rmtree(WORK)
    print('Workspace cleared. Configuration inventories and progress are preserved.')
    print('NOTE: network, firewall, and system changes are NOT reverted automatically. Restore your VM snapshot if necessary.')

def main():
    p=argparse.ArgumentParser(description='Sysadmin Gym — modular RHCSA practice')
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('start');s.add_argument('--count',type=int,default=None);s.add_argument('--lab',action='store_true',help='Include SELinux context and tmpfs/fstab tasks (VM snapshot required)');s.add_argument('--system',action='store_true',help='Include nmcli and firewall tasks; secondary NIC only');s.add_argument('--interface',help='Name of secondary virtual NIC')
    sub.add_parser('check');u=sub.add_parser('install');u.add_argument('archive');rb=sub.add_parser('rollback');rb.add_argument('module');h=sub.add_parser('hint');h.add_argument('number',type=int);sub.add_parser('reset');sub.add_parser('stats');sub.add_parser('list')
    a=p.parse_args()
    if a.command=='start':
        if a.count is None:a.count=config(ROOT)['tasks_per_round']
        if not 5<=a.count<=20:p.error('count must be between 5 and 20')
        start(a)
    elif a.command=='install':
        from .updates import install
        try:install(a.archive)
        except (ValueError,OSError,KeyError,tarfile.TarError) as e:raise SystemExit(str(e))
    elif a.command=='rollback':
        from .updates import rollback
        try:rollback(a.module)
        except (ValueError,OSError,KeyError) as e:raise SystemExit(str(e))
    elif a.command=='check':check(a)
    elif a.command=='hint':hint(a)
    elif a.command=='reset':reset(a)
    elif a.command=='stats':
        summary(ROOT)
    elif a.command=='list':
        from collections import Counter
        print('Task catalog:',len(TASKS),'templates',dict(Counter(t['group'] for t in TASKS)))
if __name__=='__main__':main()
