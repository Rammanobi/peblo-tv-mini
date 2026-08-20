import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listShows } from '../api/endpoints';
import { reference, labelFor } from '../lib/reference';
import { QueryStateGate } from '../components/DataState';
import useDebouncedValue from '../hooks/useDebouncedValue';

const PAGE_SIZE = 20;

export default function ShowListPage() {
  const [q, setQ] = useState('');
  const [section, setSection] = useState('');
  const [status, setStatus] = useState('');
  const [category, setCategory] = useState('');
  const [offset, setOffset] = useState(0);

  const debouncedQ = useDebouncedValue(q, 300);

  const filters = useMemo(
    () => ({
      q: debouncedQ || undefined,
      section: section || undefined,
      status: status || undefined,
      category: category || undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    [debouncedQ, section, status, category, offset]
  );

  const query = useQuery({
    queryKey: ['shows', filters],
    queryFn: () => listShows(filters),
  });

  const resetToFirstPage = () => setOffset(0);

  const total = query.data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="page-header">
        <h1>Shows</h1>
        <Link to="/shows/new" className="btn btn-primary">
          + New show
        </Link>
      </div>

      <div className="filter-bar">
        <input
          type="search"
          placeholder="Search by title..."
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            resetToFirstPage();
          }}
          aria-label="Search shows by title"
        />
        <select
          value={section}
          onChange={(e) => {
            setSection(e.target.value);
            resetToFirstPage();
          }}
          aria-label="Filter by section"
        >
          <option value="">All sections</option>
          {reference.sections.map((s) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            resetToFirstPage();
          }}
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          {reference.statuses.map((s) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>
        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            resetToFirstPage();
          }}
          aria-label="Filter by category"
        >
          <option value="">All categories</option>
          {reference.categories.map((c) => (
            <option key={c.key} value={c.key}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <QueryStateGate
        isLoading={query.isLoading}
        error={query.error}
        isEmpty={!query.isLoading && !query.error && (query.data?.items.length ?? 0) === 0}
        emptyTitle="No shows match these filters"
        emptyHint="Try clearing the search box or filters, or create a new show."
        onRetry={() => query.refetch()}
      >
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Section</th>
                <th>Category</th>
                <th>Status</th>
                <th>Seasons</th>
                <th>Episodes</th>
                <th>Trailers</th>
              </tr>
            </thead>
            <tbody>
              {query.data?.items.map((show) => (
                <tr key={show.id}>
                  <td>
                    <Link to={`/shows/${show.id}`}>{show.title}</Link>
                  </td>
                  <td>{labelFor(reference.sections, show.section)}</td>
                  <td>{labelFor(reference.categories, show.category)}</td>
                  <td>
                    <span className={`status-pill status-${show.status}`}>{show.status}</span>
                  </td>
                  <td>{show.season_count}</td>
                  <td>{show.episode_count}</td>
                  <td>{show.trailer_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="pagination">
          <button
            className="btn btn-secondary"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            Previous
          </button>
          <span>
            Page {page} of {pageCount} ({total} total)
          </span>
          <button
            className="btn btn-secondary"
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next
          </button>
        </div>
      </QueryStateGate>
    </div>
  );
}
