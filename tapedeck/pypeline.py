"""Handle subprocesses and pipes."""
import os
import shlex

from trio import subprocess


class Producer():
    """A subprocess that produces output."""

    cmd = None
    env = os.environ
    proc = None
    result = None
    stat = None

    def __init__(self, command, config=None):
        """Get the command redy to run."""
        self.cmd = shlex.split(command)
        for key, val in config.items():
            self.env[key] = val

    async def run_with_output(self):
        """Run the command and return the output."""
        self.proc = subprocess.Process(
            self.cmd,
            stdout=subprocess.PIPE,
            env=self.env
        )
        async with self.proc as proc:
            await proc.wait()
            self.stat = proc.returncode

            # Put the output stream into one string
            self.result = b''
            async with proc.stdout as out:
                some = await out.receive_some(8)
                while some:
                    self.result += some
                    some = await out.receive_some(8)
        return self.read()

    def read(self):
        """Read the decoded output of the command."""
        return self.result.decode('utf-8').strip()
