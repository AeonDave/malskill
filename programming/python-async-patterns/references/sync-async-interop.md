# Sync/async interoperability

## Don’t block the event loop

Blocking examples:
- `time.sleep()`
- sync HTTP clients (`requests`) used inside async functions
- CPU-heavy loops

## Offload blocking work

### to_thread (Python 3.9+)

```python
result = await asyncio.to_thread(blocking_fn, arg1, arg2)
```

Use when:
- you must use a sync library
- the operation is short enough that threads are acceptable

## Executors

Use executors for fine control or process pools for CPU work.

## References

- https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread
