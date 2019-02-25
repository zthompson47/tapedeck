import sys

import trio


async def run():
    async with trio.wrap_file(sys.stdin) as stdin:
        while True:
            await stdin.flush()
            keyboard = await stdin.read(8)
            if keyboard == 'q':
                print('!!!!!!!!!!!!1')
                sys.exit(0)

trio.run(run)
