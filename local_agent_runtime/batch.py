from __future__ import annotations

from dataclasses import asdict
import asyncio

from .engine import Engine


async def run_batch(
    engine_factory,
    records: list[tuple[str, dict]],
    workers: int = 4,
) -> list[dict]:
    if workers < 1:
        raise ValueError("workers must be positive")

    semaphore = asyncio.Semaphore(workers)

    async def one(item_id: str, inputs: dict):
        async with semaphore:
            engine: Engine = engine_factory()
            result = await engine.run(inputs, run_id=item_id)
            return asdict(result)

    tasks = [
        asyncio.create_task(one(item_id, inputs))
        for item_id, inputs in records
    ]
    return await asyncio.gather(*tasks)
