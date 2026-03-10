# Unit tests: TDD, table-driven, subtests

## TDD (red → green → refactor)

- Write a failing test for one behavior
- Implement the smallest change to pass
- Refactor with tests staying green

## Table-driven tests

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name string
        a, b int
        want int
    }{
        {"pos", 2, 3, 5},
        {"neg", -1, -2, -3},
        {"zero", 0, 0, 0},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Add(tt.a, tt.b)
            if got != tt.want {
                t.Fatalf("Add(%d,%d)=%d; want %d", tt.a, tt.b, got, tt.want)
            }
        })
    }
}
```

### Error cases

Prefer explicit `wantErr` and validate the error shape.

```go
if tt.wantErr {
    if err == nil { t.Fatalf("expected error") }
    return
}
if err != nil { t.Fatalf("unexpected error: %v", err) }
```

## Subtests and parallel subtests

Use `t.Parallel()` only when tests are isolated and do not share state.

```go
for _, tt := range tests {
    tt := tt
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        // ...
    })
}
```

Tip: any shared global (env vars, temp dirs, time, net ports) can break parallelism.
