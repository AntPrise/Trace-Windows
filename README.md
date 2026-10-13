# Trace

A privacy-first Windows diagnostic monitor, built with Python, `psutil`, and Tkinter. The interface is deliberately restrained: live telemetry, readable process tables, connection information, and explicit local data export.

## Features

- CPU and RAM live percentage charts with 1-second samples
- Disk read throughput and received network bandwidth
- Sortable-by-mode process inventory with CPU and resident memory information
- Local TCP/UDP connection listing with PID and endpoints (permissions may restrict results)
- Session recording (up to 3,600 samples) and JSON/CSV export
- No accounts, telemetry uploads, network requests, injected hooks, privileged execution, or process modification

## Getting started (Windows 10 / 11)

Install Python 3.10+ with the Windows Python launcher (`py`). Double-click **`launch.bat`**. The first run creates a virtual environment and installs `psutil`. Later launches reuse it.

Alternatively:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
$env:PYTHONPATH = 'src'
.venv\Scripts\python -m trace_monitor
```

## Tests

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python -m unittest discover -s tests -v
```

## Repository

- `src/trace_monitor/collector.py` — OS metric access and process/socket listings
- `src/trace_monitor/ui.py` — desktop interface and live graphs
- `src/trace_monitor/recording.py` — bounded session capture and export
- `tests/` — regression tests for export and metrics

## Known limitations

- Currently distributed as **Python source**, not a signed Windows EXE.
- Designed for Windows. UI and unit tests can run on other platforms, but Windows is the target.
- Windows administrator permissions may be required to see some process/socket information; the app doesn't elevate itself.
- CPU measurements from `psutil.process_iter` can be near zero on initial sampling; values normalize over subsequent refreshes.
- Disk/network throughput reflects system-wide counters, not per-application bandwidth. No latency or packet-loss probing yet.
- Changes in process state may prevent collecting a row; such rows are skipped.

## Safety

This application is strictly read-only. It never transmits collected data. Exports are user-initiated and may contain process names, endpoint addresses, and other sensitive details; review before sharing.

## License

MIT. See [LICENSE](LICENSE).
