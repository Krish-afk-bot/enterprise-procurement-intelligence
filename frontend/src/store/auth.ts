import { create } from "zustand";
import { persist } from "zustand/middleware";

import { api, setAccessToken } from "@/lib/api";
import type { MeResponse } from "@/lib/types";

interface AuthState {
  token: string | null;
  user: MeResponse | null;
  status: "idle" | "loading" | "ready" | "error";
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  can: (permission: string) => boolean;
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      status: "idle",
      error: null,
      async login(email, password) {
        set({ status: "loading", error: null });
        try {
          const tokens = await api.login(email, password);
          const token = tokens.access_token;
          setAccessToken(token);
          const user = tokens.user ?? (await api.me());
          set({ token, user, status: "ready", error: null });
        } catch (error) {
          set({ status: "error", error: error instanceof Error ? error.message : "Sign-in failed" });
          throw error;
        }
      },
      async register(email, password, fullName) {
        set({ status: "loading", error: null });
        try {
          const tokens = await api.register(email, password, fullName);
          const token = tokens.access_token;
          setAccessToken(token);
          const user = tokens.user ?? (await api.me());
          set({ token, user, status: "ready", error: null });
        } catch (error) {
          set({ status: "error", error: error instanceof Error ? error.message : "Registration failed" });
          throw error;
        }
      },
      logout() {
        setAccessToken(null);
        set({ token: null, user: null, status: "idle", error: null });
      },
      async refreshUser() {
        const token = get().token;
        if (!token) return;
        setAccessToken(token);
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
    }),
    {
      name: "epi-auth",
      partialize: (state) => ({ token: state.token }),
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          setAccessToken(state.token);
        }
      },
    },
  ),
);
