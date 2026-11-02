/**
 * Build-time feature flags.
 *
 * The 3D world is opt-in: `VITE_ENABLE_WORLD=true` at build time mounts the
 * persistent band, and anything else (including an unset variable) leaves the
 * application with its ordinary DOM layout. Keeping the flag a plain constant
 * lets Vite drop the disabled branch and keeps the choice out of runtime state.
 */
export const WORLD_ENABLED = import.meta.env.VITE_ENABLE_WORLD === "true";
