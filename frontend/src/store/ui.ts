import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UiState {
  sidebarCollapsed: boolean;
  includeSynthetic: boolean;
  toggleSidebar: () => void;
  setIncludeSynthetic: (value: boolean) => void;
}

export const useUi = create<UiState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      includeSynthetic: true,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setIncludeSynthetic: (value) => set({ includeSynthetic: value }),
    }),
    { name: "epi-ui" },
  ),
);
