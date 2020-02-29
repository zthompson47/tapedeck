from itertools import count

from trio_repl import TrioRepl
from trignalc import main as signal

from prompt_toolkit.patch_stdout import patch_stdout

from .aria2 import CMD as aria2_cmd
from .mpd import CMD as mpd_cmd
from .etree import CMD as etree_cmd
from .pulse import CMD as pulse_cmd

from .format import FMT_ARIA2 as aria2_fmt, FMT_ETREE as etree_fmt
from .config import PS1
from .parser import parse

class CommandNotFound(Exception):
    pass

class Dispatch:
    def __init__(self, aria2=None, mpd=None, redis=None, etree=None, pulse=None):
        """Start up proxy services"""
        self.namespace = ""
        self.aria2 = aria2
        self.mpd = mpd
        self.redis = redis
        self.etree = etree
        self.pulse = pulse

    def PS1(self):
        if self.namespace == "mpd.":
            return PS1.format(namespace="mpd")
        elif self.namespace  == "aria2.":
            return PS1.format(namespace="aria2")
        elif self.namespace  == "etree.":
            return PS1.format(namespace="etree")
        elif self.namespace  == "pulse.":
            return PS1.format(namespace="pulse")
        else:
            return PS1.format(namespace="~")

    async def route(self, request):
        """Parse request and execute command."""
        if not request:
            raise CommandNotFound()
        program = parse(request)

        args = request.split()
        command = None
        if args:
            command = args[0]

        # Builtins
        if command == "~":
            self.namespace = ""
        elif command == "aria2.~":
            self.namespace = "aria2."
        elif command == "mpd.~":
            self.namespace = "mpd."
        elif command == "etree.~":
            self.namespace = "etree."
        elif command == "pulse.~":
            self.namespace = "pulse."
        elif command == "trio":
            await TrioRepl().run(locals())
        elif command == "trignalc":
            await signal()

        # MPD
        elif self.namespace == "mpd."or command.startswith("mpd."):
            if command.startswith("mpd."):
                cmd_name = program[0][0][4:]
            else:
                cmd_name = program[0][0]
            args = program[0][1:]
            meth = mpd_cmd[cmd_name]
            await meth(self.mpd, *args)

        # Aria2
        elif self.namespace == "aria2."or command.startswith("aria2."):
            if command.startswith("aria2."):
                cmd_name = program[0][0][6:]
            else:
                cmd_name = program[0][0]
            args = program[0][1:]
            meth = aria2_cmd[cmd_name]
            response = await meth(self.aria2, *args)
            format = aria2_fmt.get(cmd_name, aria2_fmt["_default"])
            print("-------->>>>>>>!!!!!!!!!!!!!!", flush=True)
            print(format(response), flush=True)

        # RSS (Etree)
        elif self.namespace == "etree."or command.startswith("etree."):
            if command.startswith("etree."):
                cmd_name = program[0][0][6:]
            else:
                cmd_name = program[0][0]
            args = program[0][1:]
            meth = etree_cmd[cmd_name]
            response = await meth(self.etree, *args)
            format = etree_fmt.get(cmd_name, etree_fmt["_default"])
            print(format(response))

        # Pulseaudio
        elif self.namespace == "pulse."or command.startswith("pulse."):
            if command.startswith("pulse."):
                cmd_name = program[0][0][6:]
            else:
                cmd_name = program[0][0]
            args = program[0][1:]
            meth = pulse_cmd[cmd_name]
            response = await meth(self.pulse, *args)
            print(response.decode("utf-8"))

        else:
            raise CommandNotFound()
