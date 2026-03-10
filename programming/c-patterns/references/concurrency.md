# Concurrency in C

## Thread model

C11 introduced `<threads.h>` (`thrd_t`, `mtx_t`, `cnd_t`). POSIX pthreads remain more widely used in practice.

## pthreads basics

```c
#include <pthread.h>
#include <stdio.h>

void *worker(void *arg) {
    int *val = (int *)arg;
    printf("worker got %d\n", *val);
    return NULL;
}

int main(void) {
    pthread_t t;
    int data = 42;
    pthread_create(&t, NULL, worker, &data);
    pthread_join(t, NULL);
    return 0;
}
```

## Mutex

```c
pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;

pthread_mutex_lock(&mu);
/* critical section */
pthread_mutex_unlock(&mu);

pthread_mutex_destroy(&mu);
```

## C11 Atomics (`<stdatomic.h>`)

Prefer atomics for simple counters over full mutexes.

```c
#include <stdatomic.h>

atomic_int counter = ATOMIC_VAR_INIT(0);

// Thread-safe increment (sequentially consistent)
atomic_fetch_add(&counter, 1);

// Load with explicit ordering
int val = atomic_load_explicit(&counter, memory_order_acquire);
```

## Windows threads (Win32)

```c
#include <windows.h>

DWORD WINAPI worker(LPVOID arg) {
    /* ... */
    return 0;
}

HANDLE h = CreateThread(NULL, 0, worker, NULL, 0, NULL);
WaitForSingleObject(h, INFINITE);
CloseHandle(h);

// Critical section (faster than Mutex for intra-process locking)
CRITICAL_SECTION cs;
InitializeCriticalSection(&cs);
EnterCriticalSection(&cs);
/* critical section */
LeaveCriticalSection(&cs);
DeleteCriticalSection(&cs);
```

## Rules

- Avoid shared mutable state; prefer message-passing or work queues.
- Always initialize mutexes before use.
- Document which mutex protects which data.
- Prefer `atomic_*` for single counters; use mutexes for compound state.
- Never lock one mutex while holding another (potential deadlock) without a documented lock order.

## Tools for race detection

- **Linux**: `clang -fsanitize=thread` (TSan)
- **Linux**: `helgrind` (Valgrind tool): `valgrind --tool=helgrind ./foo`
- **Windows (MSVC)**: Thread Sanitizer via `/fsanitize=address` is incomplete for races; use WinDbg or VS Concurrency Visualizer.

## References

- POSIX pthreads: https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/pthread.h.html
- C11 stdatomic: https://en.cppreference.com/w/c/atomic
