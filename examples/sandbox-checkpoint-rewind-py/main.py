"""Checkpoint a running sandbox, wreck it, and revert it in place.

Extracted from Hindsight (applications/hindsight), which gives a coding agent
these two calls as tools.
"""

import asyncio
import hashlib
import os
import time
from contextlib import AsyncExitStack

from solari_sandbox import SandboxClient

PATH = "/tmp/notes.txt"
NOTES = "Written before the checkpoint.\n"


async def sh(sandbox, command: str):
    # Commands are argv, not shell lines: run("a; b") looks for a binary named "a; b".
    return await sandbox.commands.run("sh", args=["-c", command])


async def main() -> None:
    async with (
        SandboxClient(
            api_key=os.environ["SOLARI_API_KEY"], base_url="https://api.getsolari.com"
        ) as client,
        AsyncExitStack() as cleanup,
    ):
        sandbox = await client.create(template="base", timeout_ms=300_000)
        # The VM is killed before the snapshot is deleted: the inner stack exits first.
        async with AsyncExitStack() as vm_cleanup:
            vm_cleanup.push_async_callback(sandbox.close)
            vm_cleanup.push_async_callback(client.kill, sandbox.sandboxId)
            await sandbox.connect()

            # State no setup script describes: a file, and a package installed by hand.
            await sandbox.files.write(PATH, NOTES)
            installed = await sh(sandbox, "pip install --quiet flask")
            assert installed.exitCode == 0, installed.stderr
            expected = hashlib.sha256(NOTES.encode()).hexdigest()

            snapshot = await sandbox.snapshot("checkpoint-rewind-demo")
            cleanup.push_async_callback(client.delete_snapshot, snapshot)
            print("checkpoint: taken")

            await sh(sandbox, f"pip uninstall -y -q flask; rm -f {PATH}")
            assert (await sh(sandbox, "python3 -c 'import flask'")).exitCode != 0
            assert (await sh(sandbox, f"test -e {PATH}")).exitCode != 0
            print("wrecked   : flask uninstalled, notes deleted")

            started = time.perf_counter()
            await sandbox.revert(snapshot)
            elapsed = time.perf_counter() - started
            # Revert rewinds the guest's memory, control channel included, so the
            # connection has to be re-established. reconnect() does nothing while
            # the channel still reports connected; give the drop a moment first.
            await asyncio.sleep(1.0)
            await sandbox.reconnect()

            digest = hashlib.sha256(await sandbox.files.read(PATH)).hexdigest()
            assert digest == expected, "revert did not restore the notes"
            flask = await sh(sandbox, "python3 -c 'import flask; print(flask.__version__)'")
            assert flask.exitCode == 0, "revert did not restore the package"
            print(f"reverted  : in place, same sandbox, {elapsed:.1f}s")
            print(f"notes     : SHA-256 {digest}")
            print(f"flask     : {flask.stdout.strip()}, importable again")
    print("Sandbox and snapshot deleted.")


if __name__ == "__main__":
    asyncio.run(main())
