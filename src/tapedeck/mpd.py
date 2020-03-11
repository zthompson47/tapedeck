from functools import partial

import trio

CMD = {}


def cmd(name):
    """Fill CMD with list of commands."""

    def decorator(func):
        CMD[name] = func
        return func

    return decorator


class MPDRequest:
    def __init__(self, command, *params):
        self.command = command
        self.params = params

    def send(self):
        if self.params:
            params = [
                param.encode("utf-8") for param in self.params
            ]
            params_str = b" \"" + b"\" \"".join(params) + b"\""
            command = self.command.encode("utf-8") + params_str
        else:
            command = self.command.encode("utf-8")
        return command + b"\n"


class MPDConnection:
    def __init__(self):
        self.queue = []
        self.version = None
        self.initialized = False
        self.in_idle = False

    def _decode(self, data):
        text = data.decode("utf-8").rstrip()
        _message = []
        for line in text.split("\n"):
            if line and line != "OK":
                _message.append(line)
        return "\n".join(_message)

    def send(self, request):
        if request.command == "idle":
            self.in_idle = True
        elif request.command == "noidle":
            self.in_idle = False
        return request.send()

    def receive_event(self, event):
        self.in_idle = False

    def receive_data(self, data):
        response = self._decode(data)
        if self.initialized:
            return response
        else:
            self.version = response[7:]
            self.initialized = True


class TrioMPDProxy:
    def __init__(self, nursery, *uri):
        self.mpd = MPDConnection()
        self.nursery = nursery
        self.uri = uri

    async def __aenter__(self):
        self.sock = await trio.open_tcp_stream(*self.uri)

        # Receive MPD greeting
        init = await self.sock.receive_some(65536)
        self.mpd.receive_data(init)
        assert self.mpd.initialized

        # Idle for events and keep connection alive
        self.idle_scope = await self.nursery.start(self.idle_task)

        return self

    async def _send_idle(self):
        idle = MPDRequest("idle")
        encoded = self.mpd.send(idle)
        await self.sock.send_all(encoded)

    async def _send_noidle(self):
        noidle = MPDRequest("noidle")
        encoded = self.mpd.send(noidle)
        await self.sock.send_all(encoded)

        confirmation = await self.sock.receive_some(65536)
        self.mpd.receive_event(confirmation)

    async def idle_task(self, task_status=trio.TASK_STATUS_IGNORED):
        await self._send_idle()
        cancel_scope = trio.CancelScope()
        task_status.started(cancel_scope)
        with cancel_scope:
            while True:
                event = await self.sock.receive_some(65536)
                self.mpd.receive_event(event)
                print("==MPD==>", event)
                await self._send_idle()

    async def __aexit__(self, *args):
        await self.sock.aclose()

    async def run_cmd(self, command, *params):
        self.idle_scope.cancel()
        await self._send_noidle()

        # Build request
        request = MPDRequest(command, *params)
        encoded = self.mpd.send(request)

        # Perform IO
        await self.sock.send_all(encoded)
        response = await self.sock.receive_some(65536)

        # Back to idle
        self.idle_scope = await self.nursery.start(self.idle_task)

        # Report results
        return self.mpd.receive_data(response)

    @cmd("add")
    async def add(self, uri):
        return await self.run_cmd("add", uri)

    @cmd("clear")
    async def clear(self):
        return await self.run_cmd("clear")

    @cmd("consume")
    async def consume(self, state):
        return await self.run_cmd("consume", state)

    @cmd("disableoutput")
    async def disable_output(self, output):
        return await self.run_cmd("disableoutput", output)

    @cmd("enableoutput")
    async def enable_output(self, output):
        return await self.run_cmd("enableoutput", output)

    @cmd("toggleoutput")
    async def toggle_output(self, output):
        return await self.run_cmd("toggleoutput", output)

    @cmd("listall")
    async def list_all(self):
        return await self.run_cmd("listall")

    @cmd("outputs")
    async def outputs(self):
        return await self.run_cmd("outputs")

    @cmd("play")  # [SONGPOS]
    async def play(self):
        return await self.run_cmd("play")

    @cmd("playlist")
    async def playlist(self):
        return await self.run_cmd("playlist")

    @cmd("shuffle")
    async def shuffle(self):
        return await self.run_cmd("shuffle")

    @cmd("status")
    async def status(self):
        return await self.run_cmd("status")

    @cmd("update")
    async def update(self):
        return await self.run_cmd("update")

    @cmd("clearerror")
    async def clear_error(self):
        return await self.run_cmd("clearerror")

    @cmd("currentsong")
    async def current_song(self):
        return await self.run_cmd("currentsong")

    @cmd("idle")  # [SUBSYSTEMS]
    async def idle(self):
        return await self.run_cmd("idle")

    @cmd("stats")
    async def stats(self):
        return await self.run_cmd("stats")

    @cmd("crossfade")  # {SECONDS}
    async def crossfade(self):
        return await self.run_cmd("crossfade")

    @cmd("mixrampdb")  # {deciBels}
    async def mix_ramp_db(self):
        return await self.run_cmd("mixrampdb")

    @cmd("mixrampdelay")  # {SECONDS}
    async def mix_ramp_delay(self):
        return await self.run_cmd("mixrampdelay")

    @cmd("random")  # {STATE}
    async def random(self):
        return await self.run_cmd("random")

    @cmd("repeat")  # {STATE}
    async def repeat(self):
        return await self.run_cmd("repeat")

    @cmd("setvol")  # {VOL}
    async def set_vol(self):
        return await self.run_cmd("setvol")

    @cmd("single")  # {STATE}
    async def single(self):
        return await self.run_cmd("single")

    @cmd("replay_gain_mode")  # {MODE}
    async def replay_gain_mode(self):
        return await self.run_cmd("replay_gain_mode")

    @cmd("replay_gain_status")
    async def replay_gain_status(self):
        return await self.run_cmd("replay_gain_status")

    @cmd("previous")
    async def previous(self):
        return await self.run_cmd("previous")

    @cmd("next")
    async def next(self):
        return await self.run_cmd("next")

    @cmd("pause")
    async def pause(self):
        return await self.run_cmd("pause")

    @cmd("stop")
    async def stop(self):
        return await self.run_cmd("stop")

    @cmd("playid")  # [SONGID]
    async def play_id(self):
        return await self.run_cmd("playid")

    @cmd("seek")  # {SONGPOS} {TIME}
    async def seek(self):
        return await self.run_cmd("seek")

    @cmd("seekid")  # {SONGPOS} {TIME}
    async def seek_id(self):
        return await self.run_cmd("seekid")

    @cmd("seekcur")  # {TIME}
    async def seek_cur(self):
        return await self.run_cmd("seekcur")

    @cmd("addid")  # {URI} [POSITION]
    async def add_id(self):
        return await self.run_cmd("addid")

    @cmd("delete")  # [{POS} | {START:END}]
    async def delete(self):
        return await self.run_cmd("delete")

    @cmd("deleteid")  # {SONGID}
    async def delete_id(self):
        return await self.run_cmd("deleteid")
