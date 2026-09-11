# Checkpoint and rewind in place (Python)

Install a package and write a file in a running sandbox, then snapshot it. Wreck
both — uninstall the package, delete the file — and assert the damage happened.
Then `revert()` to the snapshot and assert the file's SHA-256 and the package
both came back.

Unlike [forking a snapshot](../sandbox-snapshot-fork-py), a revert restores the
sandbox you already hold. There is no second VM and no new id, so it fits a
one-VM concurrency limit without killing anything first. It earns its place when
the state can't be rebuilt from a script because nobody wrote one — an agent's
environment after forty improvised steps, say.

- **Reconnect after reverting.** Revert rewinds the guest's memory, control
  channel included. `reconnect()` returns immediately while the channel still
  reports connected, so the script pauses briefly before calling it.
- **It is not fast.** On 2026-09-08 revert took 9.5s–58.9s, median 23.4s (n=8,
  `base` template). A fresh create plus a short setup script took 8.7s. If a
  script can rebuild your state, rebuilding is usually quicker.
- **It has refused before.** Worldline recorded `Not revertable` from the gateway
  on 2026-09-01; it reverted cleanly a week later. If `revert()` raises, forking
  from the same snapshot is the fallback.
- **Snapshots outlive the VM that made them**, so the script deletes it
  explicitly, after the VM is killed.

## Run

```bash
cd examples/sandbox-checkpoint-rewind-py
pip install -r requirements.txt
export SOLARI_API_KEY=slr_live_...   # https://console.getsolari.com
python main.py
```

In PowerShell, use `$env:SOLARI_API_KEY = 'slr_live_...'` instead of `export`.
The script reads the environment variable; it does not load `.env` automatically.
Run without Python's `-O` flag, which disables assertions.

Expected output: the checkpoint, the damage, then the restored digest and flask
version, followed by confirmation of cleanup. This uses a real Solari sandbox and
a persistent snapshot; normal usage charges apply.

Source: [`main.py`](main.py). Extracted from
[Hindsight](../../applications/hindsight), which gives a coding agent
`checkpoint` and `rewind` as tools.
