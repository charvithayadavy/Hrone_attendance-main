import React, { useState, useEffect } from 'react';
import { History, Edit3, ChevronLeft, ChevronRight, X, AlertCircle } from 'lucide-react';
import { api } from '../api/client';
import type { AttendanceLog, RegularizePayload } from '../types';

interface AttendanceListProps {
  initialEmpCode?: string;
}

export const AttendanceList: React.FC<AttendanceListProps> = ({ initialEmpCode = '' }) => {
  const [logs, setLogs] = useState<AttendanceLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [empCodeFilter, setEmpCodeFilter] = useState(initialEmpCode);
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Regularize Modal State
  const [selectedRecord, setSelectedRecord] = useState<AttendanceLog | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [regStatus, setRegStatus] = useState<string>('PRESENT');
  const [regPunchIn, setRegPunchIn] = useState<string>('');
  const [regPunchOut, setRegPunchOut] = useState<string>('');
  const [regReason, setRegReason] = useState<string>('System correction for forgotten punch');
  const [regBy, setRegBy] = useState<string>('HR Admin');
  const [regError, setRegError] = useState<string | null>(null);
  const [regSubmitting, setRegSubmitting] = useState(false);

  // History Viewer Modal
  const [historyRecord, setHistoryRecord] = useState<AttendanceLog | null>(null);

  const fetchAttendance = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listAttendance({
        emp_code: empCodeFilter || undefined,
        status: statusFilter || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page,
        page_size: 10,
      });
      setLogs(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch attendance logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAttendance();
  }, [page, empCodeFilter, statusFilter, dateFrom, dateTo]);

  const handleOpenRegularize = (record: AttendanceLog) => {
    setSelectedRecord(record);
    setRegStatus(record.status);
    setRegPunchIn(record.punch_in ? new Date(record.punch_in).toISOString().slice(0, 16) : '');
    setRegPunchOut(record.punch_out ? new Date(record.punch_out).toISOString().slice(0, 16) : '');
    setRegReason('Manager approved attendance adjustment');
    setRegBy('HR Admin');
    setRegError(null);
    setShowModal(true);
  };

  const handleRegularizeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRecord) return;
    setRegError(null);
    setRegSubmitting(true);

    const payload: RegularizePayload = {
      status: regStatus,
      reason: regReason,
      regularized_by: regBy,
    };

    if (regStatus !== 'ABSENT' && regStatus !== 'LEAVE') {
      if (regPunchIn) payload.punch_in = new Date(regPunchIn).getTime();
      if (regPunchOut) payload.punch_out = new Date(regPunchOut).getTime();
    }

    try {
      await api.regularize(selectedRecord.emp_code, selectedRecord.date, payload);
      setShowModal(false);
      fetchAttendance();
    } catch (err: any) {
      setRegError(err.message || 'Regularization failed');
    } finally {
      setRegSubmitting(false);
    }
  };

  const formatEpochTime = (ms: number | null) => {
    if (!ms) return '-';
    const d = new Date(ms);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className="main-content">
      <div className="page-header">
        <div>
          <h1 className="page-title">Attendance Log Records</h1>
          <p className="page-subtitle">Historical punch records, metric calculations, and audit history</p>
        </div>
      </div>

      {error && (
        <div className="alert-box alert-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Emp Code</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. EMP1001"
              value={empCodeFilter}
              onChange={(e) => {
                setEmpCodeFilter(e.target.value);
                setPage(1);
              }}
            />
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Status Filter</label>
            <select
              className="form-select"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Statuses</option>
              <option value="PRESENT">PRESENT</option>
              <option value="WFH">WFH</option>
              <option value="ON_DUTY">ON_DUTY</option>
              <option value="ABSENT">ABSENT</option>
              <option value="LEAVE">LEAVE</option>
            </select>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Date From</label>
            <input
              type="date"
              className="form-input"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
            />
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Date To</label>
            <input
              type="date"
              className="form-input"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setPage(1);
              }}
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="glass-panel">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Emp Code</th>
                <th>Date</th>
                <th>Status</th>
                <th>Punch In</th>
                <th>Punch Out</th>
                <th>Work Hours</th>
                <th>Late / OT</th>
                <th>Audit History</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '2rem' }}>
                    Loading attendance records...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                    No attendance records found matching filters.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={`${log.emp_code}-${log.date}`}>
                    <td style={{ fontWeight: '700', color: 'var(--accent-primary)' }}>{log.emp_code}</td>
                    <td style={{ fontWeight: '600' }}>{log.date}</td>
                    <td>
                      <span className={`badge badge-${log.status.toLowerCase()}`}>
                        {log.status}
                      </span>
                      {log.half_day && <span className="badge badge-late" style={{ marginLeft: '0.35rem' }}>Half Day</span>}
                    </td>
                    <td>{formatEpochTime(log.punch_in)}</td>
                    <td>{formatEpochTime(log.punch_out)}</td>
                    <td style={{ fontWeight: 700 }}>
                      {log.work_hours !== null ? `${log.work_hours} hrs` : '-'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.35rem' }}>
                        {log.late_minutes > 0 && <span className="badge badge-late">+{log.late_minutes}m Late</span>}
                        {log.overtime_minutes > 0 && <span className="badge badge-ot">+{log.overtime_minutes}m OT</span>}
                        {log.late_minutes === 0 && log.overtime_minutes === 0 && <span style={{ color: 'var(--text-muted)' }}>On Time</span>}
                      </div>
                    </td>
                    <td>
                      {log.history && log.history.length > 0 ? (
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => setHistoryRecord(log)}
                        >
                          <History size={14} /> {log.history.length} audit entry
                        </button>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>None</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => handleOpenRegularize(log)}
                      >
                        <Edit3 size={14} /> Regularize
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="pagination" style={{ padding: '1rem 1.5rem' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Showing {logs.length > 0 ? (page - 1) * 10 + 1 : 0} to{' '}
            {Math.min(page * 10, total)} of {total} records
          </span>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              className="btn btn-secondary btn-sm"
              disabled={page === 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft size={16} /> Prev
            </button>
            <button
              className="btn btn-secondary btn-sm"
              disabled={page * 10 >= total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Regularization Modal */}
      {showModal && selectedRecord && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h2 className="modal-title">Regularize Attendance ({selectedRecord.emp_code} - {selectedRecord.date})</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>
                <X size={20} />
              </button>
            </div>

            {regError && (
              <div className="alert-box alert-error" style={{ marginBottom: '1rem' }}>
                <AlertCircle size={16} />
                <span>{regError}</span>
              </div>
            )}

            <form onSubmit={handleRegularizeSubmit}>
              <div className="form-group">
                <label className="form-label">Status</label>
                <select
                  className="form-select"
                  value={regStatus}
                  onChange={(e) => setRegStatus(e.target.value)}
                >
                  <option value="PRESENT">PRESENT</option>
                  <option value="WFH">WFH</option>
                  <option value="ON_DUTY">ON_DUTY</option>
                  <option value="ABSENT">ABSENT</option>
                  <option value="LEAVE">LEAVE</option>
                </select>
              </div>

              {regStatus !== 'ABSENT' && regStatus !== 'LEAVE' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">Punch In (UTC/Local Time)</label>
                    <input
                      type="datetime-local"
                      className="form-input"
                      value={regPunchIn}
                      onChange={(e) => setRegPunchIn(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Punch Out (UTC/Local Time)</label>
                    <input
                      type="datetime-local"
                      className="form-input"
                      value={regPunchOut}
                      onChange={(e) => setRegPunchOut(e.target.value)}
                    />
                  </div>
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Audit Reason (Required)</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  minLength={5}
                  maxLength={200}
                  placeholder="Reason for attendance modification"
                  value={regReason}
                  onChange={(e) => setRegReason(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Regularized By</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  placeholder="Manager / HR Name"
                  value={regBy}
                  onChange={(e) => setRegBy(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={regSubmitting}>
                  {regSubmitting ? 'Updating...' : 'Save Correction & Audit Log'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* History Modal */}
      {historyRecord && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h2 className="modal-title">Immutable Audit Trail ({historyRecord.emp_code} - {historyRecord.date})</h2>
              <button className="close-btn" onClick={() => setHistoryRecord(null)}>
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {historyRecord.history.map((h, idx) => (
                <div key={idx} className="glass-panel" style={{ padding: '1rem', background: 'rgba(255, 255, 255, 0.03)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                    <strong style={{ color: 'var(--accent-primary)' }}>By: {h.by}</strong>
                    <span style={{ color: 'var(--text-muted)' }}>
                      {h.at ? new Date(h.at).toLocaleString() : 'N/A'}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.875rem', marginBottom: '0.75rem' }}>
                    <strong>Reason:</strong> {h.reason}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    <strong>Changes:</strong>
                    <pre style={{ background: '#020617', padding: '0.5rem', borderRadius: '4px', marginTop: '0.25rem', overflowX: 'auto' }}>
                      {JSON.stringify(h.changes, null, 2)}
                    </pre>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
