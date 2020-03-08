import trio
from functools import partial
from pyudev import Context, Monitor


class UdevProxy:
    def __init__(self, nursery):
        self.nursery = nursery
        self.context = Context()

    async def __aenter__(self):
        self.nursery.start_soon(partial(
            trio.to_thread.run_sync,
            self.sound_listener,
            cancellable=True
        ))
        self.nursery.start_soon(partial(
            trio.to_thread.run_sync,
            self.storage_listener,
            cancellable=True
        ))
        return self

    def sound_listener(self):
        monitor = Monitor.from_netlink(self.context)
        monitor.filter_by("sound")
        for device in iter(monitor.poll, None):
            print(device.action, device.sys_path)

    def storage_listener(self):
        monitor = Monitor.from_netlink(self.context)
        monitor.filter_by("block")
        for device in iter(monitor.poll, None):
            if 'ID_FS_TYPE' in device:
                print('{0} partition {1}'.format(
                    device.action,
                    device.get('ID_FS_LABEL')
                ))

    async def __aexit__(self, *_):
        pass
