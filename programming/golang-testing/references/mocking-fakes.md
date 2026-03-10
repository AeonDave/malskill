# Mocking and fakes

## Prefer fakes for most tests

A fake is a small in-memory implementation of a dependency. It tends to be simpler and more robust than a mock.

Example: fake repository

```go
type UserRepo interface {
    Get(ctx context.Context, id string) (User, error)
    Save(ctx context.Context, u User) error
}

type FakeUserRepo struct {
    mu    sync.Mutex
    users map[string]User
}

func NewFakeUserRepo() *FakeUserRepo {
    return &FakeUserRepo{users: map[string]User{}}
}

func (r *FakeUserRepo) Get(ctx context.Context, id string) (User, error) {
    r.mu.Lock(); defer r.mu.Unlock()
    u, ok := r.users[id]
    if !ok { return User{}, ErrNotFound }
    return u, nil
}

func (r *FakeUserRepo) Save(ctx context.Context, u User) error {
    r.mu.Lock(); defer r.mu.Unlock()
    r.users[u.ID] = u
    return nil
}
```

## When mocks are appropriate

Use a mock when you need to assert:
- a call happened
- arguments were specific
- ordering matters

Even then, keep the mock tiny; prefer hand-written stubs over complex frameworks.

## Avoid hidden external dependencies

If an example requires a DB driver or cgo, call it out explicitly in the test docs (and keep unit tests independent from it).
