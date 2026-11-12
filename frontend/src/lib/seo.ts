import { useEffect } from "react";

/**
 * Per-route document metadata.
 *
 * This is a single-page app, so the served HTML carries the landing metadata and
 * each public route replaces the title, description and social tags on mount.
 * Tags are updated in place rather than appended, so navigating between public
 * pages never stacks duplicates. Canonical URLs are deliberately not written:
 * the deployment origin is a runtime property of the operator, not of the build.
 */
type Seo = {
  title: string;
  description: string;
  noindex?: boolean;
};

function setMeta(attribute: "name" | "property", key: string, content: string) {
  let node = document.head.querySelector<HTMLMetaElement>(`meta[${attribute}="${key}"]`);
  if (!node) {
    node = document.createElement("meta");
    node.setAttribute(attribute, key);
    document.head.appendChild(node);
  }
  node.setAttribute("content", content);
}

export function useSeo({ title, description, noindex = false }: Seo) {
  useEffect(() => {
    document.title = title;
    setMeta("name", "description", description);
    setMeta("property", "og:title", title);
    setMeta("property", "og:description", description);
    setMeta("name", "twitter:title", title);
    setMeta("name", "twitter:description", description);
    setMeta("name", "robots", noindex ? "noindex, nofollow" : "index, follow");
  }, [title, description, noindex]);
}
