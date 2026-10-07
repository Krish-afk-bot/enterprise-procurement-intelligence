"""Phase 3: Redis live verification via the application cache abstraction."""

from __future__ import annotations

import asyncio
import os
import sys

REDIS_URL = "redis://localhost:6379/0"


async def main() -> None:
    from app.providers.cache import RedisCache

    cache = RedisCache(REDIS_URL)

    # 1. status
    status = await cache.status()
    print(f"status.available={status.available}  detail={status.detail!r}")
    assert status.available, f"Redis not available: {status.detail}"

    # 2. set / get string
    await cache.set("phase3:str", "hello-redis")
    val = await cache.get("phase3:str")
    print(f"get after set: {val!r}")
    assert val == "hello-redis", f"expected 'hello-redis', got {val!r}"

    # 3. set / get dict (serialisation)
    data = {"supplier": "Acme Corp", "price": 92.0, "currency": "USD"}
    await cache.set("phase3:dict", data)
    result = await cache.get("phase3:dict")
    print(f"dict round-trip: {result}")
    assert result == data, f"dict mismatch: {result}"

    # 4. TTL — set with 5-second TTL; key must still exist immediately after
    await cache.set("phase3:ttl", "expires_soon", ttl_seconds=5)
    ttl = await cache.ttl("phase3:ttl")
    print(f"TTL on fresh key: {ttl}s")
    assert ttl is not None and ttl > 0, f"expected positive TTL, got {ttl}"

    # 5. cache miss
    missing = await cache.get("phase3:definitely_not_set")
    print(f"missing key returns: {missing!r}")
    assert missing is None

    # 6. delete
    await cache.set("phase3:del", "to_delete")
    await cache.delete("phase3:del")
    gone = await cache.get("phase3:del")
    print(f"after delete: {gone!r}")
    assert gone is None, f"expected None after delete, got {gone!r}"

    # 7. incr (rate-limit counter pattern)
    count1 = await cache.incr("phase3:counter", ttl_seconds=60)
    count2 = await cache.incr("phase3:counter", ttl_seconds=60)
    count3 = await cache.incr("phase3:counter", ttl_seconds=60)
    print(f"incr sequence: {count1}, {count2}, {count3}")
    assert count1 == 1
    assert count2 == 2
    assert count3 == 3

    # 8. clear_prefix
    await cache.set("phase3:prefix:a", "a")
    await cache.set("phase3:prefix:b", "b")
    cleared = await cache.clear_prefix("phase3:prefix:")
    print(f"clear_prefix removed {cleared} keys")
    assert cleared >= 2
    assert await cache.get("phase3:prefix:a") is None

    # 9. cleanup
    for key in ("phase3:str", "phase3:dict", "phase3:ttl", "phase3:counter"):
        await cache.delete(key)

    await cache.aclose()
    print("✓  Redis live verification PASSED")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
