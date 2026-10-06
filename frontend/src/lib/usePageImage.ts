import { useEffect, useState } from "react";

import { ApiError, api, getAccessToken } from "@/lib/api";

export interface PageImageState {
  url: string | null;
  error: unknown;
  loading: boolean;
}

/**
 * Rendered page images are served behind the same authorization as every other
 * document route, so the bytes are fetched with the bearer token and exposed as
 * an object URL. A plain <img src> would be rejected with 401.
 */
export function usePageImage(documentId: string, page: number): PageImageState {
  const [state, setState] = useState<PageImageState>({ url: null, error: null, loading: false });

  useEffect(() => {
    if (!documentId || !page) {
      setState({ url: null, error: null, loading: false });
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    setState({ url: null, error: null, loading: true });

    const token = getAccessToken();
    fetch(api.pageImageUrl(documentId, page), {
      headers: token ? { authorization: `Bearer ${token}` } : undefined,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new ApiError(
            response.status === 404 ? "No rendered image is stored for this page." : "The page image could not be loaded.",
            response.status,
            null,
          );
        }
        const blob = await response.blob();
        objectUrl = URL.createObjectURL(blob);
        if (!cancelled) setState({ url: objectUrl, error: null, loading: false });
      })
      .catch((error: unknown) => {
        if (!cancelled) setState({ url: null, error, loading: false });
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, page]);

  return state;
}
