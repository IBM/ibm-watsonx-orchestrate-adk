import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Coroutine, TypeVar, Optional

T = TypeVar("T")


def run_coroutine_sync(coroutine: Coroutine[Any, Any, T], timeout: Optional[float] = None) -> T:
    """Run an async coroutine synchronously from any calling context.

    Handles three situations:
    - No running event loop: uses ``asyncio.run()``.
    - Running loop on the main thread (but not yet executing): calls
      ``loop.run_until_complete()`` directly.
    - Running loop, called from a **thread-pool thread** (e.g. when TRM
      dispatches a ``PythonTool`` via ``loop.run_in_executor``): schedules
      the coroutine on the existing loop via
      ``asyncio.run_coroutine_threadsafe`` and blocks until done.

    .. warning:: **Deadlock risk in the thread-pool path**

        When this function is called from a non-main thread while a running
        event loop exists (the ``else`` branch), it schedules the coroutine on
        that loop and blocks the current thread with ``.result()``.  If the
        async function body itself enqueues further work on the *same* thread
        pool (e.g. via ``loop.run_in_executor(None, ...)`` with the default
        executor) *and* the pool is fully saturated, the result future will
        never resolve and the call will deadlock.

        The proper long-term fix is for the TRM server to call
        ``PythonTool.__call__`` from a context where it can directly ``await``
        the coroutine (requires TRM-side changes).  Until then, async tool
        functions should avoid calling ``loop.run_in_executor(None, ...)``
        without an explicit, bounded executor.
    """
    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coroutine)
        finally:
            new_loop.close()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    if threading.current_thread() is threading.main_thread():
        if not loop.is_running():
            return loop.run_until_complete(coroutine)
        else:
            with ThreadPoolExecutor() as pool:
                future = pool.submit(run_in_new_loop)
                return future.result(timeout=timeout)
    else:
        return asyncio.run_coroutine_threadsafe(coroutine, loop).result()