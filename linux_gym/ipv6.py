"""IPv6 address literacy exercises with representation-aware grading."""
import ipaddress
from pathlib import Path
import subprocess

def prepare(task, rng):
    kind=task['kind'][5:]
    address=ipaddress.IPv6Address(f'2001:db8:{rng.randrange(1,65536):x}:{rng.randrange(0,65536):x}::{rng.randrange(1,256):x}')
    result=task['result']
    if kind=='expand':
        question=f'Expand {address.compressed} into eight groups of four hexadecimal digits.'
        answer=address.exploded
    elif kind=='compress':
        question=f'Write {address.exploded} in canonical compressed IPv6 notation.'
        answer=address.compressed
    elif kind=='type':
        value,label=rng.choice([('::1','loopback'),('fe80::12','link-local'),('fd12:3456::1','unique-local'),('ff02::1','multicast'),('2606:4700::1111','global-unicast')])
        question=f'Classify {value} as one of: loopback, link-local, unique-local, multicast, global-unicast.'
        answer=label
    elif kind in ('prefix64','prefix_other'):
        prefix=64 if kind=='prefix64' else rng.choice([48,56])
        question=f'Find the network prefix of {address}/{prefix}, including the prefix length.'
        answer=str(ipaddress.IPv6Network((address,prefix),strict=False))
    elif kind=='same':
        prefix=rng.choice([48,64,64])
        other=ipaddress.IPv6Address(int(address)^ (1 << rng.choice([8,24,64,80,96])))
        question=f'Are {address} and {other} in the same /{prefix} subnet? Answer YES or NO.'
        answer='YES' if other in ipaddress.IPv6Network((address,prefix),strict=False) else 'NO'
    elif kind=='reachability':
        question='Check whether the local IPv6 loopback address ::1 responds to an ICMPv6 echo request. Answer YES or NO.'
        answer=None
    else:
        raise ValueError(f'Unknown IPv6 exercise: {kind}')
    task['answer']=answer
    task['description']=f'{question} Record only the answer in {result}.'
    return task

def check(task):
    path=Path(task['result'])
    if not path.is_file():
        return False
    actual=path.read_text().strip().lower()
    kind=task['kind'][5:]
    answer=task['answer']
    if kind=='reachability':
        answer='yes' if subprocess.run(['ping','-6','-c','1','-W','2','::1'],capture_output=True,timeout=5).returncode==0 else 'no'
    if kind in ('prefix64','prefix_other'):
        try:
            return '/' in actual and ipaddress.IPv6Network(actual,strict=True)==ipaddress.IPv6Network(answer)
        except ValueError:
            return False
    return actual==answer.lower()
