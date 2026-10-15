import React, { useState, useEffect } from 'react';
import { TrendingUp, Trophy, Building2, User, Database, AlertCircle } from 'lucide-react';
import { api } from '../api/client';
import type {
  EmployeeMonthlyAnalytics,
  DepartmentSummaryItem,
  LateLeaderboardItem,
  DepartmentTrendItem,
} from '../types';
import { ExplainModal } from './ExplainModal';

export const AnalyticsDashboard: React.FC = () => {
  const currentMonth = new Date().toISOString().slice(0, 7); // YYYY-MM
  const todayStr = new Date().toISOString().slice(0, 10);
  const monthAgoStr = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10);

  // Tab selections within Analytics
  const [analyticsSubTab, setAnalyticsSubTab] = useState<'dept' | 'emp' | 'leaderboard' | 'trend'>('dept');

  // Explain modal state
  const [explainEndpoint, setExplainEndpoint] = useState<string | null>(null);
  const [explainParams, setExplainParams] = useState<Record<string, string>>({});

  // 1. Department Summary state
  const [deptMonth, setDeptMonth] = useState(currentMonth);
  const [deptSummary, setDeptSummary] = useState<DepartmentSummaryItem[]>([]);
  const [deptLoading, setDeptLoading] = useState(false);
  const [deptError, setDeptError] = useState<string | null>(null);

  // 2. Employee Monthly state
  const [empCodeInput, setEmpCodeInput] = useState('EMP1001');
  const [empMonthInput, setEmpMonthInput] = useState(currentMonth);
  const [empAnalytics, setEmpAnalytics] = useState<EmployeeMonthlyAnalytics | null>(null);
  const [empLoading, setEmpLoading] = useState(false);
  const [empError, setEmpError] = useState<string | null>(null);

  // 3. Late Leaderboard state
  const [leaderMonth, setLeaderMonth] = useState(currentMonth);
  const [leaderLimit, setLeaderLimit] = useState(10);
  const [leaderboard, setLeaderboard] = useState<LateLeaderboardItem[]>([]);
  const [leaderLoading, setLeaderLoading] = useState(false);
  const [leaderError, setLeaderError] = useState<string | null>(null);

  // 4. Department Trend state
  const [trendDept, setTrendDept] = useState('Engineering');
  const [trendFrom, setTrendFrom] = useState(monthAgoStr);
  const [trendTo, setTrendTo] = useState(todayStr);
  const [trendItems, setTrendItems] = useState<DepartmentTrendItem[]>([]);
  const [trendLoading, setTrendLoading] = useState(false);
  const [trendError, setTrendError] = useState<string | null>(null);

  // Fetch Dept Summary
  const fetchDeptSummary = async () => {
    setDeptLoading(true);
    setDeptError(null);
    try {
      const res = await api.getDepartmentSummary(deptMonth);
      setDeptSummary(res.items);
    } catch (err: any) {
      setDeptError(err.message || 'Failed to fetch department summary');
    } finally {
      setDeptLoading(false);
    }
  };

  // Fetch Emp Monthly
  const fetchEmpMonthly = async () => {
    if (!empCodeInput) return;
    setEmpLoading(true);
    setEmpError(null);
    try {
      const res = await api.getEmployeeMonthly(empCodeInput, empMonthInput);
      setEmpAnalytics(res);
    } catch (err: any) {
      setEmpError(err.message || 'Failed to fetch employee monthly analytics');
    } finally {
      setEmpLoading(false);
    }
  };

  // Fetch Leaderboard
  const fetchLeaderboard = async () => {
    setLeaderLoading(true);
    setLeaderError(null);
    try {
      const res = await api.getLateLeaderboard(leaderMonth, leaderLimit);
      setLeaderboard(res.items);
    } catch (err: any) {
      setLeaderError(err.message || 'Failed to fetch leaderboard');
    } finally {
      setLeaderLoading(false);
    }
  };

  // Fetch Trend
  const fetchTrend = async () => {
    if (!trendDept) return;
    setTrendLoading(true);
    setTrendError(null);
    try {
      const res = await api.getDepartmentTrend(trendDept, trendFrom, trendTo);
      setTrendItems(res.items);
    } catch (err: any) {
      setTrendError(err.message || 'Failed to fetch trend data');
    } finally {
      setTrendLoading(false);
    }
  };

  useEffect(() => {
    if (analyticsSubTab === 'dept') fetchDeptSummary();
    if (analyticsSubTab === 'emp') fetchEmpMonthly();
    if (analyticsSubTab === 'leaderboard') fetchLeaderboard();
    if (analyticsSubTab === 'trend') fetchTrend();
  }, [analyticsSubTab]);

  return (
    <div className="main-content">
      <div className="page-header">
        <div>
          <h1 className="page-title">Native Aggregation Analytics & Explain</h1>
          <p className="page-subtitle">Real-time MongoDB aggregation pipelines for headcount, competition ranking, moving averages, and query diagnostics</p>
        </div>
      </div>

      {/* Sub Tab Navigation */}
      <div style={{ display: 'flex', gap: '0.75rem', borderBottom: '1px solid var(--border-card)', paddingBottom: '0.75rem' }}>
        <button
          className={`btn ${analyticsSubTab === 'dept' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
          onClick={() => setAnalyticsSubTab('dept')}
        >
          <Building2 size={16} /> Department Summary
        </button>
        <button
          className={`btn ${analyticsSubTab === 'emp' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
          onClick={() => setAnalyticsSubTab('emp')}
        >
          <User size={16} /> Employee Monthly Stats
        </button>
        <button
          className={`btn ${analyticsSubTab === 'leaderboard' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
          onClick={() => setAnalyticsSubTab('leaderboard')}
        >
          <Trophy size={16} /> Late Leaderboard (R8)
        </button>
        <button
          className={`btn ${analyticsSubTab === 'trend' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
          onClick={() => setAnalyticsSubTab('trend')}
        >
          <TrendingUp size={16} /> Department Trends & 7d MA
        </button>
      </div>

      {/* 1. Department Summary */}
      {analyticsSubTab === 'dept' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Month (YYYY-MM)</label>
                <input
                  type="month"
                  className="form-input"
                  value={deptMonth}
                  onChange={(e) => setDeptMonth(e.target.value)}
                />
              </div>
              <button className="btn btn-primary" onClick={fetchDeptSummary} style={{ marginTop: '1.2rem' }}>
                Load Summary
              </button>
            </div>

            <button
              className="btn btn-secondary"
              onClick={() => {
                setExplainEndpoint('department_summary');
                setExplainParams({ month: deptMonth });
              }}
            >
              <Database size={16} /> Explain Query
            </button>
          </div>

          {deptError && (
            <div className="alert-box alert-error">
              <AlertCircle size={18} />
              <span>{deptError}</span>
            </div>
          )}

          <div className="glass-panel">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Department</th>
                    <th>Headcount (R9)</th>
                    <th>Present Days</th>
                    <th>Avg Work Hours</th>
                    <th>Late Count</th>
                    <th>Total Late Mins</th>
                    <th>Leave Count</th>
                    <th>On Duty Count</th>
                  </tr>
                </thead>
                <tbody>
                  {deptLoading ? (
                    <tr>
                      <td colSpan={8} style={{ textAlign: 'center', padding: '2rem' }}>
                        Executing MongoDB $lookup aggregation pipeline...
                      </td>
                    </tr>
                  ) : deptSummary.length === 0 ? (
                    <tr>
                      <td colSpan={8} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                        No departmental records found for {deptMonth}.
                      </td>
                    </tr>
                  ) : (
                    deptSummary.map((item) => (
                      <tr key={item.department}>
                        <td style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>{item.department}</td>
                        <td style={{ fontWeight: 700 }}>{item.headcount}</td>
                        <td>{item.present_days}</td>
                        <td>{item.avg_work_hours !== null ? `${item.avg_work_hours} hrs` : '-'}</td>
                        <td>
                          {item.late_count > 0 ? (
                            <span className="badge badge-late">{item.late_count}</span>
                          ) : (
                            '0'
                          )}
                        </td>
                        <td>{item.total_late_minutes} mins</td>
                        <td>{item.leave_count}</td>
                        <td>{item.on_duty_count}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 2. Employee Monthly */}
      {analyticsSubTab === 'emp' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Emp Code</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="EMP1001"
                  value={empCodeInput}
                  onChange={(e) => setEmpCodeInput(e.target.value)}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Month</label>
                <input
                  type="month"
                  className="form-input"
                  value={empMonthInput}
                  onChange={(e) => setEmpMonthInput(e.target.value)}
                />
              </div>
              <button className="btn btn-primary" onClick={fetchEmpMonthly} style={{ marginTop: '1.2rem' }}>
                Calculate Stats
              </button>
            </div>

            <button
              className="btn btn-secondary"
              onClick={() => {
                setExplainEndpoint('employee_monthly');
                setExplainParams({ emp_code: empCodeInput, month: empMonthInput });
              }}
            >
              <Database size={16} /> Explain Query
            </button>
          </div>

          {empError && (
            <div className="alert-box alert-error">
              <AlertCircle size={18} />
              <span>{empError}</span>
            </div>
          )}

          {empLoading ? (
            <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>
              Calculating employee monthly attendance metrics...
            </div>
          ) : empAnalytics ? (
            <div className="stats-grid">
              <div className="stat-card glass-panel">
                <div className="stat-header">Working Days (R7)</div>
                <div className="stat-value">{empAnalytics.working_days}</div>
              </div>
              <div className="stat-card glass-panel">
                <div className="stat-header">Present Days</div>
                <div className="stat-value" style={{ color: 'var(--status-present)' }}>
                  {empAnalytics.present_days}
                </div>
              </div>
              <div className="stat-card glass-panel">
                <div className="stat-header">Attendance %</div>
                <div className="stat-value" style={{ color: 'var(--accent-primary)' }}>
                  {empAnalytics.attendance_pct !== null ? `${empAnalytics.attendance_pct}%` : 'N/A'}
                </div>
              </div>
              <div className="stat-card glass-panel">
                <div className="stat-header">Late Incidents</div>
                <div className="stat-value" style={{ color: empAnalytics.late_count > 0 ? '#fb7185' : 'inherit' }}>
                  {empAnalytics.late_count} ({empAnalytics.total_late_minutes}m)
                </div>
              </div>
              <div className="stat-card glass-panel">
                <div className="stat-header">Overtime</div>
                <div className="stat-value" style={{ color: '#67e8f9' }}>
                  {empAnalytics.total_overtime_minutes} mins
                </div>
              </div>
              <div className="stat-card glass-panel">
                <div className="stat-header">Leave Days</div>
                <div className="stat-value">{empAnalytics.leave_days}</div>
              </div>
            </div>
          ) : (
            <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Enter Employee Code and Month to calculate monthly metrics.
            </div>
          )}
        </div>
      )}

      {/* 3. Late Leaderboard */}
      {analyticsSubTab === 'leaderboard' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Month</label>
                <input
                  type="month"
                  className="form-input"
                  value={leaderMonth}
                  onChange={(e) => setLeaderMonth(e.target.value)}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Limit Cutoff</label>
                <input
                  type="number"
                  className="form-input"
                  min={1}
                  max={50}
                  value={leaderLimit}
                  onChange={(e) => setLeaderLimit(parseInt(e.target.value) || 10)}
                />
              </div>
              <button className="btn btn-primary" onClick={fetchLeaderboard} style={{ marginTop: '1.2rem' }}>
                Load Leaderboard
              </button>
            </div>

            <button
              className="btn btn-secondary"
              onClick={() => {
                setExplainEndpoint('late_leaderboard');
                setExplainParams({ month: leaderMonth, limit: leaderLimit.toString() });
              }}
            >
              <Database size={16} /> Explain Query
            </button>
          </div>

          {leaderError && (
            <div className="alert-box alert-error">
              <AlertCircle size={18} />
              <span>{leaderError}</span>
            </div>
          )}

          <div className="glass-panel">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank (R8 Competition)</th>
                    <th>Emp Code</th>
                    <th>Name</th>
                    <th>Department</th>
                    <th>Total Late Minutes</th>
                    <th>Late Incidents</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderLoading ? (
                    <tr>
                      <td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>
                        Executing MongoDB $setWindowFields ranking pipeline...
                      </td>
                    </tr>
                  ) : leaderboard.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                        No late attendance records for {leaderMonth}.
                      </td>
                    </tr>
                  ) : (
                    leaderboard.map((item, idx) => (
                      <tr key={idx}>
                        <td>
                          <span
                            className="badge"
                            style={{
                              background: item.rank === 1 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(255, 255, 255, 0.08)',
                              color: item.rank === 1 ? '#fbbf24' : 'var(--text-primary)',
                              border: item.rank === 1 ? '1px solid #f59e0b' : '1px solid var(--border-card)',
                              fontWeight: 800,
                            }}
                          >
                            #{item.rank}
                          </span>
                        </td>
                        <td style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>{item.emp_code}</td>
                        <td style={{ fontWeight: 600 }}>{item.name}</td>
                        <td>{item.department}</td>
                        <td style={{ color: '#fb7185', fontWeight: 700 }}>{item.total_late_minutes} mins</td>
                        <td>{item.late_count} times</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 4. Department Trend */}
      {analyticsSubTab === 'trend' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Department</label>
                <input
                  type="text"
                  className="form-input"
                  value={trendDept}
                  onChange={(e) => setTrendDept(e.target.value)}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">From Date</label>
                <input
                  type="date"
                  className="form-input"
                  value={trendFrom}
                  onChange={(e) => setTrendFrom(e.target.value)}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">To Date</label>
                <input
                  type="date"
                  className="form-input"
                  value={trendTo}
                  onChange={(e) => setTrendTo(e.target.value)}
                />
              </div>
              <button className="btn btn-primary" onClick={fetchTrend} style={{ marginTop: '1.2rem' }}>
                Generate Trend
              </button>
            </div>

            <button
              className="btn btn-secondary"
              onClick={() => {
                setExplainEndpoint('department_trend');
                setExplainParams({ department: trendDept, from: trendFrom, to: trendTo });
              }}
            >
              <Database size={16} /> Explain Query
            </button>
          </div>

          {trendError && (
            <div className="alert-box alert-error">
              <AlertCircle size={18} />
              <span>{trendError}</span>
            </div>
          )}

          <div className="glass-panel">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Working Day</th>
                    <th>Headcount</th>
                    <th>Present Count</th>
                    <th>Late Count</th>
                    <th>Attendance Rate</th>
                    <th>7-Day Moving Avg</th>
                  </tr>
                </thead>
                <tbody>
                  {trendLoading ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: '2rem' }}>
                        Generating gap-filled trend series and moving average calculation...
                      </td>
                    </tr>
                  ) : trendItems.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                        No trend data available for {trendDept}.
                      </td>
                    </tr>
                  ) : (
                    trendItems.map((item) => (
                      <tr key={item.date}>
                        <td style={{ fontWeight: 600 }}>{item.date}</td>
                        <td>{item.is_working_day ? <span className="badge badge-present">Yes</span> : <span className="badge badge-leave">Weekend</span>}</td>
                        <td>{item.headcount}</td>
                        <td>{item.present_count}</td>
                        <td>{item.late_count}</td>
                        <td style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>
                          {item.attendance_rate !== null ? `${(item.attendance_rate * 100).toFixed(2)}%` : '-'}
                        </td>
                        <td style={{ fontWeight: 700, color: '#38bdf8' }}>
                          {item.moving_avg_7d !== null ? `${(item.moving_avg_7d * 100).toFixed(2)}%` : '-'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Explain Modal */}
      {explainEndpoint && (
        <ExplainModal
          endpoint={explainEndpoint}
          params={explainParams}
          onClose={() => setExplainEndpoint(null)}
        />
      )}
    </div>
  );
};
