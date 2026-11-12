import { describe, expect, it } from "vitest";

import { MIN_PASSWORD_LENGTH, hasErrors, validateCredentials } from "../validation";

describe("validateCredentials", () => {
  it("accepts a valid sign-in", () => {
    expect(validateCredentials({ mode: "signin", email: "buyer@epi.local", password: "x" })).toEqual({});
  });

  it("rejects an empty email and password", () => {
    const errors = validateCredentials({ mode: "signin", email: "  ", password: "" });
    expect(errors.email).toBeDefined();
    expect(errors.password).toBeDefined();
    expect(hasErrors(errors)).toBe(true);
  });

  it("rejects an address without a domain dot", () => {
    expect(validateCredentials({ mode: "signin", email: "buyer@epi", password: "x" }).email).toBeDefined();
  });

  it("rejects spaces inside the address", () => {
    expect(validateCredentials({ mode: "signin", email: "bu yer@epi.local", password: "x" }).email).toBeDefined();
  });

  it("does not impose a length rule when signing in", () => {
    expect(validateCredentials({ mode: "signin", email: "buyer@epi.local", password: "short" }).password).toBeUndefined();
  });

  it("requires a usable password when registering", () => {
    const short = validateCredentials({
      mode: "register",
      email: "buyer@epi.local",
      password: "1234567",
      fullName: "Jamie Chen",
    });
    expect(short.password).toContain(String(MIN_PASSWORD_LENGTH));

    const ok = validateCredentials({
      mode: "register",
      email: "buyer@epi.local",
      password: "a".repeat(MIN_PASSWORD_LENGTH),
      fullName: "Jamie Chen",
    });
    expect(ok).toEqual({});
  });

  it("requires a display name when registering", () => {
    const errors = validateCredentials({
      mode: "register",
      email: "buyer@epi.local",
      password: "a".repeat(MIN_PASSWORD_LENGTH),
      fullName: " ",
    });
    expect(errors.fullName).toBeDefined();
  });

  it("ignores the display name while signing in", () => {
    expect(validateCredentials({ mode: "signin", email: "buyer@epi.local", password: "x" })).toEqual({});
  });
});
