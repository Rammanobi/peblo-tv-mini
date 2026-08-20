import React, { useEffect, useRef, useState } from 'react';
import { artworkSpecByKind, reference } from '../lib/reference';
import { ApiError } from '../api/client';
import type { Artwork, ArtworkKind } from '../types/api';

interface Props {
  kind: ArtworkKind;
  existing?: Artwork;
  onUpload: (file: File) => Promise<Artwork>;
  disabled?: boolean;
}

interface PreCheck {
  ok: boolean;
  messages: string[];
}

function checkFileClientSide(file: File, spec: (typeof artworkSpecByKind)[string]): Promise<PreCheck> {
  return new Promise((resolve) => {
    const messages: string[] = [];

    if (!reference.artwork.allowed_mime_types.includes(file.type)) {
      messages.push(`File type "${file.type || 'unknown'}" is not jpeg/png/webp.`);
    }
    if (file.size > reference.artwork.max_file_size_bytes) {
      messages.push(
        `File is ${(file.size / 1024).toFixed(0)} KB, over the ${reference.artwork.max_file_size_human} limit.`
      );
    }

    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const ratio = img.width / img.height;
      const tolerance = reference.artwork.aspect_ratio_tolerance;
      const expected = spec.aspect_ratio_value;
      if (Math.abs(ratio - expected) / expected > tolerance) {
        messages.push(
          `Image is ${img.width}x${img.height} (about ${(img.width / img.height).toFixed(2)}:1). Expected close to ${spec.width}x${spec.height} (${spec.aspect_ratio}).`
        );
      }
      URL.revokeObjectURL(url);
      resolve({ ok: messages.length === 0, messages });
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      messages.push('Could not read image dimensions in the browser.');
      resolve({ ok: false, messages });
    };
    img.src = url;
  });
}

export default function ArtworkSlot({ kind, existing, onUpload, disabled }: Props) {
  const spec = artworkSpecByKind[kind];
  const [preview, setPreview] = useState<string | null>(existing?.url ?? null);
  const [preCheck, setPreCheck] = useState<PreCheck | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const objectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    setPreview(existing?.url ?? null);
  }, [existing?.url]);

  useEffect(
    () => () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    },
    []
  );

  const handleFile = async (file: File | null) => {
    if (!file) return;
    setServerError(null);

    // Instant client-side preview.
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    const localUrl = URL.createObjectURL(file);
    objectUrlRef.current = localUrl;
    setPreview(localUrl);

    // Fast, non-authoritative pre-check for immediate feedback only.
    const result = await checkFileClientSide(file, spec);
    setPreCheck(result);

    // The real server call always happens regardless of the pre-check result.
    setUploading(true);
    try {
      const artwork = await onUpload(file);
      setPreview(artwork.url);
      setServerError(null);
    } catch (err) {
      if (err instanceof ApiError) {
        setServerError(err.message + (err.details[0]?.message ? ` ${err.details[0].message}` : ''));
      } else {
        setServerError('Upload failed. Please try again.');
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="artwork-slot">
      <div className="artwork-slot-header">
        <strong>{kind[0].toUpperCase() + kind.slice(1)}</strong>
        <span className="muted">
          {spec.width}x{spec.height} ({spec.aspect_ratio}), &le; {reference.artwork.max_file_size_human}
        </span>
      </div>

      <div className="artwork-preview" data-kind={kind}>
        {preview ? (
          <img src={preview} alt={`${kind} preview`} />
        ) : (
          <div className="artwork-preview-empty">No image yet</div>
        )}
      </div>

      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        disabled={disabled || uploading}
        onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
      />

      {uploading && <p className="muted">Uploading...</p>}

      {preCheck && !preCheck.ok && (
        <ul className="precheck-warning">
          {preCheck.messages.map((m, i) => (
            <li key={i}>Heads up: {m}</li>
          ))}
        </ul>
      )}

      {serverError && (
        <p className="field-error" role="alert">
          {serverError}
        </p>
      )}
    </div>
  );
}
