"use client";
import { useEffect, useState, useCallback } from "react";
import styles from "./page.module.css";

// ── Types ─────────────────────────────────────────────────────────────────────
type AssetType   = "domain" | "ip" | "service";
type AssetStatus = "active" | "inactive";

interface Asset {
  id:         string;
  name:       string;
  type:       AssetType;
  status:     AssetStatus;
  created_at: string;
}

interface ScanJob {
  job_id:      string;
  asset_id:    string;
  status:      string;
  result:      Record<string, unknown> | null;
  error:       string | null;
  created_at:  string;
  completed_at: string | null;
}

interface Pagination {
  page:        number;
  limit:       number;
  total:       number;
  total_pages: number;
}

interface Stats {
  total:     number;
  by_type:   Record<string, number>;
  by_status: Record<string, number>;
}

const API = "/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── Badge ─────────────────────────────────────────────────────────────────────
function Badge({ value, variant = "default" }: { value: string; variant?: string }) {
  const colors: Record<string, string> = {
    domain:    "#7c6af7",
    ip:        "#22d3a0",
    service:   "#f7a45a",
    active:    "#22d3a0",
    inactive:  "#6b7280",
    pending:   "#f7a45a",
    running:   "#7c6af7",
    completed: "#22d3a0",
    failed:    "#f75a5a",
    default:   "#6b7280",
  };
  const color = colors[value] ?? colors[variant] ?? colors.default;
  return (
    <span style={{
      background: color + "22",
      color,
      border:       `1px solid ${color}44`,
      borderRadius: "4px",
      padding:      "2px 8px",
      fontSize:     "11px",
      fontWeight:   600,
      letterSpacing: "0.05em",
    }}>
      {value}
    </span>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function Home() {
  const [tab, setTab]               = useState<"list" | "create" | "stats">("list");
  const [assets, setAssets]         = useState<Asset[]>([]);
  const [pagination, setPagination] = useState<Pagination | null>(null);
  const [stats, setStats]           = useState<Stats | null>(null);
  const [selected, setSelected]     = useState<Set<string>>(new Set());
  const [scanJobs, setScanJobs]     = useState<Record<string, ScanJob>>({});
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");
  const [page, setPage]             = useState(1);
  const [filterType, setFilterType] = useState("");
  const [search, setSearch]         = useState("");

  // Create form
  const [newName,   setNewName]   = useState("");
  const [newType,   setNewType]   = useState<AssetType>("domain");
  const [newStatus, setNewStatus] = useState<AssetStatus>("active");
  const [creating,  setCreating]  = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      let url = `/assets?page=${page}&limit=20`;
      if (filterType) url += `&type=${filterType}`;
      const data = await apiFetch<{ data: Asset[]; pagination: Pagination }>(url);
      setAssets(data.data);
      setPagination(data.pagination);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "HTTP 404");
    } finally {
      setLoading(false);
    }
  }, [page, filterType]);

  const loadStats = useCallback(async () => {
    try {
      const data = await apiFetch<Stats>("/assets/stats");
      setStats(data);
    } catch {}
  }, []);

  useEffect(() => { load(); loadStats(); }, [load, loadStats]);

  const doSearch = async () => {
    if (!search.trim()) return load();
    setLoading(true);
    try {
      const data = await apiFetch<Asset[]>(`/assets/search?q=${encodeURIComponent(search)}`);
      setAssets(data);
      setPagination(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const createAsset = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await apiFetch("/assets/batch", {
        method: "POST",
        body: JSON.stringify({ assets: [{ name: newName, type: newType, status: newStatus }] }),
      });
      setNewName("");
      setTab("list");
      load();
      loadStats();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setCreating(false);
    }
  };

  const batchDelete = async (ids: string[]) => {
    if (!ids.length) return;
    await apiFetch(`/assets/batch?ids=${ids.join(",")}`, { method: "DELETE" });
    setSelected(new Set());
    load();
    loadStats();
  };

  const startScan = async (assetId: string) => {
    try {
      const job = await apiFetch<ScanJob>(`/assets/${assetId}/scan`, { method: "POST" });
      setScanJobs(prev => ({ ...prev, [assetId]: job }));
      pollJob(assetId, job.job_id);
    } catch (e: unknown) {
      setScanJobs(prev => ({
        ...prev,
        [assetId]: {
          job_id: "", asset_id: assetId, status: "failed",
          result: null, error: e instanceof Error ? e.message : "Scan failed",
          created_at: new Date().toISOString(), completed_at: null,
        },
      }));
    }
  };

  const pollJob = async (assetId: string, jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const job = await apiFetch<ScanJob>(`/scan/jobs/${jobId}`);
        setScanJobs(prev => ({ ...prev, [assetId]: job }));
        if (job.status === "completed" || job.status === "failed") {
          clearInterval(interval);
        }
      } catch {
        clearInterval(interval);
      }
    }, 3000);
  };

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    setSelected(prev => prev.size === assets.length ? new Set() : new Set(assets.map(a => a.id)));
  };

  const formatDate = (d: string) => new Date(d).toLocaleDateString("vi-VN");

  return (
    <div className={styles.shell}>
      {/* Navbar */}
      <nav className={styles.nav}>
        <div className={styles.navBrand}>
          <span className={styles.navIcon}>⬡</span>
          <span className={styles.navTitle}>ASSET MGR</span>
        </div>
        <div className={styles.navTabs}>
          {(["list", "create", "stats"] as const).map(t => (
            <button key={t} className={tab === t ? styles.tabActive : styles.tab}
              onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </div>
      </nav>

      <main className={styles.main}>
        {/* ── LIST TAB ─────────────────────────────────────────────── */}
        {tab === "list" && (
          <div>
            {/* Toolbar */}
            <div className={styles.toolbar}>
              <input
                className={styles.searchInput}
                placeholder="Search by name…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                onKeyDown={e => e.key === "Enter" && doSearch()}
              />
              <select value={filterType} onChange={e => { setFilterType(e.target.value); setPage(1); }}
                className={styles.select}>
                <option value="">all types</option>
                <option value="domain">domain</option>
                <option value="ip">ip</option>
                <option value="service">service</option>
              </select>
              <button className={styles.btnSecondary} onClick={() => { setSearch(""); load(); }}>↺</button>
              {selected.size > 0 && (
                <button className={styles.btnDanger}
                  onClick={() => batchDelete(Array.from(selected))}>
                  Delete ({selected.size})
                </button>
              )}
            </div>

            {error && <div className={styles.errorBanner}>{error}</div>}

            {/* Table */}
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th><input type="checkbox" checked={selected.size === assets.length && assets.length > 0}
                      onChange={toggleAll} /></th>
                    <th>NAME</th>
                    <th>TYPE</th>
                    <th>STATUS</th>
                    <th>CREATED</th>
                    <th>SCAN</th>
                  </tr>
                </thead>
                <tbody>
                  {assets.length === 0 && !loading && (
                    <tr><td colSpan={6} className={styles.empty}>No assets found</td></tr>
                  )}
                  {assets.map(asset => {
                    const job = scanJobs[asset.id];
                    return (
                      <tr key={asset.id} className={selected.has(asset.id) ? styles.rowSelected : styles.row}>
                        <td><input type="checkbox" checked={selected.has(asset.id)}
                          onChange={() => toggleSelect(asset.id)} /></td>
                        <td>
                          <div className={styles.assetName}>{asset.name}</div>
                          <div className={styles.assetId}>{asset.id.slice(0, 8)}…</div>
                        </td>
                        <td><Badge value={asset.type} /></td>
                        <td><Badge value={asset.status} /></td>
                        <td className={styles.muted}>{formatDate(asset.created_at)}</td>
                        <td>
                          {!job || job.status === "failed" || job.status === "completed" ? (
                            <button className={styles.btnScan}
                              onClick={() => startScan(asset.id)}>
                              {job?.status === "completed" ? "re-scan" : "scan"}
                            </button>
                          ) : (
                            <Badge value={job.status} />
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {pagination && pagination.total_pages > 1 && (
              <div className={styles.pagination}>
                <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className={styles.btnSecondary}>←</button>
                <span className={styles.muted}>{page} / {pagination.total_pages}</span>
                <button disabled={page >= pagination.total_pages}
                  onClick={() => setPage(p => p + 1)} className={styles.btnSecondary}>→</button>
              </div>
            )}
          </div>
        )}

        {/* ── CREATE TAB ───────────────────────────────────────────── */}
        {tab === "create" && (
          <div className={styles.createForm}>
            <h2 className={styles.formTitle}>Add New Asset</h2>
            {error && <div className={styles.errorBanner}>{error}</div>}
            <div className={styles.formGroup}>
              <label className={styles.label}>Name</label>
              <input value={newName} onChange={e => setNewName(e.target.value)}
                placeholder="example.com or 192.168.1.1"
                className={styles.input} onKeyDown={e => e.key === "Enter" && createAsset()} />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.label}>Type</label>
              <select value={newType} onChange={e => setNewType(e.target.value as AssetType)}
                className={styles.select}>
                <option value="domain">domain</option>
                <option value="ip">ip</option>
                <option value="service">service</option>
              </select>
            </div>
            <div className={styles.formGroup}>
              <label className={styles.label}>Status</label>
              <select value={newStatus} onChange={e => setNewStatus(e.target.value as AssetStatus)}
                className={styles.select}>
                <option value="active">active</option>
                <option value="inactive">inactive</option>
              </select>
            </div>
            <button className={styles.btnPrimary} onClick={createAsset} disabled={creating || !newName.trim()}>
              {creating ? "Creating…" : "Create Asset"}
            </button>
          </div>
        )}

        {/* ── STATS TAB ────────────────────────────────────────────── */}
        {tab === "stats" && stats && (
          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{stats.total}</div>
              <div className={styles.statLabel}>Total Assets</div>
            </div>
            {Object.entries(stats.by_type).map(([k, v]) => (
              <div key={k} className={styles.statCard}>
                <div className={styles.statValue}>{v}</div>
                <div className={styles.statLabel}>{k}</div>
              </div>
            ))}
            {Object.entries(stats.by_status).map(([k, v]) => (
              <div key={k} className={styles.statCard}>
                <div className={styles.statValue}>{v}</div>
                <div className={styles.statLabel}>{k}</div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}