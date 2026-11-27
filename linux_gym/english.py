"""Original English, outcome-based task descriptions and tiered hints."""
from pathlib import Path

def prompt_for(t):
    k=t['kind']; w=Path(t['target']).parent; target=t['target']; result=t['result']; v=t.get('variant','A')
    src=w/'source.txt'; tree=w/'tree'; log=w/'application.log'; access=w/'access.log'; inv=w/'inventory.csv'
    lead='You are preparing a development environment. ' if v=='A' else 'During a routine maintenance window, '
    if k in ('mode','symbolic'):
        mode=int(t['mode'],8)
        def phrase(n):
            return ', '.join([name for bit,name in ((4,'read'),(2,'write'),(1,'execute/traverse')) if n&bit]) or 'no access'
        u,g,o=((mode>>i)&7 for i in (6,3,0))
        special=[]
        if mode&0o2000:special.append('new entries must inherit the directory group')
        if mode&0o1000:special.append('users must not delete entries belonging to other users')
        if mode&0o4000:special.append('the set-user-ID behavior is required')
        extra=(' Additional requirement: '+ '; '.join(special)+'.') if special else ''
        return f'{lead}Apply the following access policy to {target}: owner: {phrase(u)}; group: {phrase(g)}; everyone else: {phrase(o)}.{extra} Preserve its contents.'
    if k=='umask':
        m=int(t['mask'],8); f=0o666&~m; d=0o777&~m
        def permissions(x):return f'owner {"read/write" if x&0o600==0o600 else "read" if x&0o400 else "none"}; group {"read/write" if x&0o060==0o060 else "read" if x&0o040 else "none"}; others {"read/write" if x&0o006==0o006 else "read" if x&0o004 else "none"}'
        return f'Create a regular file at {t["file"]} and a directory at {t["directory"]}. Apply a process creation policy so the file has {f:03o} and the directory has {d:03o} at creation. Do not change permissions afterwards or modify your parent shell.'
    descriptions={
      'make_dir':f'A new application component needs a directory at {target}. Create it.',
      'remove_file':f'The obsolete artifact at {target} must no longer exist. Remove it without affecting other files.',
      'empty_file':f'An application must retain its log file {target}, but its contents must be cleared.',
      'nested_dir':f'Prepare a directory hierarchy rooted at {target} with child path a/b/c.',
      'content_search':f'Audit the directory {tree}. Record the complete paths of files containing the string report, one path per line, in {result}.',
      'copy':f'A service needs another copy of {src} at {result}; the original must remain unchanged.',
      'move':f'The artifact at {src} has been relocated to {result}. Only its new location should remain.',
      'hardlink':f'Two pathnames must refer to the same inode: retain {src} and create {result} as the second pathname.',
      'symlink':f'Applications must reach {src} through a symbolic reference at {result}.',
      'find_name':f'Audit {tree} for filenames ending in .log. Put just the basenames, alphabetically sorted and one per line, in {result}.',
      'find_size':f'Identify regular files larger than 1 MiB beneath {tree}. Record just the basenames, one per line, in {result}.',
      'archive':f'Create a gzip-compressed tar archive at {result} containing the tree directory with its relative paths.',
      'extract':f'Restore the supplied archive {w/"sample.tar.gz"} into {target}; the restored tree must contain report.txt.',
      'compare':f'Compare {src} and {w/"copy.txt"}. Write exactly identical or different to {result}, according to the contents.',
      'count_lines':f'Auditors need the number of lines in {log}. Put only the decimal count in {result}.',
      'grep':f'Extract every ERROR entry from {log} into {result}, preserving their order.',
      'grep_ci':f'Extract all entries containing warning (regardless of case) from {log} into {result}.',
      'sort':f'The records in {inv} need to be stored alphabetically, one original record per line, in {result}.',
      'unique':f'Prepare an access summary from {access}: each line in {result} must contain a request count followed by its IPv4 address; sort by IPv4 address.',
      'count_error':f'Record only the number of ERROR entries in {log} in {result}.',
      'head':f'A colleague needs the earliest five entries in {access}, in their original order, copied to {result}.',
      'redirect':f'Create {result} containing only the word stdout, followed by a newline.',
      'append':f'The record {result} must contain two lines, first and second, in that order, without a third line.',
      'pipeline':f'From {access}, identify the three IPv4 addresses with the most requests. Store only the addresses in {result}, most frequent first; break ties by ascending textual IP address.',
      'cut':f'Export only the employee names (first field) from {inv} into {result}, maintaining row order.',
      'regex':f'Only log entries starting with ERROR or WARNING from {log} may appear in {result}, in source order.',
      'tail':f'Retain the most recent three log entries from {log} in {result}, preserving order.',
      'fields':f'A downstream service needs the second colon-delimited field from every row in {inv}. Write these fields to {result}.',
      'sort_numeric':f'The values in {w/"numbers.txt"} must be stored in increasing numerical order in {result}.',
      'count_files':f'Count regular files immediately inside {tree} (not subdirectories). Write the single number to {result}.',
      'health_body':f'The application health response from http://127.0.0.1:{t["port"]}/health.txt must be archived verbatim in {result}.',
      'http_code':f'Record only the HTTP status code returned by http://127.0.0.1:{t["port"]}/health.txt in {result}.',
      'headers':f'Record the response headers from http://127.0.0.1:{t["port"]}/health.txt in {result}, including the HTTP status line.',
      'tcp':f'An application is expected to listen on 127.0.0.1:{t["port"]}. If a TCP connection succeeds, put OK in {result}.',
      'status':f'Confirm whether http://127.0.0.1:{t["port"]}/health.txt returns a successful 2xx response. Put OK in {result} if it does.',
      'resolve':f'Check the IPv4 resolution of localhost. If it resolves to 127.0.0.1, record that exact address in {result}.',
      'routes':f'Record the VM’s default IPv4 gateway in {result}; use NONE if none exists.',
      'address':f'Find the interface used by the default IPv4 route. Record its current IPv4 address without the prefix in {result}.',
      'listen':f'Determine the TCP port used by the temporary Linux Gym web server listening on loopback. Store only its port number in {result}.',
      'http_missing':f'A client requests http://127.0.0.1:{t["port"]}/does-not-exist. Record the returned HTTP status code in {result}.',
      'fetch_headers':f'Record only the Content-Type response header value for http://127.0.0.1:{t["port"]}/health.txt in {result}.',
      'memory':f'Capacity planning requires the total physical memory reported by the OS, in KiB. Record the decimal number in {result}.',
      'cpu':f'Identify the PID of the process currently consuming the highest percentage of CPU. Put only the PID in {result}.',
      'uptime':f'Operations needs the system uptime in seconds (within two minutes of the current value). Store the number in {result}.',
      'processes':f'Identify the PID of the system manager (systemd) and write just its PID in {result}.',
      'signal':f'Stop the temporary exercise process whose PID is listed in {w/"exercise.pid"}. Request graceful termination rather than a forced kill.',
      'service':f'Determine whether the SSH server service is currently running. Store active or inactive in {result}.',
      'journal':f'Capture at least three recent journal entries into {result} for a support ticket.',
      'disk':f'Operations needs the current percentage of space used by the root filesystem. Record only the whole number, without the percent sign, in {result}.',
      'mounts':f'Identify the filesystem source mounted as /. Record that source exactly in {result}.',
      'block':f'Identify the block device backing the root filesystem and record a device name in {result}.',
      'largest':f'Estimate the disk usage of {tree} in KiB. Record a positive whole number in {result}.',
      'kernel':f'Record the running kernel release in {result}.',
      'whoami':f'Write the name of the effective current user to {result}.',
      'hostname':f'Record this VM’s current hostname in {result}.',
      'uid':f'Record your numeric user ID in {result}.',
      'service_enabled':f'Determine whether the SSH server is configured to start at boot. Put enabled or disabled in {result}.',
      'root_fs':f'Identify the filesystem type mounted at /. Write its type to {result}.',
      'firewall_port':'An application listens on TCP port 18420. Clients must be allowed to connect now and after a firewalld reload. Preserve existing firewall rules and SSH access.',
      'nmcli_profile':f'The secondary practice interface {t["iface"]} requires a connection named gym-lab with static IPv4 address 192.0.2.50 and subnet mask 255.255.255.0. Activate it and ensure it reconnects after reboot. Do not configure a gateway or DNS server on that connection.',
      'selinux_context':f'A web application serves files in {target}. Both the directory and its index.html must permanently carry the SELinux type httpd_sys_content_t, including after relabeling. Do not alter the global SELinux mode.',
      'fstab_tmpfs':f'The application needs a 16 MiB memory-backed filesystem mounted at {target}, active now and defined for subsequent boots. Preserve all existing fstab entries; do not modify physical disks.',
    }
    if k.startswith(('cidr_','same_subnet','gateway_subnet','tls_')):
        a=t.get('address'); p=t.get('prefix'); b=t.get('other')
        prompts={
            'cidr_network':f'Find the network address of {a}/{p}, without the prefix.',
            'cidr_hosts':f'How many usable host addresses are in a conventional IPv4 /{p} subnet?',
            'same_subnet':f'Are {a} and {b} in the same /{p} subnet? Answer YES or NO.',
            'cidr_broadcast':f'Find the broadcast address of {a}/{p}.',
            'cidr_mask':f'Find the dotted-decimal subnet mask for /{p}.',
            'gateway_subnet':f'Can host {a}/{p} reach gateway {b} on its local subnet? Answer YES or NO.',
            'tls_subject':'Find the certificate subject common name.',
            'tls_issuer':'Find the certificate issuer common name.',
            'tls_expiry':'Find the certificate expiration date in YYYY-MM-DD format.',
            'tls_verify':'Is the supplied certificate a valid PEM X.509 certificate? Answer YES or NO.',
        }
        source=f' Certificate: {t["cert"]}.' if k.startswith('tls_') else ''
        return prompts[k]+source+f' Record only the answer in {result}.'
    if k not in descriptions:raise ValueError(f'Unknown task: {k}')
    return descriptions[k]

HINTS={
 'mode':'Review file access rights and special directory bits; compare the current rights with the required policy.',
 'symbolic':'Read the symbolic permissions section of chmod(1).',
 'umask':'Default file creation rights and directory creation rights differ; investigate umask.',
 'nmcli_profile':'Inspect nmcli connection show and the NetworkManager profile properties.',
 'firewall_port':'Review firewalld runtime versus permanent configuration, and how to apply changes.',
 'selinux_context':'Review getenforce, ls -Z, semanage fcontext, and restorecon.',
 'fstab_tmpfs':'Review fstab(5), mount, and findmnt; keep a copy of fstab first.',
}
def hint_for(t):
    k=t['kind']
    if k.startswith(('cidr_','same_subnet','gateway_subnet')):return 'Identify the network and host bits using the prefix length.'
    if k.startswith('tls_'):return 'Review the openssl x509 manual.'
    if k=='file_audit':return t['hint']
    if k in HINTS:return HINTS[k]
    group=t['group']
    return {'files':'Investigate file and directory operations in the coreutils and find manuals.', 'shell':'Review shell redirection, text filters, and pipelines.', 'network':'Inspect the ip, ss, getent, or curl command documentation.', 'observe':'Review systemctl, journalctl, ps, procfs, and filesystem reporting commands.'}.get(group,'Consult the appropriate Linux manual page.')
