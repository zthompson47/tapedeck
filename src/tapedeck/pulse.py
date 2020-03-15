import logging

import trio
from jeepney.bus_messages import message_bus
from jeepney.wrappers import MessageGenerator, new_method_call

from .config import PULSE
from .dbus2 import TrioDBusProxy
from .util import CommandRegistry

#CMD = {}
#
#
#def cmd(name):
#    """Fill CMD with list of commands."""
#
#    def decorator(func):
#        CMD[name] = func
#        return func
#
#    return decorator


class CliRequest:
    def __init__(self, command, *params):
        self.command = command
        self.params = params

    def send(self):
        """Generate netword data for this request."""
        if self.params:
            params = [
                param.encode("utf-8") for param in self.params
            ]
            params_str = b" " + b" ".join(params)
            command = self.command.encode("utf-8") + params_str
        else:
            command = self.command.encode("utf-8")
        return command + b"\n"


class CliResponse:
    def __init__(self, data):
        self.data = data

    def decode(self):
        return self.data


class TrioPulseProxy:
    def __init__(self, uri):
        self.uri = uri

    async def __aenter__(self):
        self.sock = await trio.open_unix_socket(self.uri)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        logging.debug(f"==>> {exc_type}\n{exc}\n{tb}")
        await self.sock.aclose()

    async def run_cmd(self, command, *params, expect_response=True):
        request = CliRequest(command, *params)
        await self.sock.send_all(request.send())
        if expect_response:
            response = CliResponse(await self.sock.receive_some(65536))
            return response.decode()
        else:
            return b""

#    @cmd("list-sinks")
#    async def list_sinks(self):
#        return await self.run_cmd("list-sinks")
#
#    @cmd("set-default-sink")
#    async def set_default_sink(self, sink_id):
#        return await self.run_cmd(
#            "set-default-sink", sink_id, expect_response=False
#        )


class PulseAddress(MessageGenerator):
    interface = "org.freedesktop.DBus.Properties"
    object_path = "/org/pulseaudio/server_lookup1"

    def __init__(self, bus_name=None):
        self.bus_name = bus_name
        
    def Get(self, interface_name, property_name):
        return new_method_call(
            self, "Get", "ss", (interface_name, property_name)
        )


class PulseProperties(MessageGenerator):
    interface = "org.freedesktop.DBus.Properties"
    object_path = "/org/pulseaudio/core1"
    bus_name = "org.PulseAudio.Core1"

    def __init__(self):
        pass

    def Get(self, interface_name, property_name):
        return new_method_call(
            self, "Get", "ss", (interface_name, property_name)
        )


class PulseProxyWrapper:
    def __init__(self, proxy):
        self.proxy = proxy

    cmd = CommandRegistry("pulse").cmd

    @cmd("list_sinks")
    async def list_sinks(self):
        sinks = await self.proxy.Get("org.PulseAudio.Core1", "Sinks")
        return sinks[0][1]


async def open_pulse_proxy(nursery, exit_stack):
    _mbus = TrioDBusProxy(message_bus, nursery)
    mbus = await exit_stack.enter_async_context(_mbus)
    pulse_owner = await mbus.GetNameOwner("org.PulseAudio1")
    lookup_msggen = PulseAddress(bus_name=pulse_owner[0])
    _lookup_proxy = TrioDBusProxy(lookup_msggen, nursery)
    lookup_proxy = await exit_stack.enter_async_context(_lookup_proxy)
    owner = await lookup_proxy.Get(
        "org.PulseAudio.ServerLookup1", "Address"
    )
    pulse_msggen = PulseProperties()
    _pulse_proxy = TrioDBusProxy(
        pulse_msggen, nursery, bus=owner[0][1]
    )
    pulse_proxy = await exit_stack.enter_async_context(_pulse_proxy)
    return PulseProxyWrapper(pulse_proxy)
