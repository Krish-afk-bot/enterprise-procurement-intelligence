import { create } from "zustand";

import { api, refreshAccessToken, setAccessToken, setAuthFailureHandler } from "@/lib/api";
import type { MeResponse } from "@/lib/types";

interface AuthState {
  token: string | null;
  user: MeResponse | null;
  status: "idle" | "loading" | "ready" | "error";
  error: string | null;
  /** True once the one-off silent-refresh attempt on page load has settled. */
  bootstrapped: boolean;
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  can: (permission: string) => boolean;
}

/**
 * Auth state.
 *
 * Nothing here is persisted. The access token lives in memory only, so a page
 * reload starts signed out and {@link AuthState.bootstrap} rebuilds the session
 * from the httpOnly refresh cookie. That keeps the token out of reach of any
 * script that manages to run on the page.
 */
export const useAuth = create<AuthState>()((set, get) => ({
  token: null,
  user: null,
  status: "idle",
  error: null,
  bootstrapped: false,

  async bootstrap() {
    if (get().bootstrapped) return;
    // There is no in-memory token after a reload; the refresh cookie is the
    // only durable credential, so ask the API to rotate it into a fresh one.
    const tokens = await refreshAccessToken();
    if (tokens?.access_token) {
      set({ token: tokens.access_token, user: tokens.user ?? get().user, status: "ready", error: null });
      if (!tokens.user) await get().refreshUser();
    }
    set({ bootstrapped: true });
  },

  async login(email, password) {
    set({ status: "loading", error: null });
    try {
      const tokens = await api.login(email, password);
      setAccessToken(tokens.access_token);
      const user = tokens.user ?? (await api.me());
      set({ token: tokens.access_token, user, status: "ready", error: null });
    } catch (error) {
      set({ status: "error", error: error instanceof Error ? error.message : "Sign-in failed" });
      throw error;
    }
  },

  async register(email, password, fullName) {
    set({ status: "loading", error: null });
    try {
      const tokens = await api.register(email, password, fullName);
      setAccessToken(tokens.access_token);
      const user = tokens.user ?? (await api.me());
      set({ token: tokens.access_token, user, status: "ready", error: null });
    } catch (error) {
      set({ status: "error", error: error instanceof Error ? error.message : "Registration failed" });
      throw error;
    }
  },

  logout() {
    // The refresh cookie is httpOnly, so only the server can clear it. Fire the
    // call and drop the local session immediately; the UI must not wait on it.
    void api.logout().catch(() => undefined);
    setAccessToken(null);
    set({ token: null, user: null, status: "idle", error: null });
  },

  async refreshUser() {
    try {
      const user = await api.me();
      set({ user, status: "ready", error: null });
    } catch (error) {
      setAccessToken(null);
      set({
        token: null,
        user: null,
        status: "error",
        error: error instanceof Error ? error.message : "Session expired",
      });
    }
  },

  can(permission) {
    return get().user?.permissions?.includes(permission) ?? false;
  },
}));

// When a refresh attempt fails the session cannot be recovered, so the API
// client tells us to drop the signed-in user and let the UI return to sign-in.
setAuthFailureHandler(() => {
  setAccessToken(null);
  useAuth.setState({
    token: null,
    user: null,
    status: "idle",
    error: "Your session expired. Please sign in again.",
  });
});
