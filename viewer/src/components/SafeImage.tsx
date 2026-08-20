import { useState } from "react";

interface SafeImageProps {
  src: string | undefined;
  alt: string;
  /** e.g. "2 / 3" or "16 / 9" — reserves space to prevent layout shift. */
  aspectRatio: string;
  className?: string;
  /** Hero/above-the-fold images should NOT be lazy and should be preloaded. */
  priority?: boolean;
}

/**
 * Resilient artwork image:
 * - reserves aspect ratio so a slow/broken load never shifts layout
 * - shows a skeleton shimmer until the image loads
 * - falls back to a placeholder box on error, without breaking row layout
 * - lazy-loads by default; `priority` opts an image (e.g. the hero) out of that
 */
export function SafeImage({
  src,
  alt,
  aspectRatio,
  className,
  priority = false,
}: SafeImageProps) {
  const [status, setStatus] = useState<"loading" | "loaded" | "error">(
    src ? "loading" : "error"
  );

  return (
    <div
      className={`safe-image ${className ?? ""}`}
      style={{ aspectRatio }}
    >
      {status !== "loaded" && (
        <div className={`safe-image__placeholder ${status === "error" ? "safe-image__placeholder--error" : "safe-image__placeholder--loading"}`}>
          {status === "error" && <span className="safe-image__icon">🎬</span>}
        </div>
      )}
      {src && status !== "error" && (
        <img
          src={src}
          alt={alt}
          loading={priority ? "eager" : "lazy"}
          fetchPriority={priority ? "high" : "auto"}
          className={`safe-image__img ${status === "loaded" ? "safe-image__img--visible" : ""}`}
          onLoad={() => setStatus("loaded")}
          onError={() => setStatus("error")}
        />
      )}
    </div>
  );
}
