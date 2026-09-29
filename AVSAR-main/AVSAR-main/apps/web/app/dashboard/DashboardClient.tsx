'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import {
  type CrosswalkRow,
  type DistrictRow,
  type GapItem,
  type Role,
  type SessionDetail,
  type SessionRow,
  type Stats,
  clearSession,
  downloadExport,
  fetchAuditLog,
  fetchCrosswalk,
  fetchDistricts,
  fetchGap,
  fetchSessionDetail,
  fetchSessions,
  fetchStats,
  getRole,
  getToken,
  login,
  updateCrosswalk,
} from '@/lib/officer';

type Tab = 'overview' | 'gap' | 'sessions' | 'crosswalk';

const CHART_COLOURS = ['#4338ca', '#6366f1', '#818cf8', '#a5b4fc', '#c7d2fe'];

export default function DashboardClient() {
  const [role, setRole] = useState<Role | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [district, setDistrict] = useState<string>('');
  const [stats, setStats] = useState<Stats | null>(null);
  const [gap, setGap] = useState<{ items: GapItem[]; flagged: number; legend: Record<string, string> } | null>(null);
  const [districts, setDistricts] = useState<DistrictRow[]>([]);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [crosswalk, setCrosswalk] = useState<CrosswalkRow[]>([]);
  const [canEdit, setCanEdit] = useState(false);
  const [audit, setAudit] = useState<any[]>([]);
  const [error, setError] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState('');

  useEffect(() => {
    if (getToken()) setRole(getRole());
  }, []);

  const load = useCallback(async () => {
    if (!role) return;
    setError('');
    try {
      const [s, g, d] = await Promise.all([
        fetchStats(district || undefined),
        fetchGap(district || undefined),
        fetchDistricts(),
      ]);
      setStats(s);
      setGap(g);
      setDistricts(d.items);
      if (s.can_drill_down) {
        const list = await fetchSessions(district || undefined);
        setSessions(list.items);
      }
    } catch (err) {
      setError((err as Error).message);
      if ((err as Error).message === 'unauthorized') setRole(null);
    }
  }, [role, district]);

  useEffect(() => {
    void load();
  }, [load]);

  const openCrosswalk = async (gapsOnly = false) => {
    try {
      const data = await fetchCrosswalk(undefined, gapsOnly);
      setCrosswalk(data.items);
      setCanEdit(data.can_edit);
      if (data.can_edit) setAudit((await fetchAuditLog()).items);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  if (!role) return <LoginScreen onSuccess={(r) => setRole(r)} />;

  return (
    <main id="main" className="mx-auto max-w-6xl space-y-5 p-5" lang="en">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold text-brand-900 dark:text-brand-200">
            Officer Dashboard
          </h1>
          <p className="text-sm text-ink-muted">
            PM-AJAY GIA · aspirations captured by AVSAR · signed in as <b>{role}</b>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="district" className="sr-only">
            Filter by district
          </label>
          <select
            id="district"
            value={district}
            onChange={(event) => setDistrict(event.target.value)}
            className="min-h-tap rounded-xl2 border-2 border-slate-300 px-3 py-2 text-base dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="">All districts</option>
            {districts.map((d) => (
              <option key={d.district_code} value={d.district_code}>
                {d.district} ({d.sessions})
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => {
              clearSession();
              setRole(null);
            }}
            className="tap-secondary text-base"
          >
            Sign out
          </button>
        </div>
      </header>

      {error && (
        <p role="alert" className="rounded-xl2 border-2 border-danger-500 bg-danger-100 p-3 text-danger-500">
          {error}
        </p>
      )}
      {toast && <p className="chip-ok">{toast}</p>}

      <nav className="flex flex-wrap gap-2" aria-label="Dashboard sections">
        {(['overview', 'gap', 'sessions', 'crosswalk'] as Tab[]).map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => {
              setTab(name);
              if (name === 'crosswalk') void openCrosswalk();
            }}
            aria-current={tab === name ? 'page' : undefined}
            className={`tap text-base ${tab === name ? 'bg-brand-700 text-white' : 'tap-secondary'}`}
          >
            {name === 'overview' && '📊 Overview'}
            {name === 'gap' && '⚠ Gap panel'}
            {name === 'sessions' && '🗂 Sessions'}
            {name === 'crosswalk' && '🔗 Crosswalk'}
          </button>
        ))}
      </nav>

      {/* ---------------- OVERVIEW ---------------- */}
      {tab === 'overview' && stats && (
        <section className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Sessions captured" value={stats.total_sessions} />
            <Stat
              label="Women participation"
              value={`${stats.women_pct}%`}
              target={`target ≥ ${stats.compliance?.women?.target_pct ?? 30}%`}
              ok={stats.compliance?.women?.meets_mandate}
            />
            <Stat
              label="Consent complete"
              value={`${stats.consent_pct}%`}
              target="DPDP s.6"
              ok={stats.consent_pct >= 100}
            />
            <Stat
              label="Priority income ≤ ₹2.5L"
              value={stats.priority_income_pct === null ? '—' : `${stats.priority_income_pct}%`}
              target="priority, not eligibility"
            />
          </div>

          <div className="card">
            <h2 className="mb-3 text-xl font-semibold">Aspirations by GIA domain</h2>
            {stats.by_domain.length === 0 ? (
              <p className="text-ink-muted">No aspirations captured yet.</p>
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats.by_domain} layout="vertical" margin={{ left: 12, right: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} />
                    <YAxis type="category" dataKey="name" width={190} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" name="Aspirations" radius={[0, 6, 6, 0]}>
                      {stats.by_domain.map((_, index) => (
                        <Cell key={index} fill={CHART_COLOURS[index % CHART_COLOURS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="mb-3 text-xl font-semibold">Top activity concepts</h2>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.top_concepts.slice(0, 10)} margin={{ left: 4, right: 12 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="concept" tick={{ fontSize: 11 }} interval={0} angle={-25} textAnchor="end" height={70} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" name="Aspirations" fill="#4338ca" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <h2 className="mb-3 text-xl font-semibold">Districts</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <caption className="sr-only">Sessions and women participation by district</caption>
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th scope="col" className="py-2">District</th>
                    <th scope="col">State</th>
                    <th scope="col">Sessions</th>
                    <th scope="col">Women %</th>
                    <th scope="col">≥30% mandate</th>
                    <th scope="col">Consent %</th>
                  </tr>
                </thead>
                <tbody>
                  {districts.map((d) => (
                    <tr key={d.district_code} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-2 font-medium">{d.district}</td>
                      <td>{d.state}</td>
                      <td>{d.sessions}</td>
                      <td>{d.women_pct}%</td>
                      <td>
                        <span className={d.meets_women_mandate ? 'chip-ok' : 'chip-danger'}>
                          {d.meets_women_mandate ? '✓ meets' : '✗ below'}
                        </span>
                      </td>
                      <td>{d.consent_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <ExportBar district={district} onDone={(m) => setToast(m)} onError={setError} busy={busy} setBusy={setBusy} />
        </section>
      )}

      {/* ---------------- GAP ---------------- */}
      {tab === 'gap' && gap && (
        <section className="card space-y-3">
          <h2 className="text-xl font-semibold">
            Demand vs local supply {gap.flagged > 0 && <span className="chip-warn">⚠ {gap.flagged} flagged</span>}
          </h2>
          <p className="text-sm text-ink-muted">
            Aspirations captured here, against seats available in this district&apos;s centres.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Aspiration demand against local training supply</caption>
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th scope="col" className="py-2">Concept</th>
                  <th scope="col">Demand</th>
                  <th scope="col">Seats</th>
                  <th scope="col">QPs</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {gap.items.map((item) => (
                  <tr key={item.concept} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-2 font-medium">{item.concept}</td>
                    <td>{item.demand_n}</td>
                    <td>{item.supply_seats}</td>
                    <td className="font-mono text-xs">{item.qp_codes.length}</td>
                    <td>
                      {item.status === 'supplied' && <span className="chip-ok">✓ supplied</span>}
                      {item.status === 'no_local_supply' && <span className="chip-warn">⚠ no local supply</span>}
                      {item.status === 'no_qualification' && <span className="chip-danger">✗ no qualification exists</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <dl className="text-xs text-ink-muted">
            {Object.entries(gap.legend).map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <dt className="font-mono">{key}</dt>
                <dd>— {value}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {/* ---------------- SESSIONS ---------------- */}
      {tab === 'sessions' && (
        <section className="space-y-4">
          {!stats?.can_drill_down ? (
            <p className="card">
              Your role can see aggregates only. Individual beneficiary rows are restricted to
              officers (ARCHITECTURE §9 row-level access).
            </p>
          ) : (
            <>
              <div className="card overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <caption className="sr-only">Captured sessions</caption>
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th scope="col" className="py-2">District</th>
                      <th scope="col">Lang</th>
                      <th scope="col">Age</th>
                      <th scope="col">Gender</th>
                      <th scope="col">Education</th>
                      <th scope="col">Consent</th>
                      <th scope="col">Flags</th>
                      <th scope="col"><span className="sr-only">Open</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map((s) => (
                      <tr key={s.session_id} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-2 font-medium">{s.district ?? '—'}</td>
                        <td>{s.lang}</td>
                        <td>{s.age_band ?? '—'}</td>
                        <td>{s.gender ?? '—'}</td>
                        <td>{s.edu_level ?? '—'}</td>
                        <td>{s.consent ? <span className="chip-ok">✓</span> : <span className="chip-danger">✗</span>}</td>
                        <td className="space-x-1">
                          {s.synthetic && <span className="chip-synthetic">⚗️ sample</span>}
                          {s.degraded && <span className="chip-warn">⚠ degraded</span>}
                          {s.officer_callback && <span className="chip-warn">☎ callback</span>}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="tap-secondary text-sm"
                            onClick={async () => setDetail(await fetchSessionDetail(s.session_id))}
                          >
                            Open
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {detail && <SessionDetailPanel detail={detail} onClose={() => setDetail(null)} />}
            </>
          )}
        </section>
      )}

      {/* ---------------- CROSSWALK ---------------- */}
      {tab === 'crosswalk' && (
        <section className="space-y-4">
          <div className="card">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold">Crosswalk review</h2>
              <button type="button" className="tap-secondary text-sm" onClick={() => openCrosswalk(false)}>
                All
              </button>
              <button type="button" className="tap-secondary text-sm" onClick={() => openCrosswalk(true)}>
                Declared gaps only
              </button>
              {!canEdit && <span className="chip-warn">read-only — admin role required to edit</span>}
            </div>
            <p className="mb-3 text-sm text-ink-muted">
              The aspiration→QP join table. No register publishes this link, so it is hand-authored
              and versioned here; every edit writes an audit record.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <caption className="sr-only">Curated aspiration to qualification mappings</caption>
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th scope="col" className="py-2">Phrase</th>
                    <th scope="col">Lang</th>
                    <th scope="col">Concept</th>
                    <th scope="col">Domain</th>
                    <th scope="col">QPs</th>
                    <th scope="col">Status</th>
                    <th scope="col">v</th>
                    {canEdit && <th scope="col"><span className="sr-only">Action</span></th>}
                  </tr>
                </thead>
                <tbody>
                  {crosswalk.map((row) => (
                    <tr key={row.id} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-2" lang={row.lang}>{row.phrase}</td>
                      <td>{row.lang}</td>
                      <td className="font-mono text-xs">{row.concept}</td>
                      <td className="text-xs">{row.gia_domain_name}</td>
                      <td className="font-mono text-xs">
                        {row.is_gap ? <span className="chip-danger">declared gap</span> : row.qp_codes.length}
                      </td>
                      <td>
                        <span className={row.status === 'reviewed' ? 'chip-ok' : 'chip-warn'}>{row.status}</span>
                      </td>
                      <td>{row.version}</td>
                      {canEdit && (
                        <td>
                          <button
                            type="button"
                            className="tap-secondary text-sm"
                            onClick={async () => {
                              try {
                                await updateCrosswalk(row.id, { status: 'reviewed' });
                                setToast(`Entry ${row.id} re-approved — audit record written`);
                                await openCrosswalk();
                              } catch (err) {
                                setError((err as Error).message);
                              }
                            }}
                          >
                            Approve
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {canEdit && audit.length > 0 && (
            <div className="card">
              <h2 className="mb-2 text-xl font-semibold">Audit log</h2>
              <ul className="space-y-1 text-xs">
                {audit.slice(0, 10).map((entry) => (
                  <li key={entry.id} className="font-mono">
                    {entry.ts?.slice(0, 19)} · actor {entry.actor} · {entry.action} · {entry.entity}#
                    {entry.entity_id}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <footer className="border-t border-slate-200 pt-4 text-xs text-ink-muted dark:border-slate-800">
        {stats && stats.synthetic.sessions > 0 && (
          <p className="mb-1">
            <span className="chip-synthetic">⚗️ Sample data</span>{' '}
            {stats.synthetic.sessions} of {stats.total_sessions} sessions ({stats.synthetic.share_pct}%)
            are seeded demo records, not real field intake. Catalogue and district-supply rows are
            likewise labelled — see <code>docs/ingest-report.md</code>.
          </p>
        )}
        <p>
          Compliance basis: PM-AJAY Guidelines (May 2023 Revised), Ch. 3 §7.A.a.iv — job roles must
          be endorsed on aspiration of the target group and availability of job market.
        </p>
      </footer>
    </main>
  );
}

function Stat({
  label,
  value,
  target,
  ok,
}: {
  label: string;
  value: string | number;
  target?: string;
  ok?: boolean;
}) {
  return (
    <div className="card">
      <p className="text-sm text-ink-muted">{label}</p>
      <p className="mt-1 text-3xl font-semibold">{value}</p>
      {target && (
        <p className="mt-1 text-xs">
          {ok === undefined ? (
            <span className="text-ink-muted">{target}</span>
          ) : (
            <span className={ok ? 'chip-ok' : 'chip-danger'}>{ok ? '✓' : '✗'} {target}</span>
          )}
        </p>
      )}
    </div>
  );
}

function ExportBar({
  district,
  onDone,
  onError,
  busy,
  setBusy,
}: {
  district: string;
  onDone: (m: string) => void;
  onError: (m: string) => void;
  busy: boolean;
  setBusy: (b: boolean) => void;
}) {
  const run = async (kind: 'csv' | 'xlsx') => {
    setBusy(true);
    try {
      const size = await downloadExport(kind, district || undefined);
      onDone(`${kind.toUpperCase()} downloaded (${(size / 1024).toFixed(1)} KB)`);
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="card flex flex-wrap items-center gap-3">
      <h2 className="text-lg font-semibold">Export</h2>
      <button type="button" disabled={busy} onClick={() => run('csv')} className="tap-secondary text-base">
        ⬇ Sessions CSV
      </button>
      <button type="button" disabled={busy} onClick={() => run('xlsx')} className="tap-primary text-base">
        ⬇ AAP annexure XLSX
      </button>
      <span className="text-xs text-ink-muted">
        AAP annexure groups aspirations by GIA domain — the shape an Annual Action Plan needs.
      </span>
    </div>
  );
}

function SessionDetailPanel({ detail, onClose }: { detail: SessionDetail; onClose: () => void }) {
  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">
          Session drill-down · {detail.district.name ?? '—'} · {detail.lang}
        </h2>
        <button type="button" onClick={onClose} className="tap-secondary text-sm">
          Close
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {detail.synthetic && <span className="chip-synthetic">⚗️ sample data</span>}
        {detail.consent.granted ? (
          <span className="chip-ok">✓ consent recorded</span>
        ) : (
          <span className="chip-danger">✗ no consent — profile not stored</span>
        )}
        {detail.degraded && <span className="chip-warn">⚠ degraded (fallback used)</span>}
        {detail.officer_callback && <span className="chip-warn">☎ officer callback requested</span>}
      </div>

      <div>
        <h3 className="font-semibold">Parsed slots</h3>
        <dl className="grid grid-cols-2 gap-x-4 text-sm sm:grid-cols-4">
          {Object.entries(detail.profile).map(([key, value]) => (
            <div key={key}>
              <dt className="text-ink-muted">{key}</dt>
              <dd className="font-medium">{String(value ?? '—')}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div>
        <h3 className="font-semibold">Transcript</h3>
        <ol className="space-y-1 text-sm">
          {detail.transcript.map((turn) => (
            <li key={turn.turn_no} className="rounded bg-slate-50 p-2 dark:bg-slate-800">
              <span className="text-ink-muted">#{turn.turn_no} [{turn.provider}]</span>{' '}
              <span lang={detail.lang}>{turn.text || <em>(no speech detected)</em>}</span>
              {turn.confidence !== null && (
                <span className="ml-2 text-xs text-ink-muted">
                  conf {Math.round((turn.confidence ?? 0) * 100)}%
                </span>
              )}
            </li>
          ))}
        </ol>
      </div>

      <div>
        <h3 className="font-semibold">Recommendations</h3>
        {detail.recommendations.length === 0 ? (
          <p className="text-sm text-ink-muted">
            None — the aspiration had no qualification in the register, so AVSAR refused rather than
            suggesting an unrelated trade.
          </p>
        ) : (
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Recommended qualifications with scores</caption>
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700">
                <th scope="col">#</th>
                <th scope="col">QP</th>
                <th scope="col">Course</th>
                <th scope="col">NSQF</th>
                <th scope="col">Score</th>
                <th scope="col">Grounded</th>
              </tr>
            </thead>
            <tbody>
              {detail.recommendations.map((rec) => (
                <tr key={rec.rank} className="border-b border-slate-100 dark:border-slate-800">
                  <td>{rec.rank}</td>
                  <td className="font-mono text-xs">{rec.qp_code}</td>
                  <td>
                    {rec.name} {rec.confirmed && <span className="chip-ok">chosen</span>}
                  </td>
                  <td>{rec.nsqf_level ?? '—'}</td>
                  <td>{rec.score.toFixed(4)}</td>
                  <td>{rec.grounded ? '✓' : '⚠'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function LoginScreen({ onSuccess }: { onSuccess: (role: Role) => void }) {
  const [email, setEmail] = useState('officer@demo');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  return (
    <main id="main" className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-5 p-6">
      <h1 className="text-3xl font-semibold text-brand-900 dark:text-brand-200">Officer sign-in</h1>
      <form
        className="card space-y-4"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError('');
          try {
            const { role } = await login(email, password);
            onSuccess(role);
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-xl2 border-2 border-slate-300 px-4 py-3 text-lg dark:border-slate-700 dark:bg-slate-900"
          />
        </div>
        <div>
          <label htmlFor="password" className="mb-1 block text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-xl2 border-2 border-slate-300 px-4 py-3 text-lg dark:border-slate-700 dark:bg-slate-900"
          />
        </div>
        {error && (
          <p role="alert" className="text-danger-500">
            {error}
          </p>
        )}
        <button type="submit" disabled={busy} className="tap-primary w-full justify-center">
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      <p className="text-xs text-ink-muted">
        Demo accounts are created by <code>make seed</code> from <code>.env</code>; passwords are
        never committed. Roles: viewer (aggregates only), officer (drill-down + exports), admin
        (crosswalk edits).
      </p>
    </main>
  );
}
