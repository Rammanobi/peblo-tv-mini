import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getPublishRuns, getValidationReport, publishCatalog } from '../api/endpoints';
import { useAuth } from '../lib/AuthContext';
import { QueryStateGate, PermissionDeniedState } from '../components/DataState';
import { ApiError } from '../api/client';

export default function PublishPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [publishError, setPublishError] = useState<string | null>(null);
  const [note, setNote] = useState('');

  const reportQuery = useQuery({
    queryKey: ['validation-report'],
    queryFn: () => getValidationReport(),
  });

  const runsQuery = useQuery({
    queryKey: ['publish-runs'],
    queryFn: () => getPublishRuns(),
  });

  const publishMutation = useMutation({
    mutationFn: () => publishCatalog({ note: note || undefined }),
    onSuccess: () => {
      setPublishError(null);
      queryClient.invalidateQueries({ queryKey: ['publish-runs'] });
      queryClient.invalidateQueries({ queryKey: ['validation-report'] });
    },
    onError: (err) => {
      setPublishError(err instanceof ApiError ? err.message : 'Publish failed. Please try again.');
    },
  });

  const isAdmin = user?.role === 'admin';

  return (
    <div>
      <div className="page-header">
        <h1>Publish</h1>
      </div>

      <section className="panel">
        <h2>Validation report</h2>
        <QueryStateGate
          isLoading={reportQuery.isLoading}
          error={reportQuery.error}
          onRetry={() => reportQuery.refetch()}
        >
          {reportQuery.data && (
            <>
              {reportQuery.data.publishable ? (
                <div className="ok-banner">
                  Catalogue is clean — {reportQuery.data.summary.shows_total} shows checked, no
                  blocking issues.
                </div>
              ) : (
                <div className="warning-banner">
                  {reportQuery.data.summary.blocking_issues} blocking issue(s) across{' '}
                  {reportQuery.data.summary.shows_affected} show(s) must be fixed before publishing.
                </div>
              )}

              {Object.keys(reportQuery.data.summary.by_type).length > 0 && (
                <div className="table-scroll">
                  <table className="data-table data-table-compact">
                    <thead>
                      <tr>
                        <th>Issue type</th>
                        <th>Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(reportQuery.data.summary.by_type).map(([code, count]) => (
                        <tr key={code}>
                          <td>{code}</td>
                          <td>{count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {reportQuery.data.by_show.map((entry) => (
                <div key={entry.show.id} className="issue-group">
                  <h3>
                    {entry.show.title} <span className="muted">({entry.show.status})</span>
                  </h3>
                  <ul>
                    {entry.issues.map((issue, i) => (
                      <li key={i} className={`issue issue-${issue.severity}`}>
                        <strong>{issue.code}</strong>: {issue.message}
                        {issue.hint && <div className="muted">Hint: {issue.hint}</div>}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </>
          )}
        </QueryStateGate>
      </section>

      <section className="panel">
        <h2>Publish catalogue</h2>
        {!isAdmin ? (
          <PermissionDeniedState message="Publishing the catalogue requires an admin account. Ask an admin to run the publish." />
        ) : (
          <>
            <label htmlFor="publish-note">Note (optional)</label>
            <input
              id="publish-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Aug launch batch"
            />

            {reportQuery.data && !reportQuery.data.publishable && (
              <div className="warning-banner">
                Publish is disabled: {reportQuery.data.summary.blocking_issues} blocking issue(s) must
                be resolved first. See the list above for exact rows and fixes.
              </div>
            )}

            <button
              className="btn btn-primary"
              type="button"
              disabled={
                !reportQuery.data ||
                !reportQuery.data.publishable ||
                publishMutation.isPending ||
                reportQuery.isLoading
              }
              onClick={() => {
                setPublishError(null);
                publishMutation.mutate();
              }}
            >
              {publishMutation.isPending ? 'Publishing...' : 'Publish catalogue'}
            </button>

            {publishError && (
              <div className="form-server-error" role="alert">
                {publishError}
              </div>
            )}

            {publishMutation.isSuccess && (
              <div className="ok-banner">Publish succeeded. See run history below.</div>
            )}
          </>
        )}
      </section>

      <section className="panel">
        <h2>Run history</h2>
        <QueryStateGate
          isLoading={runsQuery.isLoading}
          error={runsQuery.error}
          isEmpty={!runsQuery.isLoading && !runsQuery.error && (runsQuery.data?.items.length ?? 0) === 0}
          emptyTitle="No publish runs yet"
          onRetry={() => runsQuery.refetch()}
        >
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Status</th>
                  <th>Version</th>
                  <th>Published at</th>
                  <th>By</th>
                  <th>Warnings</th>
                </tr>
              </thead>
              <tbody>
                {runsQuery.data?.items.map((run) => (
                  <tr key={run.run_id}>
                    <td title={run.run_id}>{run.run_id}</td>
                    <td>
                      <span className={`status-pill status-${run.status}`}>{run.status}</span>
                    </td>
                    <td>{run.version ?? '—'}</td>
                    <td>{run.published_at ? new Date(run.published_at).toLocaleString() : '—'}</td>
                    <td>{run.published_by?.email ?? '—'}</td>
                    <td>{run.warning_count ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </QueryStateGate>
      </section>
    </div>
  );
}
