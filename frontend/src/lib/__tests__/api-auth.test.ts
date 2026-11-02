/**
 * Unit tests for the API client's session handling.
 *
 * The access token is memory-only, so the client must recover from an expired
 * token by rotating the httpOnly refresh cookie and replaying the request once.
 * A failed refresh must sign the user out instead of looping.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, refreshAccessToken, setAccessToken, setAuthFailureHandler } from "../api";

const ME = {
  user_id: "usr_1",
  tenant_id: "ten_1",
  email: "admin@test.local",
  role: "admin",
  full_name: "Admin",
  permissions: ["admin:read"],
  access_ceiling: "internal",
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function tokenResponse(accessToken: string) {
  return { access_token: accessToken, token_type: "bearer", expires_at: "2030-01-01T00:00:00Z", user: ME };
}

describe("api session handling", () => {
  let calls: { url: string; init?: RequestInit }[];

  beforeEach(() => {
    calls = [];
    setAccessToken(null);
    setAuthFailureHandler(null);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    setAccessToken(null);
    setAuthFailureHandler(null);
  });

  it("refreshes once on 401 and replays the request with the new token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        calls.push({ url, init });
        if (url.endsWith("/auth/refresh")) return jsonResponse(200, tokenResponse("fresh"));
        const auth = new Headers(init?.headers).get("authorization");
        return auth === "Bearer fresh" ? jsonResponse(200, ME) : jsonResponse(401, { detail: "expired" });
      }),
    );
    setAccessToken("stale");

    const me = await api.me();

    expect(me.user_id).toBe("usr_1");
    expect(calls.map((call) => call.url)).toEqual([
      expect.stringContaining("/auth/me"),
      expect.stringContaining("/auth/refresh"),
      expect.stringContaining("/auth/me"),
    ]);
    // Every call — including the refresh and the retry — must send cookies.
    for (const call of calls) expect(call.init?.credentials).toBe("include");
  });

  it("reports a session failure when the refresh is rejected", async () => {
    const onFailure = vi.fn();
    setAuthFailureHandler(onFailure);
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(401, { detail: "expired" })));
    setAccessToken("stale");

    await expect(api.me()).rejects.toBeInstanceOf(ApiError);
    expect(onFailure).toHaveBeenCalledTimes(1);
  });

  it("returns null and does not recurse when the refresh endpoint itself fails", async () => {
    const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(
      async () => jsonResponse(401, { detail: "nope" }),
    );
    vi.stubGlobal("fetch", fetchMock);

    expect(await refreshAccessToken()).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain("/auth/refresh");
  });

  it("rotates the refresh cookie only once for concurrent 401s", async () => {
    let refreshCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/auth/refresh")) {
          refreshCalls += 1;
          // Hold the rotation open so the second 401 arrives while it is in flight.
          await new Promise((resolve) => setTimeout(resolve, 0));
          return jsonResponse(200, tokenResponse("fresh"));
        }
        const auth = new Headers(init?.headers).get("authorization");
        return auth === "Bearer fresh" ? jsonResponse(200, ME) : jsonResponse(401, { detail: "expired" });
      }),
    );
    setAccessToken("stale");

    await Promise.all([api.me(), api.me()]);

    expect(refreshCalls).toBe(1);
  });
});
