"""Read-only system metrics; no privileged operations or outbound network calls."""
from __future__ import annotations

import datetime as dt
import psutil


def metric_snapshot(previous_disk=None, previous_net=None, elapsed=1.0):
    """Gather metrics and bounded rate calculations; return serializable snapshot."""
    cpu = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    disk = psutil.disk_io_counters()
    net = psutil.net_io_counters()
    elapsed = max(elapsed, 0.001)

    def speed(current, previous, field):
        if current is None or previous is None:
            return 0.0
        return max(0, getattr(current, field) - getattr(previous, field)) / elapsed

    data = {
        'timestamp': dt.datetime.now(dt.timezone.utc).isoformat(),
        'cpu_percent': cpu,
        'memory_percent': memory.percent,
        'memory_used': memory.used,
        'memory_total': memory.total,
        'disk_read_bytes_sec': speed(disk, previous_disk, 'read_bytes'),
        'disk_write_bytes_sec': speed(disk, previous_disk, 'write_bytes'),
        'network_sent_bytes_sec': speed(net, previous_net, 'bytes_sent'),
        'network_recv_bytes_sec': speed(net, previous_net, 'bytes_recv'),
    }
    return data, disk, net


def top_processes(limit=75, sort='memory'):
    rows = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent', 'status']):
        try:
            p = proc.info
            rows.append({
                'pid': p['pid'], 'name': p['name'] or '<unnamed>',
                'memory_bytes': p['memory_info'].rss if p['memory_info'] else 0,
                'cpu_percent': p['cpu_percent'] or 0,
                'status': p['status'] or 'unknown',
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    key = 'cpu_percent' if sort == 'cpu' else 'memory_bytes'
    return sorted(rows, key=lambda r: r[key], reverse=True)[:limit]


def active_connections(limit=150):
    """Read-only connection listing; some process IDs need administrator permissions."""
    try:
        connections = psutil.net_connections(kind='inet')
    except (psutil.AccessDenied, PermissionError, OSError):
        return [], 'Some connections require Administrator permissions.'
    results = []
    for c in connections:
        local = f'{c.laddr.ip}:{c.laddr.port}' if c.laddr else '—'
        remote = f'{c.raddr.ip}:{c.raddr.port}' if c.raddr else '—'
        results.append({'pid': c.pid, 'local': local, 'remote': remote,
                        'status': c.status, 'type': 'TCP' if c.type == 1 else 'UDP'})
    return results[:limit], None


def format_size(value):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(value) < 1024 or unit == 'TB':
            return f'{value:.1f} {unit}'
        value /= 1024
