# Concurrency in C++

## Prefer high-level abstractions

Use standard library abstractions before reaching for raw threads.

Order of preference:
1. `std::async` / `std::future` for single tasks
2. `std::jthread` (C++20) for RAII-managed threads with stop token
3. `std::thread` with explicit join/detach
4. Raw platform APIs only when necessary

## std::jthread (C++20)

```cpp
#include <thread>
#include <stop_token>

std::jthread worker([](std::stop_token st) {
    while (!st.stop_requested()) {
        // do work
    }
});

// Automatically requests stop and joins on destruction
```

## std::mutex and std::lock_guard

```cpp
#include <mutex>
#include <vector>

std::mutex mu;
std::vector<int> shared;

void push(int v) {
    std::lock_guard<std::mutex> lock(mu); // RAII, unlocks on exit
    shared.push_back(v);
}
```

For multiple mutexes (deadlock-safe):

```cpp
std::scoped_lock lk(mu1, mu2); // std::scoped_lock acquires all atomically
```

## std::atomic

```cpp
#include <atomic>

std::atomic<int> counter{0};
counter.fetch_add(1, std::memory_order_relaxed); // fast counter
int v = counter.load(std::memory_order_acquire);
```

## std::condition_variable

```cpp
#include <condition_variable>

std::mutex mu;
std::condition_variable cv;
bool ready = false;

// Producer
{
    std::lock_guard lk(mu);
    ready = true;
}
cv.notify_one();

// Consumer
{
    std::unique_lock lk(mu);
    cv.wait(lk, [] { return ready; }); // predicate to avoid spurious wakeup
}
```

## Cancellation (C++20)

```cpp
std::stop_source src;
std::stop_token  tok = src.get_token();

std::jthread t([tok]() {
    while (!tok.stop_requested()) { /* work */ }
});

src.request_stop(); // signal cancellation
```

## std::async / std::future

```cpp
#include <future>

auto fut = std::async(std::launch::async, []() -> int {
    return heavy_compute();
});

int result = fut.get(); // blocks until done
```

## Common footguns

| Footgun | Fix |
|---------|-----|
| Detaching a thread that captures `this` | Use `jthread` with stop token; copy needed data |
| Locking same mutex twice (non-recursive) | Use one lock scope; or `recursive_mutex` |
| `condition_variable::wait` without predicate | Always pass a predicate lambda |
| Returning `std::future` from `std::async` and ignoring it | Futures block on destruction — handle the return value |
| Data race on `std::string`/`std::vector` across threads | Protect with mutex or use lock-free structures |

## Tooling for races

```sh
# Linux — TSan (not compatible with ASan in same build)
clang++ -fsanitize=thread -g foo.cpp -o foo && ./foo

# Linux — Helgrind (Valgrind)
valgrind --tool=helgrind ./foo

# MSVC / Windows — VS Concurrency Visualizer (profiler plugin)
# WinDbg: monitor thread states
windbg -c "~* k; q" foo.exe
```

## References

- `std::jthread`: https://en.cppreference.com/w/cpp/thread/jthread
- `std::atomic`: https://en.cppreference.com/w/cpp/atomic/atomic
- C++ Core Guidelines: concurrency section https://github.com/isocpp/CppCoreGuidelines/blob/master/CppCoreGuidelines.md#cp-concurrency-and-parallelism
