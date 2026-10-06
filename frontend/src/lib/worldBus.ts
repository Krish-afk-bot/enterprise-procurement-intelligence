/**
 * The wiring between the band's DOM and the scenes that draw inside it.
 *
 * Nothing here is React state. These values are read inside `useFrame`, dozens
 * of times a second, and written either by the DOM (a click, a pointer move) or
 * by a scene (the courier's current position). Putting any of it in a store
 * would re-render the application for a decorative character, which is exactly
 * the kind of cost this layer exists to avoid.
 */

type Listener = () => void;

const listeners = new Set<Listener>();

function emit() {
  for (const listener of listeners) listener();
}

/** Used by the canvas to follow the interactive region with `useSyncExternalStore`. */
export function subscribeWorld(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/**
 * The one region whose scene should receive pointer events. The shared canvas
 * is drawn over the page, so events have to be read from a real DOM element
 * inside the region rather than from the canvas itself; this is the element the
 * canvas connects its listeners to.
 */
let interactiveElement: HTMLElement | null = null;

export function getInteractiveElement(): HTMLElement | null {
  return interactiveElement;
}

export function setInteractiveElement(element: HTMLElement | null): void {
  if (interactiveElement === element) return;
  interactiveElement = element;
  emit();
}

/** Where the courier currently is, published by its own frame loop. */
export const courierState = {
  x: 0,
  halfWidth: 30,
  visible: false,
  /** Incremented by a click in the band; the courier stops and tips its hat. */
  poke: 0,
  /** `performance.now()` until which the courier is reacting to a passing cursor. */
  stumbleUntil: 0,
};

/** Where the Watcher's head currently is, published by its own frame loop. */
export const watcherState = {
  x: 0,
  y: 0,
  radius: 34,
  visible: false,
};

export function pokeCourier(): void {
  courierState.poke += 1;
}

/** A cursor passing close to the courier makes it stumble, if it is walking. */
export function nudgeCourier(clientX: number, rect: DOMRect): void {
  const x = clientX - rect.left - rect.width / 2;
  if (Math.abs(x - courierState.x) < 34) {
    courierState.stumbleUntil = performance.now() + 600;
  }
}

/** Which character, if any, the click inside the band rect landed on. */
export function hitTestBand(clientX: number, clientY: number, rect: DOMRect): "watcher" | "courier" | null {
  const x = clientX - rect.left - rect.width / 2;
  const y = rect.top + rect.height / 2 - clientY;
  if (watcherState.visible && Math.hypot(x - watcherState.x, y - watcherState.y) <= watcherState.radius) {
    return "watcher";
  }
  if (courierState.visible && Math.abs(x - courierState.x) <= courierState.halfWidth && y < 60 && y > -60) {
    return "courier";
  }
  return null;
}
