import asyncio
from asyncio import AbstractEventLoop


class MainLoop:
    main_loop: AbstractEventLoop = asyncio.get_event_loop()
    def is_running(self):
        return self.main_loop.is_running()
    def is_closed(self):
        return self.main_loop.is_closed()
    def close(self):
        return self.main_loop.close()


class ToolThread:

    @property
    def main(self) -> MainLoop: return MainLoop()
    @property
    def io(self) -> AbstractEventLoop: return asyncio.new_event_loop()
    @staticmethod
    def run_async_function(func): return asyncio.get_event_loop().run_until_complete(func)

