/**
 * Where the reader's attention is.
 *
 * This is deliberately NOT React state. A cursor moving across the page fires
 * hundreds of events a second; putting that in a store would re-render the
 * application hundreds of times a second for a decorative character. Instead the
 * values are written here and read inside `useFrame`, so React never re-renders
 * because of the pointer.
 *
 * Everything is normalised to -1..1 across the viewport, with (0, 0) at the centre.
 */

interface PointerSnapshot {
  /** Normalised cursor position, -1..1, or null when the pointer has never moved. */
  x: number;
  y: number;
  known: boolean;
  /** `performance.now()` of the last real pointer movement. */
  lastMove: number;
  /** True on a touch device, where there is no hover cursor. */
  touch: boolean;
}

const snapshot: PointerSnapshot = { x: 0, y: 0, known: false, lastMove: 0, touch: false };

/** Set when the reader prefers reduced motion; the world then ignores the cursor. */
let trackingEnabled = true;

export function setPointerTracking(enabled: boolean) {
  trackingEnabled = enabled;
}

export function readPointer(): Readonly<PointerSnapshot> {
  return snapshot;
}

/**
 * Seconds since the reader last moved the pointer.
 *
 * A pointer that has never moved is not an idle reader: nobody has been still
 * "since" anything yet. Reporting infinity here would put the character to
 * sleep on the first frame of a session — including for anyone who navigates
 * by keyboard and never touches the mouse — so the clock only starts once there
 * has been a movement to be idle after.
 */
export function pointerIdleSeconds(now: number): number {
  if (!snapshot.known) return 0;
  return (now - snapshot.lastMove) / 1000;
}

/** True when the pointer is in the top-left corner and has never really moved. */
export function hasPointer(): boolean {
  return snapshot.known;
}

function record(clientX: number, clientY: number) {
  if (!trackingEnabled) return;
  const width = window.innerWidth || 1;
  const height = window.innerHeight || 1;
  snapshot.x = (clientX / width) * 2 - 1;
  snapshot.y = -((clientY / height) * 2 - 1);
  snapshot.known = true;
  snapshot.lastMove = performance.now();
}

let installed = false;

/** Installs the listeners once for the whole application. */
export function installPointerTracking() {
  if (installed || typeof window === "undefined") return () => {};
  installed = true;

  const onPointerMove = (event: PointerEvent) => {
    if (event.pointerType === "touch") snapshot.touch = true;
    record(event.clientX, event.clientY);
  };
  const onTouch = (event: TouchEvent) => {
    snapshot.touch = true;
    const touch = event.touches[0];
    if (touch) record(touch.clientX, touch.clientY);
  };
  // Touch devices have no cursor, so the world follows the scroll position
  // instead: a slow drift, not a tracker.
  const onScroll = () => {
    if (!snapshot.touch) return;
    const scrolled = window.scrollY / Math.max(document.body.scrollHeight - window.innerHeight, 1);
    snapshot.y = 0.5 - scrolled;
    snapshot.lastMove = performance.now();
  };

  window.addEventListener("pointermove", onPointerMove, { passive: true });
  window.addEventListener("touchstart", onTouch, { passive: true });
  window.addEventListener("touchmove", onTouch, { passive: true });
  window.addEventListener("scroll", onScroll, { passive: true });

  return () => {
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("touchstart", onTouch);
    window.removeEventListener("touchmove", onTouch);
    window.removeEventListener("scroll", onScroll);
    installed = false;
  };
}

/**
 * Keyboard focus, so the character can look at the control being tabbed to. Only
 * the element's centre is recorded; nothing is read from or written to the element.
 */
interface FocusSnapshot {
  x: number;
  y: number;
  known: boolean;
  at: number;
}

const focusSnapshot: FocusSnapshot = { x: 0, y: 0, known: false, at: 0 };

export function readFocus(): Readonly<FocusSnapshot> {
  return focusSnapshot;
}

export function installFocusTracking() {
  if (typeof window === "undefined") return () => {};
  const onFocusIn = (event: FocusEvent) => {
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.getBoundingClientRect !== "function") return;
    const rect = target.getBoundingClientRect();
    // Elements larger than the viewport (a main region, the body) are not useful
    // targets to look at, and reading them would just aim the face at the centre.
    if (rect.width > window.innerWidth * 0.9 || rect.height > window.innerHeight * 0.9) return;
    focusSnapshot.x = ((rect.left + rect.width / 2) / (window.innerWidth || 1)) * 2 - 1;
    focusSnapshot.y = -(((rect.top + rect.height / 2) / (window.innerHeight || 1)) * 2 - 1);
    focusSnapshot.known = true;
    focusSnapshot.at = performance.now();
  };
  window.addEventListener("focusin", onFocusIn, { passive: true });
  return () => window.removeEventListener("focusin", onFocusIn);
}

/** True while a keyboard focus move should still be the thing being looked at. */
export function focusIsRecent(now: number, windowMs = 2600): boolean {
  return focusSnapshot.known && now - focusSnapshot.at < windowMs;
}
