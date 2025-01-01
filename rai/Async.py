import asyncio
from typing import Any


class AsyncTaskManager:
    """
    A robust class to manage asynchronous tasks by name and process each
    task's result immediately upon completion.
    """

    def __init__(self) -> None:
        """
        Initialize an empty collection for storing tasks.
        """
        self._tasks = []

    def add_task(self, coro: Any, name: str) -> None:
        """
        Add a new coroutine as a named task to the manager.

        :param coro: The coroutine to schedule.
        :param name: The name you want to assign to this task.
        """
        task = asyncio.create_task(coro, name=name)
        self._tasks.append(task)

    async def run(self, callback=None) -> None:
        """
        Start all tasks and handle their results in the order they complete.
        A direct approach where you supply a callback function.

        :param callback:
            An optional function that accepts (task_name, result/exception).
        """
        for completed_task in asyncio.as_completed(self._tasks):
            try:
                result = await completed_task
                if callback:
                    callback(completed_task.get_name(), result)
            except Exception as exc:
                if callback:
                    callback(completed_task.get_name(), exc)

        # Clear tasks if you don’t plan to reuse them.
        self._tasks.clear()

    async def run_yield(self):
        """
        Start all tasks and yield (task_name, result) as each finishes.
        If a task raises an exception, yield (task_name, exception) instead.

        This is an async generator, so you'll iterate over it with:
            async for task_name, result in manager.run_yielding():
                ...
        """
        for completed_task in asyncio.as_completed(self._tasks):
            try:
                result = await completed_task
                yield (completed_task.get_name(), result)
            except Exception as exc:
                yield (completed_task.get_name(), exc)

        # Clear tasks if you don’t plan to reuse them.
        self._tasks.clear()


# -----------------------
# Example usage
# -----------------------

async def fetch_data_1():
    await asyncio.sleep(1)
    return "Data from fetch_data_1"


async def fetch_data_2():
    await asyncio.sleep(2)
    return "Data from fetch_data_2"


async def main():
    manager = AsyncTaskManager()
    manager.add_task(fetch_data_1(), "Fetch1")
    manager.add_task(fetch_data_2(), "Fetch2")

    print("Using run() with a callback:")

    def my_callback(name, result):
        if isinstance(result, Exception):
            print(f"[ERROR] {name} threw an exception: {result}")
        else:
            print(f"[OK] {name} returned: {result}")

    await manager.run(callback=my_callback)

    # Add tasks again (the manager's list was cleared)
    manager.add_task(fetch_data_1(), "Fetch1")
    manager.add_task(fetch_data_2(), "Fetch2")

    print("\nUsing run_yielding() to handle results on-the-fly:")
    async for name, result in manager.run_yielding():
        if isinstance(result, Exception):
            print(f"[ERROR] {name} threw an exception: {result}")
        else:
            print(f"[OK] {name} returned: {result}")


if __name__ == "__main__":
    asyncio.run(main())
