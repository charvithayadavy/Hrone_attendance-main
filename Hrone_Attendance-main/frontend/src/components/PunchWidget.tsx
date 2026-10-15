import React, { useState, useEffect } from 'react';
import { LogIn, LogOut, CheckCircle2, AlertCircle, Clock, Calendar, ShieldCheck } from 'lucide-react';
import { api } from '../api/client';
import type { Employee, AttendanceLog } from '../types';

export const PunchWidget: React.FC = () => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selectedEmpCode, setSelectedEmpCode] = useState<string>('');
  const [status, setStatus] = useState<'PRESENT' | 'WFH' | 'ON_DUTY'>('PRESENT');
  
  // Optional custom timestamp override for rule testing
  const [useCustomTime, setUseCustomTime] = useState(false);
  const [customDateTime, setCustomDateTime] = useState('');

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AttendanceLog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    api.listEmployees('', 1, 100).then((res) => {
      setEmployees(res.items);
      if (res.items.length > 0) {
        setSelectedEmpCode(res.items[0].emp_code);
      }
    }).catch(() => {});
  }, []);

  const getPunchedAtEpoch = (): number | undefined => {
    if (!useCustomTime || !customDateTime) return undefined;
    const d = new Date(customDateTime);
    return d.getTime();
  };

  const handlePunchIn = async () => {
    if (!selectedEmpCode) {
      setError('Please select an employee code');
      return;
    }
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    setResult(null);

    try {
      const res = await api.punchIn({
        emp_code: selectedEmpCode,
        status,
        punched_at: getPunchedAtEpoch(),
      });
      setResult(res);
      setSuccessMsg(`Successfully Punched In as ${status} on Date: ${res.date}`);
    } catch (err: any) {
      setError(err.message || 'Punch In failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePunchOut = async () => {
    if (!selectedEmpCode) {
      setError('Please select an employee code');
      return;
    }
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    setResult(null);

    try {
      const res = await api.punchOut({
        emp_code: selectedEmpCode,
        punched_at: getPunchedAtEpoch(),
      });
      setResult(res);
      setSuccessMsg(`Successfully Punched Out! Total Work Hours: ${res.work_hours} hrs`);
    } catch (err: any) {
      setError(err.message || 'Punch Out failed');
    } finally {
      setLoading(false);
    }
  };

  const selectedEmp = employees.find((e) => e.emp_code === selectedEmpCode);

  return (
    <div className="main-content">
      <div className="page-header">
        <div>
          <h1 className="page-title">Attendance Punch Portal</h1>
          <p className="page-subtitle">Atomic punch-in/out terminal supporting IST date assignment & grace period rules</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '2rem' }}>
        {/* Punch Action Card */}
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Clock size={22} style={{ color: 'var(--accent-primary)' }} />
            Timecard Terminal
          </h2>

          <div className="form-group">
            <label className="form-label">Select Employee</label>
            <select
              className="form-select"
              value={selectedEmpCode}
              onChange={(e) => setSelectedEmpCode(e.target.value)}
            >
              {employees.length === 0 && <option value="">No employees found</option>}
              {employees.map((emp) => (
                <option key={emp.emp_code} value={emp.emp_code}>
                  {emp.emp_code} - {emp.name} ({emp.department})
                </option>
              ))}
            </select>
          </div>

          {selectedEmp && (
            <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '0.85rem', borderRadius: 'var(--radius-sm)', marginBottom: '1.25rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              <div>Shift Timing: <strong style={{ color: 'var(--text-primary)' }}>{selectedEmp.shift_start} - {selectedEmp.shift_end}</strong></div>
              <div>Grace Period: <strong style={{ color: '#34d399' }}>10 Minutes (Rule R2)</strong></div>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Punch Status (For Punch In)</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
              {(['PRESENT', 'WFH', 'ON_DUTY'] as const).map((st) => (
                <button
                  key={st}
                  type="button"
                  className={`btn ${status === st ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                  onClick={() => setStatus(st)}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>

          {/* Time Override Toggle */}
          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}>
              <input
                type="checkbox"
                checked={useCustomTime}
                onChange={(e) => setUseCustomTime(e.target.checked)}
              />
              <span>Override timestamp (For testing late/OT/overnight rules)</span>
            </label>
          </div>

          {useCustomTime && (
            <div className="form-group">
              <label className="form-label">Custom Timestamp (Local Time)</label>
              <input
                type="datetime-local"
                className="form-input"
                value={customDateTime}
                onChange={(e) => setCustomDateTime(e.target.value)}
              />
            </div>
          )}

          {error && (
            <div className="alert-box alert-error" style={{ marginBottom: '1rem' }}>
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="alert-box alert-success" style={{ marginBottom: '1rem' }}>
              <CheckCircle2 size={18} />
              <span>{successMsg}</span>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1.5rem' }}>
            <button className="btn btn-emerald" onClick={handlePunchIn} disabled={loading}>
              <LogIn size={18} />
              Punch In
            </button>
            <button className="btn btn-rose" onClick={handlePunchOut} disabled={loading}>
              <LogOut size={18} />
              Punch Out
            </button>
          </div>
        </div>

        {/* Live Metrics Display */}
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldCheck size={22} style={{ color: 'var(--status-present)' }} />
            Punch Verification & Metrics
          </h2>

          {result ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="stat-card glass-panel" style={{ background: 'rgba(99, 102, 241, 0.08)' }}>
                <div className="stat-header">
                  <span>Attendance Date (IST)</span>
                  <Calendar size={16} />
                </div>
                <div className="stat-value" style={{ color: 'var(--accent-primary)' }}>
                  {result.date}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="stat-card glass-panel">
                  <div className="stat-header">Status</div>
                  <div style={{ marginTop: '0.25rem' }}>
                    <span className={`badge badge-${result.status.toLowerCase()}`}>
                      {result.status}
                    </span>
                  </div>
                </div>

                <div className="stat-card glass-panel">
                  <div className="stat-header">Half Day (Rule R5)</div>
                  <div style={{ fontWeight: 700, marginTop: '0.25rem', color: result.half_day ? '#fb7185' : '#34d399' }}>
                    {result.half_day ? 'YES (< 4.50 hrs)' : 'NO (Full Day)'}
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
                <div className="stat-card glass-panel">
                  <div className="stat-header">Work Hours</div>
                  <div className="stat-value" style={{ fontSize: '1.4rem' }}>
                    {result.work_hours !== null ? `${result.work_hours} h` : 'Open'}
                  </div>
                </div>

                <div className="stat-card glass-panel">
                  <div className="stat-header">Late Mins</div>
                  <div className="stat-value" style={{ fontSize: '1.4rem', color: result.late_minutes > 0 ? '#fb7185' : 'inherit' }}>
                    {result.late_minutes} m
                  </div>
                </div>

                <div className="stat-card glass-panel">
                  <div className="stat-header">Overtime</div>
                  <div className="stat-value" style={{ fontSize: '1.4rem', color: result.overtime_minutes > 0 ? '#67e8f9' : 'inherit' }}>
                    {result.overtime_minutes} m
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
              Perform a punch-in or punch-out to view calculated metrics, IST date resolution, and audit logs.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
