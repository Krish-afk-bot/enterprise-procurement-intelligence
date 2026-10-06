/**
 * Every word of personality in the product lives here.
 *
 * Rules this file follows, and why they are rules:
 *   - One joke per state, maximum. The tone is deadpan and self-aware, never silly.
 *   - A joke may follow a clear explanation and must never replace it. Every entry
 *     therefore carries the plain sentence it decorates, and callers render both.
 *   - Nothing here changes a fact. No line states a figure, a ranking, a saving, a
 *     winner or a verification outcome; those come from the API and from nowhere else.
 *   - Errors, permissions, authentication, administration, security, privacy and
 *     terms stay plain. Humour is not applied to a failure a person has to act on.
 *   - No emoji, no copyrighted meme text, no reference to real people, customers or
 *     suppliers.
 *
 * The four lines fixed by the product brief are marked `fixed`.
 */

/** Which real application state the world should express. */
export type WorldMood = "idle" | "loading" | "found" | "conflict" | "unsupported" | "empty" | "error";

interface Line {
  /** The line as shown. */
  say: string;
  /** The plain sentence it decorates, shown beside or beneath it. */
  plain: string;
}

export const MICROCOPY = {
  // ------------------------------------------------------------------ loading
  /** fixed */
  loading: {
    say: "Digging through the paperwork…",
    plain: "Searching the indexed passages and checking them against the question.",
  },
  loadingCabinet: {
    say: "Asking the filing cabinet nicely…",
    plain: "Retrieval is running over the indexed documents.",
  },
  loadingScene: {
    say: "Building the view…",
    plain: "Loading the 3D scene. The written version is already available.",
  },

  // -------------------------------------------------------------------- found
  /** fixed */
  found: {
    say: "Yep. Found it.",
    plain: "The answer is supported by the cited passages.",
  },
  foundPage: {
    say: "Page 14. It was hiding.",
    plain: "The supporting passage was found on the cited page.",
  },

  // ----------------------------------------------------------------- conflict
  /** fixed */
  conflict: {
    say: "Uh… these documents disagree.",
    plain: "The answer states which record governs instead of averaging the values.",
  },

  // -------------------------------------------------------------- unsupported
  /** fixed */
  unsupported: {
    say: "I checked the available documents. They don't actually say.",
    plain: "No verified evidence was found for this question, so no answer is given.",
  },

  // -------------------------------------------------------------------- empty
  /** fixed */
  emptySearch: {
    say: "Nothing here. The documents are innocent.",
    plain: "No indexed passage matched this search with the current filters.",
  },
  noDocuments: {
    say: "The shelf is empty.",
    plain: "No document has been uploaded to this workspace yet.",
  },
  singleVersion: {
    say: "One version so far. Nothing to stack yet.",
    plain: "No newer version of this document has been uploaded.",
  },

  // ------------------------------------------------------------------ compare
  /** fixed */
  needTwo: {
    say: "Pick at least two suppliers and we'll compare them.",
    plain: "A comparison needs two records before it can show a difference.",
  },

  // --------------------------------------------------------------------- idle
  idle: {
    say: "Still here. Still watching. Mostly the cursor.",
    plain: "This is a decorative character and is not needed to use the workspace.",
  },
  idleTwo: {
    say: "No documents were harmed in the making of this workspace.",
    plain: "Every document is stored as uploaded and cited from its own pages.",
  },

  // ------------------------------------------------------------ 3D characters
  buddyHidden: {
    say: "Fine. I'll be over here.",
    plain: "The decorative characters are hidden. You can bring them back in the header.",
  },
  courierBusy: {
    say: "Delivering a folder. Back shortly.",
    plain: "The courier is a decorative character; nothing is actually being transferred.",
  },
  effectsReduced: {
    say: "Quiet mode. Less to look at.",
    plain: "Motion and effects are reduced across the workspace.",
  },

  // -------------------------------------------------------------------- index
  indexed: {
    say: "Read, indexed and ready.",
    plain: "The document finished processing and its passages are searchable.",
  },

  // ------------------------------------------------------------------ process
  processing: {
    say: "The pipeline is chewing on this one.",
    plain: "Ingestion is still running for this document.",
  },
} as const satisfies Record<string, Line>;

export type MicrocopyKey = keyof typeof MICROCOPY;

/** The line itself. */
export function say(key: MicrocopyKey): string {
  return MICROCOPY[key].say;
}

/** The plain statement the line decorates; never optional when the line is shown. */
export function plain(key: MicrocopyKey): string {
  return MICROCOPY[key].plain;
}

/** A stable pick from a set, so a repeated state does not flicker between lines. */
export function pick<T>(list: readonly T[], seed: number): T {
  return list[Math.abs(Math.round(seed)) % list.length];
}

/** Rotating lines the Watcher shows when it is clicked. Each is one short sentence. */
export const WATCHER_CLICKS: readonly MicrocopyKey[] = ["idle", "idleTwo", "loadingCabinet"];
