# Nestor CLI — User Guide

Nestor is an intelligent Linux storage workload advisor. It watches live block-device
I/O via eBPF, classifies the current workload pattern (e.g. random read, sequential
write, mixed), and recommends or applies the best I/O scheduler for that pattern.

---

## 1. Installation

From the project root (`~/nestor`), with your virtual environment active:

```bash
./venv/bin/pip install -e .
```

This registers a `nestor` console script inside `venv/bin/`, pointing back at your
source tree (editable install — code changes take effect without reinstalling).

If `venv/bin` is on your `PATH`, or you've run `source venv/bin/activate`, you can
call it directly as `nestor`. Otherwise, use the full path: `./venv/bin/nestor`.

All commands require root, since they read kernel telemetry (eBPF) and — for `apply`
— write to `/sys/block/<device>/queue/scheduler`. `require_root()` checks this at the
start of every command and will refuse to run otherwise:

```
Error: Nestor requires root privileges.
Run using:
    sudo nestor ...
```

### `sudo` and `PATH` — a one-time gotcha

`sudo` uses its own secure `PATH` (e.g. `/usr/sbin:/usr/bin:/sbin:/bin`), not your
shell's — so even though plain `nestor` works fine after the install above, running
`sudo nestor ...` will fail with `sudo: nestor: command not found`, since `sudo`
never looks inside `venv/bin`.

Fix it once with a symlink into a directory that's already on root's secure path:

```bash
sudo ln -s "$(pwd)/venv/bin/nestor" /usr/local/bin/nestor
```

(Run this from `~/nestor` so `$(pwd)` resolves to the right venv path.)

After that, plain `sudo nestor ...` works everywhere, with no path juggling:

```bash
sudo nestor c nvme0n1 -d 10
```

If you'd rather not symlink, the alternative is calling the full path every time:

```bash
sudo ./venv/bin/nestor c nvme0n1 -d 10
```

---

## 2. Quick Reference

| Command      | Aliases     | What it does                                             | Mutates system? |
|--------------|-------------|-----------------------------------------------------------|-----------------|
| `classify`   | `c`         | Detect the current workload pattern                        | No |
| `recommend`  | `rec`, `r`  | Detect workload + suggest schedulers                       | No |
| `apply`      | `a`         | Detect workload + apply the top recommended scheduler      | **Yes** |
| `monitor`    | `mon`, `m`  | Continuously classify workload until stopped               | No |
| `benchmark`  | `bench`, `b`| Run the fio-driven benchmark suite to generate labeled training data | No (writes to `/tmp/nestor/`) |

Every command also accepts:

```bash
nestor --version    # print the installed Nestor version
nestor --help        # top-level help / list of commands
nestor <command> --help   # help for a specific command
```

---

## 3. Commands in Detail

### `classify` (alias: `c`)

Collects a window of live telemetry from a device and reports the predicted
workload class, confidence, and the full probability breakdown across all classes.

```bash
sudo nestor classify nvme0n1
sudo nestor c nvme0n1 -d 10
```

**Arguments:**
- `device` (positional, optional) — block device to sample, e.g. `nvme0n1`.
  Defaults to `config.DEFAULT_DEVICE` if omitted.
- `--duration` / `-d` — collection window in seconds. Defaults to
  `config.DEFAULT_COLLECTION_TIME`.

---

### `recommend` (aliases: `rec`, `r`)

Same telemetry + classification as `classify`, then feeds the result into the
scheduler advisor and prints a ranked list of recommended I/O schedulers, each
with a confidence score and a short reason.

```bash
sudo nestor recommend nvme0n1
sudo nestor rec nvme0n1 -d 15
```

**Arguments:** same as `classify` (`device`, `--duration`/`-d`).

---

### `apply` (alias: `a`)

Runs the same detection + recommendation pipeline as `recommend`, then **applies**
the top-ranked scheduler to the device:

```
echo <scheduler> > /sys/block/<device>/queue/scheduler
```

```bash
sudo nestor apply nvme0n1
sudo nestor a nvme0n1 -d 10
```

> ⚠️ This is the only command that changes live system state. `classify`,
> `recommend`, `monitor`, and `benchmark` are read-only/observational by
> comparison (aside from writing telemetry/dataset files under `/tmp/nestor/`).

**Arguments:** same as `classify` (`device`, `--duration`/`-d`).

---

### `monitor` (aliases: `mon`, `m`)

Continuously samples short telemetry windows and prints a live workload +
confidence line, repeating until you press `Ctrl+C`.

```bash
sudo nestor monitor nvme0n1
sudo nestor m nvme0n1 -i 5
```

**Arguments:**
- `device` (positional, optional) — same as above.
- `--interval` / `-i` — sampling interval in seconds between updates. Defaults to
  `config.DEFAULT_MONITOR_INTERVAL`. (Note: `monitor` uses `--interval`, not
  `--duration`.)

---

### `benchmark` (aliases: `bench`, `b`)

Runs the benchmark suite (`collect_dataset.sh`) to generate **labeled** training
data via controlled `fio` runs. This is separate from the live inference commands
above and is used to (re)build the dataset that `train_model.py` trains on.

```bash
sudo nestor benchmark nvme0n1
sudo nestor bench nvme0n1
```

**Arguments:**
- `device` (positional, optional) — same as above.

---

## 4. Examples

```bash
# Quick classification with default duration
sudo nestor c nvme0n1

# Longer sample for a more confident read
sudo nestor c nvme0n1 -d 30

# Get scheduler suggestions without changing anything
sudo nestor rec nvme0n1

# Apply the recommended scheduler
sudo nestor a nvme0n1

# Watch workload shift in real time, sampling every 5s
sudo nestor m nvme0n1 -i 5

# Regenerate training data
sudo nestor bench nvme0n1
```

---

## 5. Tips & Troubleshooting

- **Low/flat confidence in `classify`:** usually means light I/O during the
  collection window (not enough signal to separate classes) — try again with a
  busier device or a longer `--duration`. Persistent flatness even under load may
  indicate the trained model's feature distribution doesn't match live conditions;
  worth checking with `eda.py` / `feature_importance.py` against a fresh CSV.
- **`RuntimeError: Telemetry collection failed. No CSV was generated.`:** almost
  always means the eBPF loader binary is stale relative to source changes. Rebuild:
  ```bash
  cd live_telemetry/ebpf
  make clean
  make
  ```
- **`Ring buffer polling failed: -4` in the logs:** this is `-EINTR`, expected
  when the loader is interrupted by `SIGINT` during normal shutdown — not an error
  you need to act on.
- **`sudo: nestor: command not found`:** `sudo` doesn't use your shell's `PATH`, so
  it won't see `venv/bin` even if plain `nestor` works. See the symlink fix in
  [Section 1](#1-installation), or call `sudo ./venv/bin/nestor ...` directly.
- **`pip install -e .` fails with "Multiple top-level packages discovered":**
  setuptools can't auto-guess which of `ml`, `cli`, `live_telemetry` to package.
  Add this to `pyproject.toml` to include all three explicitly:
  ```toml
  [tool.setuptools.packages.find]
  include = ["cli*", "live_telemetry*", "ml*"]
  ```
- **Alias caveat:** internally, `args.command` reflects whichever alias you typed
  (e.g. `"c"` rather than `"classify"`). This only matters if you're extending
  `commands.py`/`main.py` and branching on `args.command` directly.

---

## 6. Command Cheat Sheet

```
nestor classify   [device] [-d SECONDS]     # c
nestor recommend  [device] [-d SECONDS]     # rec, r
nestor apply      [device] [-d SECONDS]     # a
nestor monitor    [device] [-i SECONDS]     # mon, m
nestor benchmark  [device]                  # bench, b
nestor --version
nestor --help
nestor <command> --help
```