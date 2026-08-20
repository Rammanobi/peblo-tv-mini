import React from 'react';
import { ApiError } from '../api/client';

export function LoadingState({ label = 'Loading...' }: { label?: string }) {
  return (
    <div className="state state-loading" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="state state-empty">
      <p className="state-title">{title}</p>
      {hint && <p className="state-hint">{hint}</p>}
    </div>
  );
}

export function PermissionDeniedState({ message }: { message?: string }) {
  return (
    <div className="state state-forbidden" role="alert">
      <p className="state-title">Permission denied</p>
      <p className="state-hint">
        {message || 'Your account does not have access to this. Ask an admin if you believe this is a mistake.'}
      </p>
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof ApiError ? error.message : error instanceof Error ? error.message : 'Something went wrong.';
  const requestId = error instanceof ApiError ? error.requestId : null;
  return (
    <div className="state state-error" role="alert">
      <p className="state-title">Something went wrong</p>
      <p className="state-hint">{message}</p>
      {requestId && <p className="state-request-id">request_id: {requestId}</p>}
      {onRetry && (
        <button type="button" className="btn btn-secondary" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

/**
 * Central place to translate a fetch error into loading/empty/error/permission-denied.
 * Call this from any query-consuming view: `<QueryStateGate ... />`.
 */
export function QueryStateGate({
  isLoading,
  error,
  isEmpty,
  emptyTitle,
  emptyHint,
  onRetry,
  children,
}: {
  isLoading: boolean;
  error: unknown;
  isEmpty?: boolean;
  emptyTitle?: string;
  emptyHint?: string;
  onRetry?: () => void;
  children: React.ReactNode;
}) {
  if (isLoading) return <LoadingState />;
  if (error) {
    if (error instanceof ApiError && error.kind === 'forbidden') {
      return <PermissionDeniedState message={error.message} />;
    }
    if (error instanceof ApiError && error.kind === 'unauthorized') {
      return <PermissionDeniedState message="Your session has expired. Please log in again." />;
    }
    return <ErrorState error={error} onRetry={onRetry} />;
  }
  if (isEmpty) {
    return <EmptyState title={emptyTitle ?? 'Nothing here yet'} hint={emptyHint} />;
  }
  return <>{children}</>;
}
