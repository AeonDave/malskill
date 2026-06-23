import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { classifyCommand } from "../src/policy.js";

describe("classifyCommand", () => {
  it("allows ordinary commands", () => {
    assert.deepEqual(classifyCommand("git status"), { kind: "allow" });
  });

  it("denies dangerous commands", () => {
    const result = classifyCommand("rm -rf dist");
    assert.equal(result.kind, "deny");
  });
});
