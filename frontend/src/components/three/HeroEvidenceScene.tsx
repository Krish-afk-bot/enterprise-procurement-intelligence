import type { ReactNode } from "react";

import { EvidenceFlowScene } from "@/components/three/EvidenceFlowScene";
import { SceneFrame } from "@/components/three/SceneFrame";

/**
 * Heavy entry point for the landing page hero: retrieved documents, one quoted
 * passage, one answer. Lazy so the marketing page stays cheap to load.
 */
export default function HeroEvidenceScene({ fallback }: { fallback: ReactNode }) {
  return (
    <SceneFrame
      title="From documents to a cited answer"
      caption="A schematic, not data: each document is retrieved on its own, the passage that supports the answer is quoted, and the answer is composed from it."
      ariaLabel="Schematic: a master contract, an amendment and a pricing schedule each connect to one cited passage, which connects to the answer. No figures are shown."
      fallback={fallback}
      height={300}
    >
      <EvidenceFlowScene />
    </SceneFrame>
  );
}
