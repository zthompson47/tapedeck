import json
from itertools import count

import trio

CMD = {}

def cmd(name):
    """Fill aria2.CMD with command list via this decorator."""
    def decorator(func):
        CMD[name] = func
        return func
    return decorator

class Aria2Proxy:
    def __init__(self, nursery, socket):
        self.nursery = nursery
        self.socket = socket
        self.id_counter = count()
        self.pending = {}
        self.nursery.start_soon(self.listener)

    async def listener(self):
        while True:
            try:
                response = await self.socket.get_message()
            except:
                break
            rsp = json.loads(response)
            if rsp.get("id") is not None:
                if self.pending.get(rsp["id"]) is not None:
                    await self.pending[int(rsp["id"])].send(rsp)
                    del(self.pending[int(rsp["id"])])
                else:
                    print("aria2", response)
            else:
                print("aria2", response)

    async def run(self, command, params=None):
        req_id = next(self.id_counter)
        req = {"jsonrpc": "2.0", "id": req_id, "method": command}
        if params:
            req["params"] = params
        await self.socket.send_message(json.dumps(req))
        ch_snd, ch_rcv = trio.open_memory_channel(0)
        self.pending[req_id] = ch_snd
        return await ch_rcv.receive()

    @cmd("addUri")
    async def add_uri(self, uri):
        return await self.run("aria2.addUri", [[uri]])

    @cmd("tellActive")
    async def tell_active(self):
        return await self.run("aria2.tellActive")

    @cmd("tellStatus")
    async def tell_status(self, gid):
        return await self.run("aria2.tellStatus", [gid])

    @cmd("listMethods")
    async def list_methods(self):
        return await self.run("system.listMethods")

    @cmd("listNotifications")
    async def list_notifications(self):
        return await self.run("system.listNotifications")

    @cmd("addTorrent")
    async def add_torrent(self, torrent):
        return await self.run("aria2.addTorrent", [torrent])

    @cmd("getPeers")
    async def get_peers(self, gid):
        return await self.run("aria2.getPeers", [gid])

    @cmd("addMetaLink")
    async def add_meta_link(self, metalink):
        return await self.run("aria2.addMetalink", [metalink])

    @cmd("remove")
    async def remove(self, gid):
        return await self.run("aria2.remove", [gid])

    @cmd("pause")
    async def pause(self, gid):
        return await self.run("aria2.pause", [gid])

    @cmd("forcePause")
    async def force_pause(self, gid):
        return await self.run("aria2.forcePause", [gid])

    @cmd("pauseAll")
    async def pause_all(self):
        return await self.run("aria2.pauseAll")

    @cmd("forcePauseAll")
    async def force_pause_all(self):
        return await self.run("aria2.forcePauseAll")

    @cmd("unpause")
    async def unpause(self, gid):
        return await self.run("aria2.unpause", [gid])

    @cmd("unpauseAll")
    async def unpause_all(self):
        return await self.run("aria2.unpauseAll")

    @cmd("forceRemove")
    async def force_remove(self, gid):
        return await self.run("aria2.forceRemove", [gid])

    @cmd("changePosition")
    async def change_position(self, gid, pos, how):
        return await self.run("aria2.changePosition", [gid, pos, how])

    @cmd("getUris")
    async def get_uris(self, gid):
        return await self.run("aria2.getUris", [gid])

    @cmd("getFiles")
    async def get_files(self, gid):
        return await self.run("aria2.getFiles", [gid])

    @cmd("getServers")
    async def get_servers(self, gid):
        return await self.run("aria2.getServers", [gid])

    @cmd("tellWaiting")
    async def tell_waiting(self, offset, num):
        return await self.run("aria2.tellWaiting", [offset, num])

    @cmd("tellStopped")
    async def tell_stopped(self, offset, num):
        return await self.run("aria2.tellStopped", [offset, num])

    @cmd("getOption")
    async def get_option(self, gid):
        return await self.run("aria2.getOption", [gid])

    @cmd("changeUri")
    async def change_uri(self, gid, fileIndex, delUris, addUris):
        return await self.run(
            "aria2.changeUri", [gid, fileIndex, delUris, addUris]
        )

    @cmd("changeOption")
    async def change_option(self, gid, options):
        return await self.run("aria2.changeOption", [gid, options])

    @cmd("getGlobalOption")
    async def get_global_option(self, options):
        return await self.run("aria2.getGlobalOption", [options])

    @cmd("changeGlobalOption")
    async def change_global_option(self):
        return await self.run("aria2.changeGlobalOption")

    @cmd("purgeDownloadResult")
    async def purge_download_result(self):
        return await self.run("aria2.purgeDownloadResult")

    @cmd("removeDownloadResult")
    async def remove_download_result(self, gid):
        return await self.run("aria2.removeDownloadResult", [gid])

    @cmd("getVersion")
    async def get_version(self):
        return await self.run("aria2.getVersion")

    @cmd("getSessionInfo")
    async def get_session_info(self):
        return await self.run("aria2.getSessionInfo")

    @cmd("shutdown")
    async def shutdown(self):
        return await self.run("aria2.shutdown")

    @cmd("forceShutdown")
    async def force_shutdown(self):
        return await self.run("aria2.forceShutdown")

    @cmd("getGlobalStat")
    async def get_global_stat(self):
        return await self.run("aria2.getGlobalStat")

    @cmd("saveSession")
    async def save_session(self):
        return await self.run("aria2.saveSession")

    @cmd("multicall")
    async def multicall(self, methods):
        return await self.run("system.multicall", [methods])
