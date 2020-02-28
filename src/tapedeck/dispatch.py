from itertools import count

from trio_repl import TrioRepl
from trignalc import main as signal

from prompt_toolkit.patch_stdout import patch_stdout

from .aria2.proxy import CMD as aria2_cmd
from .aria2.format import FMT as aria2_fmt

from .mpd.proxy import CMD as mpd_cmd

from .etree.proxy import CMD as etree_cmd
from .etree.format import FMT as etree_fmt

from .config import PS1
from .parser import parse

class CommandNotFound(Exception):
    pass

class Dispatch:
    def __init__(self, aria2=None, mpd=None, redis=None, etree=None):
        """Start up proxy services"""
        self.namespace = ""
        self.aria2 = aria2
        self.mpd = mpd
        self.redis = redis
        self.etree = etree

    def PS1(self):
        if self.namespace == "mpd.":
            return PS1.format(namespace="mpd")
        elif self.namespace  == "aria2.":
            return PS1.format(namespace="aria2")
        elif self.namespace  == "etree.":
            return PS1.format(namespace="etree")
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

        else:
            raise CommandNotFound()
