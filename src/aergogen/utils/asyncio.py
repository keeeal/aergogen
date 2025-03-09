from asyncio import Semaphore, gather
from typing import Any, Coroutine, Optional, TypeVar

T = TypeVar("T")


def gather_with_concurrency(
    *coros_or_futures: Coroutine[Any, Any, T],
    return_exceptions: bool = False,
    concurrency: Optional[int] = None,
) -> Coroutine[Any, Any, list[T]]:
    semaphore = Semaphore(concurrency or len(coros_or_futures))

    async def task(coro: Coroutine[Any, Any, T]) -> T:
        async with semaphore:
            return await coro

    return gather(
        *(task(coro) for coro in coros_or_futures),
        return_exceptions=return_exceptions,
    )
