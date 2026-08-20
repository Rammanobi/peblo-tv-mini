import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { deleteEpisode, deleteSeason, listEpisodes } from '../api/endpoints';
import { ApiError } from '../api/client';
import type { Season } from '../types/api';
import { QueryStateGate } from './DataState';

export default function SeasonEpisodesPanel({ season, showId }: { season: Season; showId: number }) {
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);

  const episodesQuery = useQuery({
    queryKey: ['episodes', season.id],
    queryFn: () => listEpisodes(season.id, { limit: 200 }),
  });

  const deleteSeasonMutation = useMutation({
    mutationFn: () => deleteSeason(season.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['seasons', String(showId)] });
    },
    onError: (err) => {
      setActionError(
        err instanceof ApiError ? err.message : 'Could not delete this season. Please try again.'
      );
    },
  });

  const deleteEpisodeMutation = useMutation({
    mutationFn: (episodeId: number) => deleteEpisode(episodeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['episodes', season.id] });
    },
    onError: (err) => {
      setActionError(
        err instanceof ApiError ? err.message : 'Could not delete this episode. Please try again.'
      );
    },
  });

  const episodeCount = episodesQuery.data?.items.length ?? 0;

  const handleDeleteSeason = () => {
    setActionError(null);
    const label = season.is_trailer_season ? 'trailers (season 0)' : `season ${season.season_number}`;
    // The API refuses to delete a season that still holds published episodes
    // (a safety guard against silently orphaning live content) — it does not
    // cascade-delete them, so the confirmation must not imply that it will.
    const warning =
      episodeCount > 0
        ? `Delete ${label}? It still has ${episodeCount} episode(s) — delete or unpublish those first if this is blocked. This cannot be undone.`
        : `Delete ${label}? This cannot be undone.`;
    if (window.confirm(warning)) {
      deleteSeasonMutation.mutate();
    }
  };

  const handleDeleteEpisode = (episodeId: number, title: string) => {
    setActionError(null);
    if (window.confirm(`Delete episode "${title}"? This cannot be undone.`)) {
      deleteEpisodeMutation.mutate(episodeId);
    }
  };

  return (
    <div className="season-card">
      <div className="season-card-header">
        <strong>
          {season.is_trailer_season ? 'Trailers (season 0)' : season.title || `Season ${season.season_number}`}
        </strong>
        <div className="season-card-actions">
          <Link
            className="btn btn-secondary btn-sm"
            to={`/shows/${showId}/seasons/${season.id}/episodes/new`}
          >
            + {season.is_trailer_season ? 'Add trailer' : 'Add episode'}
          </Link>
          <button
            className="btn btn-danger btn-sm"
            type="button"
            onClick={handleDeleteSeason}
            disabled={deleteSeasonMutation.isPending}
            title={
              season.is_trailer_season
                ? 'Delete trailers season'
                : `Delete season ${season.season_number}`
            }
          >
            {deleteSeasonMutation.isPending ? 'Deleting…' : 'Delete season'}
          </button>
        </div>
      </div>

      {actionError && (
        <div className="form-server-error" role="alert">
          {actionError}
        </div>
      )}

      <QueryStateGate
        isLoading={episodesQuery.isLoading}
        error={episodesQuery.error}
        isEmpty={!episodesQuery.isLoading && !episodesQuery.error && episodeCount === 0}
        emptyTitle="No episodes yet"
        onRetry={() => episodesQuery.refetch()}
      >
        <div className="table-scroll">
          <table className="data-table data-table-compact">
            <thead>
              <tr>
                <th>#</th>
                <th>Title</th>
                <th>Language</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Artwork</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {episodesQuery.data?.items.map((ep) => (
                <tr key={ep.id}>
                  <td>{ep.episode_number ?? '—'}</td>
                  <td>
                    <Link to={`/episodes/${ep.id}`}>{ep.title}</Link>
                  </td>
                  <td>{ep.language}</td>
                  <td>
                    <span className={`status-pill status-${ep.status}`}>{ep.status}</span>
                  </td>
                  <td>{ep.duration_seconds ? `${ep.duration_seconds}s` : '—'}</td>
                  <td>
                    {ep.missing_artwork_kinds.length > 0 ? (
                      <span className="warning-pill">missing: {ep.missing_artwork_kinds.join(', ')}</span>
                    ) : (
                      <span className="ok-pill">complete</span>
                    )}
                  </td>
                  <td>
                    <button
                      className="btn btn-danger btn-sm"
                      type="button"
                      onClick={() => handleDeleteEpisode(ep.id, ep.title)}
                      disabled={deleteEpisodeMutation.isPending}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </QueryStateGate>
    </div>
  );
}
