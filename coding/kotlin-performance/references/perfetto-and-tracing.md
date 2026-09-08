# Perfetto and Tracing

Load when a performance symptom needs system-level attribution — jank, GC pressure, JIT bursts, I/O stalls, or when correlating app work with OS scheduling.

## Perfetto vs systrace

`systrace` is deprecated (Python 2, Android 10-). Use Perfetto:

- **UI**: `https://ui.perfetto.dev` — drag-and-drop trace file.
- **CLI recorder** (on device): `perfetto` binary, config-driven.
- **SDK** (in-app): `androidx.tracing:tracing` — adds custom slices to Perfetto tracks.

## Quick trace capture

```bash
adb shell perfetto \
  -o /data/misc/perfetto-traces/trace.perfetto-trace \
  -t 20s \
  -b 32mb \
  sched freq idle am wm gfx view binder_driver hal dalvik power camera input res
adb pull /data/misc/perfetto-traces/trace.perfetto-trace
```

Atrace categories (positional args at the end):

- `sched freq idle` — scheduler + CPU frequency + idle states (jank attribution)
- `am wm` — ActivityManager, WindowManager (startup, transitions)
- `gfx view` — graphics + view lifecycle (frame time)
- `binder_driver` — IPC (system service calls)
- `dalvik` — ART events (JIT, GC, class load)
- `hal camera input` — hardware and input pipeline

Use `--all` sparingly — trace files get huge fast.

## Config file (recommended over positional args)

`config.pbtx`:

```
buffers { size_kb: 63488 fill_policy: DISCARD }
data_sources {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "sched/sched_switch"
            ftrace_events: "sched/sched_wakeup"
            ftrace_events: "power/cpu_frequency"
            atrace_categories: "am"
            atrace_categories: "gfx"
            atrace_categories: "view"
            atrace_categories: "dalvik"
        }
    }
}
data_sources { config { name: "linux.process_stats" } }
duration_ms: 20000
```

Run:

```bash
adb shell perfetto -c - --txt -o /data/misc/perfetto-traces/trace.pb < config.pbtx
```

## Custom trace sections (in-app)

```kotlin
implementation("androidx.tracing:tracing-ktx:1.3.0")

androidx.tracing.trace("MyFeature:load") {
    repo.load()
}

// Async slice across suspend points
androidx.tracing.beginAsyncSection("MyFeature:refresh", cookie = 0)
try { withContext(Dispatchers.IO) { refresh() } }
finally { androidx.tracing.endAsyncSection("MyFeature:refresh", cookie = 0) }
```

For Compose recomposition slices, add:

```kotlin
implementation("androidx.tracing:tracing-perfetto:1.0.0")
```

Then in Macrobenchmark:

```kotlin
androidx.benchmark {
    perfettoSdkTracing = true
}
```

## Key tracks to inspect

Open the trace in Perfetto UI:

| Track | What to look for |
|-------|------------------|
| `Application` per process | Main thread activity, custom slices |
| `sched` (CPU tracks) | Which core is executing what, and for how long |
| `Choreographer#doFrame` | Every frame slice; measure duration vs the frame budget (16.6 ms / 8.3 ms / 6.9 ms for 60/120/144 Hz) |
| `am_activity_launch_time` | Cold-start attribution |
| `JIT Compiling %` | If > 5% during a user flow, missing Baseline Profile coverage |
| `HeapTaskDaemon` | GC bursts; correlate to alloc pressure |
| `binder` calls | System service IPC; long ones = latency source |
| `Choreographer` gaps | Missing frames (indicative of main-thread block) |

## Analyzing a jank frame

1. Find a `Choreographer#doFrame` slice > frame budget.
2. Scroll down to see what the main thread was doing during that slice.
3. Common culprits:
   - `View#measure` / `View#layout` cascades in view hierarchies.
   - `Compose:Recompose <FunctionName>` running unexpectedly during scroll.
   - `Binder:Transaction` calls that blocked > 1 ms.
   - `HeapTaskDaemon` running an out-of-line GC.

## SQL analysis (advanced)

Perfetto Trace Processor exposes a SQL API over the trace:

```bash
# Install the CLI
curl -O https://get.perfetto.dev/trace_processor
chmod +x trace_processor
./trace_processor trace.perfetto-trace
```

Interactive prompt:

```sql
-- Top 10 slowest slices on the main thread
SELECT slice.name, dur/1e6 AS ms
FROM slice
JOIN thread ON slice.utid = thread.utid
WHERE thread.name = 'MainThread'
ORDER BY dur DESC LIMIT 10;

-- Frame budget breach ratio
SELECT COUNT(*) AS janky
FROM slice
WHERE name = 'Choreographer#doFrame' AND dur > 16666666;    -- 60 Hz budget
```

Integrate into CI: run Macrobenchmark, feed the trace into Trace Processor, assert on p99 frame duration.

## Offline analysis with `traceconv`

Convert Perfetto proto to legacy formats:

```bash
./traceconv text trace.perfetto-trace trace.txt        # human-readable
./traceconv json trace.perfetto-trace trace.json       # JSON tracks
./traceconv systrace trace.perfetto-trace trace.html   # legacy Chrome trace format
```

## Common recording pitfalls

- Buffer overflow → set `buffers.size_kb` high (64 MB baseline for 20 s of moderate activity).
- ftrace categories not enabled → check `atrace --list_categories` on the device.
- Non-root device restricts some ftrace categories (`irq`, `power`). Most app-level analysis works without root.
- Wireless debug drops long traces — use USB for anything over 10 s.
- Trace file size scales with FPS + category count. For long recordings, use ring-buffer mode (`fill_policy: RING_BUFFER`) and read out during the run.

## Anti-patterns

- Recording without a clear question ("let me see everything") → 200 MB trace, no signal.
- Recording on a locked screen or off-screen state → no rendering events, incomplete GPU pipeline.
- Comparing traces across different devices → CPU frequency and core counts differ; not comparable.
- Ignoring the JIT slice — hidden startup cost that Baseline Profile fixes directly.
- Not annotating your own critical paths — first thing to add before optimizing is `trace("Feature:step") { }` in the code so the trace is self-explanatory.
