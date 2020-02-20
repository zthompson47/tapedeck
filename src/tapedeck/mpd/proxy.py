import trio

CMD = {}

def cmd(name):
    """Fill aria2.CMD with command list via this decorator."""
    def decorator(func):
        CMD[name] = func
        return func
    return decorator

class MPDProxy:
    def __init__(self, nursery, stream):
        self.scope = None
        self.stream = stream
        nursery.start_soon(self.run_scope)

    async def run_scope(self):
        async with trio.open_nursery() as nursery:
            self.scope = nursery.cancel_scope
            nursery.start_soon(self.keepalive_task)
            nursery.start_soon(self.listener_task)

    async def keepalive_task(self):
        while True:
            try:
                await self.stream.send_all(b"ping\n")
            except:
                pass
            await trio.sleep(3.333)

    async def listener_task(self):
        while True:
            try:
                response = await self.stream.receive_some(65536)
                if response != b"OK\n":
                    print("mpd", response.decode("utf-8").rstrip())
            except trio.ClosedResourceError:
                print("closed resource error")
                break

    async def runcmd(self, command, *params):
        # Encode to UTF-8 bytes
        if params:
            params = [param.encode("utf-8") for param in params]
            params_str = b" " + b" ".join(params)
            command = command.encode("utf-8") + params_str
        else:
            command = command.encode("utf-8")
        await self.stream.send_all(command + b"\n")

    @cmd("add")
    async def add(self, filename):
        await self.runcmd("add", filename)

    @cmd("clear")
    async def clear(self):
        await self.runcmd("clear")

    @cmd("consume")
    async def consume(self, state):
        await self.runcmd("consume", state)

    @cmd("disableoutput")
    async def disable_output(self, output):
        await self.runcmd("disableoutput", output)

    @cmd("enableoutput")
    async def enable_output(self, output):
        await self.runcmd("enableoutput", output)

    @cmd("toggleoutput")
    async def toggle_output(self, output):
        await self.runcmd("toggleoutput", output)

    @cmd("listall")
    async def list_all(self):
        await self.runcmd("listall")

    @cmd("outputs")
    async def outputs(self):
        await self.runcmd("outputs")

    @cmd("play")
    async def play(self):
        await self.runcmd("play")

    @cmd("playlist")
    async def playlist(self):
        await self.runcmd("playlist")

    @cmd("shuffle")
    async def shuffle(self):
        await self.runcmd("shuffle")

    @cmd("status")
    async def status(self):
        await self.runcmd("status")

    @cmd("update")
    async def update(self):
        await self.runcmd("update")
