"""Trace desktop UI — entirely local and deliberately dependency-light."""
import collections
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import psutil
from .collector import metric_snapshot, top_processes, active_connections, format_size
from .recording import Recorder

BG = '#101a20'
PANEL = '#18262d'
FG = '#e4eded'
MUTED = '#8ca4a9'
ACCENT = '#9ccabf'
WARN = '#e5ae85'


class TraceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Trace  |  System Diagnostics')
        self.geometry('1120x750')
        self.minsize(820, 570)
        self.configure(bg=BG)
        self.recorder = Recorder()
        self.previous_disk = None
        self.previous_net = None
        self.last_tick = time.monotonic()
        self.history = {key: collections.deque(maxlen=80) for key in ('cpu_percent', 'memory_percent', 'network_recv_bytes_sec', 'network_sent_bytes_sec')}
        self.last_process_refresh = 0
        self.last_connection_refresh = 0
        self.sort_mode = tk.StringVar(value='memory')
        self.status = tk.StringVar(value='Ready  ·  Local-only monitoring')
        self.metric_labels = {}
        self._build()
        psutil.cpu_percent(interval=None)
        self.after(500, self._tick)

    def _build(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', background=PANEL, foreground=MUTED, padding=(20, 12), font=('Segoe UI', 10))
        style.map('TNotebook.Tab', background=[('selected', '#294047')], foreground=[('selected', FG)])
        style.configure('Treeview', background=PANEL, fieldbackground=PANEL, foreground=FG, borderwidth=0, rowheight=27, font=('Consolas', 10))
        style.configure('Treeview.Heading', background='#254048', foreground=FG, font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', '#32615e')])
        heading = tk.Frame(self, bg=BG, padx=26, pady=18)
        heading.pack(fill='x')
        tk.Label(heading, text='TRACE', fg=FG, bg=BG, font=('Segoe UI', 26, 'bold')).pack(side='left')
        tk.Label(heading, text='  /  SYSTEM DIAGNOSTICS', fg=ACCENT, bg=BG, font=('Consolas', 11)).pack(side='left', pady=12)
        tk.Button(heading, text='EXPORT SESSION', command=self._export, bg='#294b4a', fg=FG, relief='flat', padx=16, pady=10).pack(side='right', padx=4)
        self.record_button = tk.Button(heading, text='START RECORDING', command=self._toggle_record, bg='#294b4a', fg=FG, relief='flat', padx=16, pady=10)
        self.record_button.pack(side='right', padx=4)

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill='both', expand=True, padx=22, pady=(0, 12))
        self.overview = tk.Frame(self.tabs, bg=BG)
        self.process_tab = tk.Frame(self.tabs, bg=BG)
        self.connections_tab = tk.Frame(self.tabs, bg=BG)
        self.tabs.add(self.overview, text='OVERVIEW')
        self.tabs.add(self.process_tab, text='PROCESSES')
        self.tabs.add(self.connections_tab, text='CONNECTIONS')
        self._overview()
        self._processes()
        self._connections()
        tk.Label(self, textvariable=self.status, anchor='w', bg=BG, fg=MUTED, font=('Consolas', 9), padx=27, pady=9).pack(fill='x')

    def _overview(self):
        top = tk.Frame(self.overview, bg=BG)
        top.pack(fill='x', pady=(18, 15))
        for key, name in [('cpu', 'CPU LOAD'), ('memory', 'MEMORY'), ('net', 'NETWORK IN'), ('disk', 'DISK READ')]:
            panel = tk.Frame(top, bg=PANEL, padx=16, pady=14)
            panel.pack(side='left', fill='both', expand=True, padx=5)
            tk.Label(panel, text=name, bg=PANEL, fg=MUTED, font=('Consolas', 9)).pack(anchor='w')
            label = tk.Label(panel, text='—', bg=PANEL, fg=FG, font=('Segoe UI', 22, 'bold'))
            label.pack(anchor='w', pady=(7, 0))
            self.metric_labels[key] = label
        chart_panel = tk.Frame(self.overview, bg=PANEL, padx=16, pady=16)
        chart_panel.pack(fill='both', expand=True, padx=5, pady=5)
        tk.Label(chart_panel, text='LIVE TELEMETRY   /   CPU + MEMORY', bg=PANEL, fg=ACCENT, font=('Consolas', 10)).pack(anchor='w', pady=(0, 12))
        self.graph = tk.Canvas(chart_panel, bg=PANEL, highlightthickness=0)
        self.graph.pack(fill='both', expand=True)
        self.graph.bind('<Configure>', lambda _e: self._draw_graph())
        tk.Label(self.overview, text='CPU  ━━━  MINT     MEMORY  ━━━  AMBER     ·     1 SECOND SAMPLING', bg=BG, fg=MUTED, font=('Consolas', 9), pady=15).pack(anchor='w', padx=7)

    def _processes(self):
        toolbar = tk.Frame(self.process_tab, bg=BG, pady=15)
        toolbar.pack(fill='x')
        tk.Label(toolbar, text='TOP PROCESSES  ·  READ-ONLY', bg=BG, fg=MUTED, font=('Consolas', 10)).pack(side='left')
        for name, value in [('SORT MEMORY', 'memory'), ('SORT CPU', 'cpu')]:
            tk.Radiobutton(toolbar, text=name, value=value, variable=self.sort_mode, command=self._refresh_processes, bg=BG, fg=ACCENT, selectcolor=PANEL, activebackground=BG, activeforeground=FG).pack(side='right', padx=7)
        self.process_table = self._table(self.process_tab, [('pid', 85), ('name', 370), ('cpu %', 120), ('RAM', 140), ('status', 145)])

    def _connections(self):
        toolbar = tk.Frame(self.connections_tab, bg=BG, pady=15)
        toolbar.pack(fill='x')
        tk.Label(toolbar, text='ACTIVE SOCKETS  ·  SOME MAY REQUIRE ADMIN ACCESS', bg=BG, fg=MUTED, font=('Consolas', 10)).pack(side='left')
        tk.Button(toolbar, text='REFRESH', command=self._refresh_connections, bg='#294b4a', fg=FG, relief='flat', padx=15).pack(side='right')
        self.connections_table = self._table(self.connections_tab, [('protocol', 82), ('pid', 85), ('local endpoint', 275), ('remote endpoint', 275), ('state', 140)])

    def _table(self, parent, columns):
        wrapper = tk.Frame(parent, bg=PANEL)
        wrapper.pack(fill='both', expand=True)
        keys = [name for name, _ in columns]
        tree = ttk.Treeview(wrapper, columns=keys, show='headings')
        for name, width in columns:
            tree.heading(name, text=name.upper())
            tree.column(name, width=width, minwidth=60, stretch=True)
        scroll = ttk.Scrollbar(wrapper, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
        return tree

    def _draw_graph(self):
        canvas = self.graph
        canvas.delete('all')
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 50 or height < 50:
            return
        pad = 14
        for percent in (0, 25, 50, 75, 100):
            y = pad + (height - 2 * pad) * (1 - percent / 100)
            canvas.create_line(0, y, width, y, fill='#2b3d44')
            canvas.create_text(7, y - 8, text=str(percent), fill=MUTED, anchor='w', font=('Consolas', 8))
        for key, color in [('cpu_percent', ACCENT), ('memory_percent', WARN)]:
            values = list(self.history[key])
            if len(values) < 2:
                continue
            points = []
            for idx, value in enumerate(values):
                x = pad + idx * (width - 2 * pad) / (self.history[key].maxlen - 1)
                y = pad + (height - 2 * pad) * (1 - max(0, min(100, value)) / 100)
                points.extend((x, y))
            canvas.create_line(*points, fill=color, width=2, smooth=False)

    def _refresh_processes(self):
        table = self.process_table
        rows = top_processes(sort=self.sort_mode.get())
        table.delete(*table.get_children())
        for row in rows:
            table.insert('', 'end', values=(row['pid'], row['name'], f"{row['cpu_percent']:.1f}", format_size(row['memory_bytes']), row['status']))

    def _refresh_connections(self):
        rows, error = active_connections()
        table = self.connections_table
        table.delete(*table.get_children())
        for row in rows:
            table.insert('', 'end', values=(row['type'], row['pid'] or '—', row['local'], row['remote'], row['status']))
        if error:
            self.status.set(error)

    def _toggle_record(self):
        self.recorder.enabled = not self.recorder.enabled
        self.record_button.configure(text='STOP RECORDING' if self.recorder.enabled else 'START RECORDING', bg='#724b42' if self.recorder.enabled else '#294b4a')
        self.status.set('Recording locally (max 3,600 samples)' if self.recorder.enabled else f'Recording stopped  ·  {len(self.recorder.samples)} samples')

    def _export(self):
        if not self.recorder.samples:
            messagebox.showinfo('No recordings', 'Start recording to collect data before exporting.')
            return
        dest = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv'), ('JSON', '*.json')], title='Export session')
        if dest:
            try:
                count = self.recorder.save(dest)
                self.status.set(f'Exported {count} samples to {dest}')
            except (OSError, ValueError) as error:
                messagebox.showerror('Export error', str(error))

    def _tick(self):
        now = time.monotonic()
        elapsed = now - self.last_tick
        self.last_tick = now
        try:
            sample, self.previous_disk, self.previous_net = metric_snapshot(self.previous_disk, self.previous_net, elapsed)
            self.recorder.add(sample)
            for key, values in self.history.items():
                values.append(sample[key])
            self.metric_labels['cpu'].configure(text=f"{sample['cpu_percent']:.1f}%")
            self.metric_labels['memory'].configure(text=f"{sample['memory_percent']:.1f}%")
            self.metric_labels['net'].configure(text=f"{format_size(sample['network_recv_bytes_sec'])}/s")
            self.metric_labels['disk'].configure(text=f"{format_size(sample['disk_read_bytes_sec'])}/s")
            self._draw_graph()
            if now - self.last_process_refresh > 3:
                self._refresh_processes()
                self.last_process_refresh = now
            if now - self.last_connection_refresh > 12 and self.tabs.index('current') == 2:
                self._refresh_connections()
                self.last_connection_refresh = now
        except (psutil.Error, OSError) as error:
            self.status.set(f'Metric unavailable: {error}')
        finally:
            self.after(1000, self._tick)
