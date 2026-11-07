# Test design

## Unit vs integration

- Unit: deterministic, isolated, no real filesystem/network/db
- Integration: real dependencies, slower, fewer, labeled

Keep integration boundaries explicit: filesystem/network/process tests should not be silently mixed into unit suites.

## Fixtures

Use fixtures when multiple tests share setup/teardown:

```cpp
class ParserTest : public ::testing::Test {
 protected:
  void SetUp() override { parser_ = std::make_unique<Parser>(config_); }
  // TearDown() only when RAII members are not enough
  Config config_{/* test defaults */};
  std::unique_ptr<Parser> parser_;
};

TEST_F(ParserTest, RejectsEmptyInput) {
  EXPECT_FALSE(parser_->parse(""));
}
```

Prefer minimal fixtures over heavy global setup.

## Parameterized tests

```cpp
struct ParseCase { std::string input; bool valid; };

class ParseValidity : public ::testing::TestWithParam<ParseCase> {};

TEST_P(ParseValidity, MatchesExpected) {
  const auto& p = GetParam();
  EXPECT_EQ(Parser{}.parse(p.input).has_value(), p.valid) << "input: " << p.input;
}

INSTANTIATE_TEST_SUITE_P(Basic, ParseValidity, ::testing::Values(
    ParseCase{"", false},
    ParseCase{"a=1", true},
    ParseCase{"@@", false}
));
```

Use descriptive parameter names (a `<< "input: " << ...` message or custom `NameGenerator`) to keep failure output debuggable.

## Value-parameterized matchers (quick reference)

- `EXPECT_EQ/NE/TRUE/FALSE` — plain comparisons
- `EXPECT_THAT(x, MatchesRegex("..."))` — gmock matchers, better failure output
- `EXPECT_THROW(stmt, ExType)` / `EXPECT_NO_THROW` — exception contracts
- `EXPECT_DEATH_IF_SUPPORTED(stmt, "msg")` — invariant-abort paths (needs death-test config)

## Mocks vs fakes

- Fake: simple in-memory implementation
- Mock (`gmock`): verifies interaction (calls, arguments)

```cpp
struct Clock { virtual ~Clock() = default; virtual int now() = 0; };

TEST(FooTest, UsesClock) {
  testing::StrictMock<MockClock> clock;
  EXPECT_CALL(clock, now()).WillOnce(testing::Return(42));
  ASSERT_EQ(42, subject.run(clock));
}
```

Avoid over-mocking value objects; prefer fakes for state, mocks for interaction.

## Structure guidance (AAA)

- **Arrange**: isolate state and dependencies.
- **Act**: execute one behavior under test.
- **Assert**: verify outcome with targeted expectations.

Prefer one dominant assertion intent per test case to improve triage speed.
