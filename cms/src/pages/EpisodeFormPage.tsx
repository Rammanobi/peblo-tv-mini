import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createEpisode,
  getEpisode,
  getShow,
  listSeasons,
  updateEpisode,
  uploadEpisodeArtwork,
} from '../api/endpoints';
import { reference } from '../lib/reference';
import { ApiError } from '../api/client';
import { QueryStateGate } from '../components/DataState';
import ArtworkSlot from '../components/ArtworkSlot';
import type { Episode } from '../types/api';

const languageCodes = reference.languages.map((l) => l.code) as [string, ...string[]];
const statusKeys = reference.statuses.map((s) => s.key) as [string, ...string[]];

const baseSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  episode_number: z.string().optional(), // string from input; parsed below
  content_group: z.string().min(1, 'Content group is required'),
  language: z.enum(languageCodes),
  duration_seconds: z.string().optional(),
  synopsis: z.string().optional(),
  status: z.enum(statusKeys),
});

type FormValues = z.infer<typeof baseSchema>;

export default function EpisodeFormPage() {
  const { episodeId, seasonId, showId } = useParams();
  const isEditing = Boolean(episodeId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);

  const episodeQuery = useQuery({
    queryKey: ['episode', episodeId],
    queryFn: () => getEpisode(Number(episodeId)),
    enabled: isEditing,
  });

  // When creating, we need the season's context (is it trailer season?) — fetch via show's seasons.
  const effectiveShowId = showId ? Number(showId) : episodeQuery.data?.show_id;
  const seasonsQuery = useQuery({
    queryKey: ['seasons', effectiveShowId],
    queryFn: () => listSeasons(Number(effectiveShowId)),
    enabled: Boolean(effectiveShowId),
  });

  const currentSeasonId = isEditing ? episodeQuery.data?.season_id : Number(seasonId);
  const currentSeason = seasonsQuery.data?.items.find((s) => s.id === currentSeasonId);
  const isTrailerSeason = currentSeason?.is_trailer_season ?? false;

  const showQuery = useQuery({
    queryKey: ['show', String(effectiveShowId)],
    queryFn: () => getShow(Number(effectiveShowId)),
    enabled: Boolean(effectiveShowId),
  });

  const schema = useMemo(
    () =>
      baseSchema
        .extend({
          episode_number: isTrailerSeason
            ? z
                .string()
                .optional()
                .refine((v) => !v, 'Trailers (season 0) must not have an episode number.')
            : z.string().min(1, 'Episode number is required for non-trailer seasons'),
        })
        .superRefine((data, ctx) => {
          if (data.status === 'published') {
            const durationNum = Number(data.duration_seconds);
            if (!isTrailerSeason && (!data.duration_seconds || durationNum <= 0)) {
              ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ['duration_seconds'],
                message: 'A published episode must have a duration greater than 0 seconds.',
              });
            }
          }
        }),
    [isTrailerSeason]
  );

  const {
    register,
    handleSubmit,
    reset,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { status: 'draft', language: languageCodes[0] },
  });

  useEffect(() => {
    if (episodeQuery.data) {
      reset({
        title: episodeQuery.data.title,
        episode_number:
          episodeQuery.data.episode_number != null ? String(episodeQuery.data.episode_number) : '',
        content_group: episodeQuery.data.content_group,
        language: episodeQuery.data.language as FormValues['language'],
        duration_seconds:
          episodeQuery.data.duration_seconds != null ? String(episodeQuery.data.duration_seconds) : '',
        synopsis: episodeQuery.data.synopsis ?? '',
        status: episodeQuery.data.status,
      });
    }
  }, [episodeQuery.data, reset]);

  const watchedStatus = watch('status');

  const missingArtworkKinds = episodeQuery.data?.missing_artwork_kinds ?? [];

  const saveMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload = {
        title: values.title,
        episode_number:
          isTrailerSeason || !values.episode_number ? null : Number(values.episode_number),
        content_group: values.content_group,
        language: values.language,
        duration_seconds: values.duration_seconds ? Number(values.duration_seconds) : null,
        synopsis: values.synopsis || '',
        status: values.status as Episode['status'],
      };
      if (isEditing) return updateEpisode(Number(episodeId), payload);
      return createEpisode(Number(currentSeasonId), payload);
    },
    onSuccess: (episode) => {
      queryClient.invalidateQueries({ queryKey: ['episodes'] });
      queryClient.invalidateQueries({ queryKey: ['episode', String(episode.id)] });
      if (!isEditing) navigate(`/episodes/${episode.id}`);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setServerError(err.message);
        for (const detail of err.details) {
          const fieldMap: Record<string, keyof FormValues> = {
            language: 'language',
            content_group: 'content_group',
            episode_number: 'episode_number',
            duration_seconds: 'duration_seconds',
            title: 'title',
          };
          const field = detail.field ? fieldMap[detail.field.split('.')[0]] : undefined;
          if (field) {
            setError(field, { message: detail.message });
          }
        }
      } else {
        setServerError('Could not save this episode. Please try again.');
      }
    },
  });

  const onSubmit = (values: FormValues) => {
    setServerError(null);
    saveMutation.mutate(values);
  };

  const uploadArtwork = useMemo(
    () => (kind: string, file: File) =>
      uploadEpisodeArtwork(Number(episodeId), kind, file).then((art) => {
        queryClient.invalidateQueries({ queryKey: ['episode', episodeId] });
        return art;
      }),
    [episodeId, queryClient]
  );

  const artworkByKind = useMemo(() => {
    const map: Record<string, any> = {};
    for (const art of episodeQuery.data?.artwork ?? []) map[art.kind] = art;
    return map;
  }, [episodeQuery.data]);

  const loading = isEditing ? episodeQuery.isLoading : false;
  const error = isEditing ? episodeQuery.error : null;

  return (
    <div>
      <div className="page-header">
        <h1>{isEditing ? 'Edit episode' : 'New episode'}</h1>
        {effectiveShowId && (
          <Link to={`/shows/${effectiveShowId}`} className="btn btn-secondary">
            Back to show
          </Link>
        )}
      </div>

      <QueryStateGate isLoading={loading} error={error} onRetry={() => episodeQuery.refetch()}>
        <form className="panel entity-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <label htmlFor="title">Title</label>
          <input id="title" {...register('title')} />
          {errors.title && <p className="field-error">{errors.title.message}</p>}

          {!isTrailerSeason && (
            <>
              <label htmlFor="episode_number">Episode number</label>
              <input id="episode_number" type="number" min={1} {...register('episode_number')} />
              {errors.episode_number && <p className="field-error">{errors.episode_number.message}</p>}
            </>
          )}
          {isTrailerSeason && (
            <p className="field-hint">
              This is a season-0 (trailer) row. Episode number must be left empty.
            </p>
          )}

          <label htmlFor="content_group">
            Content group <span className="muted">(shared across language variants)</span>
          </label>
          <input id="content_group" {...register('content_group')} />
          {errors.content_group && <p className="field-error">{errors.content_group.message}</p>}

          <label htmlFor="language">Language</label>
          <select id="language" {...register('language')}>
            {reference.languages.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
          {errors.language && <p className="field-error">{errors.language.message}</p>}

          <label htmlFor="duration_seconds">
            Duration (seconds) {isTrailerSeason && <span className="muted">(trailers are exempt)</span>}
          </label>
          <input id="duration_seconds" type="number" min={0} {...register('duration_seconds')} />
          {errors.duration_seconds && <p className="field-error">{errors.duration_seconds.message}</p>}

          <label htmlFor="synopsis">Synopsis</label>
          <textarea id="synopsis" rows={3} {...register('synopsis')} />

          <label htmlFor="status">Status</label>
          <select id="status" {...register('status')}>
            {reference.statuses.map((s) => (
              <option key={s.key} value={s.key}>
                {s.label}
              </option>
            ))}
          </select>
          {watchedStatus === 'published' && isEditing && missingArtworkKinds.length > 0 && (
            <p className="field-error">
              This episode is still missing artwork: {missingArtworkKinds.join(', ')}. Upload it below
              before the server will accept a publish.
            </p>
          )}

          {serverError && (
            <div className="form-server-error" role="alert">
              {serverError}
            </div>
          )}

          <button className="btn btn-primary" type="submit" disabled={isSubmitting || saveMutation.isPending}>
            {saveMutation.isPending ? 'Saving...' : isEditing ? 'Save changes' : 'Create episode'}
          </button>
        </form>

        {isEditing && episodeQuery.data && (
          <section className="panel">
            <h2>Episode artwork</h2>
            <div className="artwork-grid">
              {reference.artwork.required_kinds_per_episode.map((kind) => (
                <ArtworkSlot
                  key={kind}
                  kind={kind as any}
                  existing={artworkByKind[kind]}
                  onUpload={(file) => uploadArtwork(kind, file)}
                />
              ))}
            </div>
          </section>
        )}

        {isEditing && episodeQuery.data && episodeQuery.data.variants && episodeQuery.data.variants.length > 0 && (
          <section className="panel">
            <h2>Language variants</h2>
            <ul>
              {episodeQuery.data.variants.map((v) => (
                <li key={v.id}>
                  <Link to={`/episodes/${v.id}`}>
                    {v.language} — {v.title} ({v.status})
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}
      </QueryStateGate>
    </div>
  );
}
