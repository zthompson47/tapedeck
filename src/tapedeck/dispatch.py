from .pulse import CMD as pulse_cmd
from .format import (
    FMT_ARIA2 as aria2_fmt,
    FMT_ETREE as etree_fmt,
    FMT_MPD as mpd_fmt,
    FMT_PULSE as pulse_fmt,
)
from .config import PS1
from .language import parse
from .util import CommandRegistry


class CommandNotFound(Exception):
    pass


class Dispatch:
    def __init__(self):
        self.etree_cmd = CommandRegistry.namespace["etree"]
        self.mpd_cmd = CommandRegistry.namespace["mpd"]
        self.aria2_cmd = CommandRegistry.namespace["aria2"]
        self.namespace = None
        self.proxies = {}

    def add_proxy(self, name, proxy):
        self.proxies[name] = proxy

    def PS1(self):
        if self.namespace is None:
            return PS1.format(namespace="~")
        else:
            return PS1.format(namespace=f"~{self.namespace}")

    async def route(self, request):
        """Parse request and execute command."""
        if not request:
            raise CommandNotFound()
        program = parse(request)
        command = program[0][0]
        result = None

        # Namespace
        if command == "~":
            self.namespace = ""
        elif command == "aria2.~":
            self.namespace = "aria2"
        elif command == "mpd.~":
            self.namespace = "mpd"
        elif command == "etree.~":
            self.namespace = "etree"
        elif command == "pulse.~":
            self.namespace = "pulse"

        # Utilities
        elif command == "trio":
            from trio_repl import TrioRepl
            await TrioRepl().run(locals())
        elif command == "trignalc":
            from trignalc import main as signal
            await signal()

        # MPD
        elif self.namespace == "mpd" or command.startswith("mpd."):
            if command.startswith("mpd."):
                cmd_name = program[0][0][len("mpd."):]
            else:
                cmd_name = program[0][0]
            args = program[0][1:]
            meth = self.mpd_cmd[cmd_name]
            response = await meth(self.proxies["mpd"], *args)
            format = mpd_fmt.get(cmd_name, mpd_fmt["_default"])
            result = format(response)

        # Aria2
        elif self.namespace == "aria2" or command.startswith("aria2."):
            if command.startswith("aria2."):
                cmd_name = program[0][0][len("aria2."):]
            else:
                cmd_name = program[0][0]
            args = program[0][1:]
            meth = self.aria2_cmd[cmd_name]
            response = await meth(self.proxies["aria2"], *args)
            format = aria2_fmt.get(cmd_name, aria2_fmt["_default"])
            result = format(response)

        # RSS (Etree)
        elif self.namespace == "etree" or command.startswith("etree."):
            if command.startswith("etree."):
                cmd_name = program[0][0][len("etree."):]
            else:
                cmd_name = program[0][0]
            args = program[0][1:]
            meth = self.etree_cmd[cmd_name]
            response = await meth(self.proxies["etree"], *args)
            format = etree_fmt.get(cmd_name, etree_fmt["_default"])
            result = format(response)

        # Pulseaudio
        elif self.namespace == "pulse" or command.startswith("pulse."):
            if command.startswith("pulse."):
                cmd_name = program[0][0][len("pulse."):]
            else:
                cmd_name = program[0][0]
            args = program[0][1:]
            meth = pulse_cmd[cmd_name]
            response = await meth(self.proxies["pulse"], *args)
            format = pulse_fmt.get(cmd_name, pulse_fmt["_default"])
            result = format(response)

        else:
            raise CommandNotFound()

        return result
