import React, { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";

export function useGsapContext(scope?: React.RefObject<Element | null>) {
  const ctx = useRef<gsap.Context | null>(null);

  useLayoutEffect(() => {
    ctx.current = gsap.context(() => {}, scope?.current ?? undefined);
    return () => {
      ctx.current?.revert();
    };
  }, [scope]);

  return ctx;
}

