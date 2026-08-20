import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createShow,
  createSeason,
  getShow,
  listSeasons,
  updateShow,
  uploadShowArtwork,
} from '../api/endpoints';
import { reference } from '../lib/reference';
import { ApiError } from '../api/client';
import { QueryStateGate } from '../components/DataState';
import ArtworkSlot from '../components/ArtworkSlot';
import SeasonEpisodesPanel from '../components/SeasonEpisodesPanel';
import type { Show } from '../types/api';

const sectionKeys = reference.sections.map((s) => s.key) as [string, ...string[]];
const categoryKeys = reference.categories.map((c) => c.key) as [string, ...string[]];
const statusKeys = reference.statuses.map((s) => s.key) as [string, ...string[]];

const schema = z.object({
  title: z.string().min(1, 'Title is required'),
  slug: z.string().optional(),
  description: z.string().min(1, 'Description is required'),
  category: z.enum(categoryKeys, { errorMap: () => ({ message: 'Choose a valid category' }) }),
  section: z.union([z.enum(sectionKeys), z.literal('')]).optional(),
  status: z.enum(statusKeys),
});
type FormValues = z.infer<typeof schema>;

export default function ShowFormPage() {
  const { showId } = useParams();
  const isEditing = Boolean(showId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const [newSeasonNumber, setNewSeasonNumber] = useState('');
  const [newSeasonTitle, setNewSeasonTitle] = useState('');

  const showQuery = useQuery({
    queryKey: ['show', showId],
    queryFn: () => getShow(Number(showId)),
    enabled: isEditing,
  });

  const seasonsQuery = useQuery({
    queryKey: ['seasons', showId],
    queryFn: () => listSeasons(Number(showId)),
    enabled: isEditing,
  });

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { status: 'draft', category: categoryKeys[0] },
  });

  useEffect(() => {
    if (showQuery.data) {
      reset({
        title: showQuery.data.title,
        slug: showQuery.data.slug,
        description: showQuery.data.description,
        category: showQuery.data.category as FormValues['category'],
        section: (showQuery.data.section ?? '') as FormValues['section'],
        status: showQuery.data.status,
      });
    }
  }, [showQuery.data, reset]);

  const saveMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload = {
        title: values.title,
        slug: values.slug || undefined,
        description: values.description,
        category: values.category,
        section: values.section || null,
        status: values.status as Show['status'],
      };
      if (isEditing) return updateShow(Number(showId), payload);
      return createShow(payload);
    },
    onSuccess: (show) => {
      queryClient.invalidateQueries({ queryKey: ['shows'] });
      queryClient.invalidateQueries({ queryKey: ['show', String(show.id)] });
      if (!isEditing) navigate(`/shows/${show.id}`);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setServerError(err.message);
        for (const detail of err.details) {
          if (detail.field && detail.field in schema.shape) {
            setError(detail.field as keyof FormValues, { message: detail.message });
          }
        }
      } else {
        setServerError('Could not save this show. Please try again.');
      }
    },
  });

  const onSubmit = (values: FormValues) => {
    setServerError(null);
    saveMutation.mutate(values);
  };

  const addSeasonMutation = useMutation({
    mutationFn: () =>
      createSeason(Number(showId), {
        season_number: Number(newSeasonNumber),
        title: newSeasonTitle || `Season ${newSeasonNumber}`,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['seasons', showId] });
      setNewSeasonNumber('');
      setNewSeasonTitle('');
    },
  });

  const uploadArtwork = useMemo(
    () => (kind: string, file: File) => uploadShowArtwork(Number(showId), kind, file).then((art) => {
      queryClient.invalidateQueries({ queryKey: ['show', showId] });
      return art;
    }),
    [showId, queryClient]
  );

  const artworkByKind = useMemo(() => {
    const map: Record<string, any> = {};
    for (const art of showQuery.data?.artwork ?? []) map[art.kind] = art;
    return map;
  }, [showQuery.data]);

  return (
    <div>
      <div className="page-header">
        <h1>{isEditing ? `Edit show` : 'New show'}</h1>
        <Link to="/shows" className="btn btn-secondary">
          Back to shows
        </Link>
      </div>

      {isEditing ? (
        <QueryStateGate isLoading={showQuery.isLoading} error={showQuery.error} onRetry={() => showQuery.refetch()}>
          <ShowForm />
        </QueryStateGate>
      ) : (
        <ShowForm />
      )}

      {isEditing && showQuery.data && (
        <>
          <section className="panel">
            <h2>Show artwork</h2>
            <div className="artwork-grid">
              {reference.artwork.required_kinds_per_show.map((kind) => (
                <ArtworkSlot
                  key={kind}
                  kind={kind as any}
                  existing={artworkByKind[kind]}
                  onUpload={(file) => uploadArtwork(kind, file)}
                />
              ))}
            </div>
          </section>

          <section className="panel">
            <h2>Seasons</h2>
            <QueryStateGate
              isLoading={seasonsQuery.isLoading}
              error={seasonsQuery.error}
              isEmpty={!seasonsQuery.isLoading && !seasonsQuery.error && (seasonsQuery.data?.items.length ?? 0) === 0}
              emptyTitle="No seasons yet"
              onRetry={() => seasonsQuery.refetch()}
            >
              <div className="seasons-list">
                {seasonsQuery.data?.items.map((season) => (
                  <SeasonEpisodesPanel key={season.id} season={season} showId={Number(showId)} />
                ))}
              </div>
            </QueryStateGate>

            <form
              className="inline-form"
              onSubmit={(e) => {
                e.preventDefault();
                addSeasonMutation.mutate();
              }}
            >
              <input
                type="number"
                min={0}
                placeholder="Season # (0 = trailers)"
                value={newSeasonNumber}
                onChange={(e) => setNewSeasonNumber(e.target.value)}
                required
              />
              <input
                type="text"
                placeholder="Season title (optional)"
                value={newSeasonTitle}
                onChange={(e) => setNewSeasonTitle(e.target.value)}
              />
              <button className="btn btn-secondary" type="submit" disabled={addSeasonMutation.isPending}>
                Add season
              </button>
            </form>
            {addSeasonMutation.error instanceof ApiError && (
              <p className="field-error">{addSeasonMutation.error.message}</p>
            )}
          </section>
        </>
      )}
    </div>
  );

  function ShowForm() {
    return (
      <form className="panel entity-form" onSubmit={handleSubmit(onSubmit)} noValidate>
        <label htmlFor="title">Title</label>
        <input id="title" {...register('title')} />
        {errors.title && <p className="field-error">{errors.title.message}</p>}

        <label htmlFor="slug">Slug (optional, derived from title if empty)</label>
        <input id="slug" {...register('slug')} />
        {errors.slug && <p className="field-error">{errors.slug.message}</p>}

        <label htmlFor="description">Description</label>
        <textarea id="description" rows={3} {...register('description')} />
        {errors.description && <p className="field-error">{errors.description.message}</p>}

        <label htmlFor="category">Category</label>
        <select id="category" {...register('category')}>
          {reference.categories.map((c) => (
            <option key={c.key} value={c.key}>
              {c.label}
            </option>
          ))}
        </select>
        {errors.category && <p className="field-error">{errors.category.message}</p>}

        <label htmlFor="section">Section</label>
        <select id="section" {...register('section')}>
          <option value="">— none (draft only) —</option>
          {reference.sections
            .filter((s) => s.show_in_nav)
            .map((s) => (
              <option key={s.key} value={s.key}>
                {s.label}
              </option>
            ))}
        </select>
        {errors.section && <p className="field-error">{errors.section.message}</p>}
        <p className="field-hint">A published show must have a section and poster + banner artwork.</p>

        <label htmlFor="status">Status</label>
        <select id="status" {...register('status')}>
          {reference.statuses.map((s) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>

        {serverError && (
          <div className="form-server-error" role="alert">
            {serverError}
          </div>
        )}

        <button className="btn btn-primary" type="submit" disabled={isSubmitting || saveMutation.isPending}>
          {saveMutation.isPending ? 'Saving...' : isEditing ? 'Save changes' : 'Create show'}
        </button>
      </form>
    );
  }
}
