import React, { useState, useEffect } from 'react';
import { UserPlus, Search, ChevronLeft, ChevronRight, X, AlertCircle } from 'lucide-react';
import { api } from '../api/client';
import type { Employee, EmployeeCreatePayload } from '../types';

interface EmployeeListProps {
  onSelectEmployee?: (empCode: string) => void;
}

export const EmployeeList: React.FC<EmployeeListProps> = ({ onSelectEmployee }) => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [department, setDepartment] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState<EmployeeCreatePayload>({
    emp_code: 'EMP1001',
    name: '',
    email: '',
    department: 'Engineering',
    shift_start: '09:30',
    shift_end: '18:30',
    joined_on: new Date().toISOString().split('T')[0],
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchEmployees = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listEmployees(department || undefined, page, 10);
      setEmployees(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch employees');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployees();
  }, [page, department]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await api.createEmployee(formData);
      setShowModal(false);
      fetchEmployees();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create employee');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="main-content">
      <div className="page-header">
        <div>
          <h1 className="page-title">Employee Directory</h1>
          <p className="page-subtitle">Manage organization staff, shift parameters, and departmental records</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <UserPlus size={18} />
          Add Employee
        </button>
      </div>

      {error && (
        <div className="alert-box alert-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="glass-panel" style={{ padding: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1 }}>
          <Search size={18} style={{ color: 'var(--text-secondary)' }} />
          <input
            type="text"
            className="form-input"
            placeholder="Filter by Department (e.g. Engineering, Sales)..."
            value={department}
            onChange={(e) => {
              setDepartment(e.target.value);
              setPage(1);
            }}
            style={{ width: '100%' }}
          />
        </div>
      </div>

      {/* Employee Table */}
      <div className="glass-panel">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Emp Code</th>
                <th>Full Name</th>
                <th>Email</th>
                <th>Department</th>
                <th>Shift Schedule</th>
                <th>Joined On</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2rem' }}>
                    Loading employee database...
                  </td>
                </tr>
              ) : employees.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                    No employees found matching filter criteria.
                  </td>
                </tr>
              ) : (
                employees.map((emp) => (
                  <tr key={emp.emp_code}>
                    <td style={{ fontWeight: '700', color: 'var(--accent-primary)' }}>{emp.emp_code}</td>
                    <td style={{ fontWeight: '600' }}>{emp.name}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{emp.email}</td>
                    <td>
                      <span className="badge badge-wfh">{emp.department}</span>
                    </td>
                    <td style={{ fontFamily: 'monospace' }}>
                      {emp.shift_start} - {emp.shift_end}
                    </td>
                    <td>{emp.joined_on}</td>
                    <td>
                      {onSelectEmployee && (
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => onSelectEmployee(emp.emp_code)}
                        >
                          View Logs
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="pagination" style={{ padding: '1rem 1.5rem' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Showing {employees.length > 0 ? (page - 1) * 10 + 1 : 0} to{' '}
            {Math.min(page * 10, total)} of {total} entries
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

      {/* Add Employee Modal */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h2 className="modal-title">Add New Employee</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>
                <X size={20} />
              </button>
            </div>

            {formError && (
              <div className="alert-box alert-error" style={{ marginBottom: '1rem' }}>
                <AlertCircle size={16} />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit}>
              <div className="form-group">
                <label className="form-label">Employee Code (e.g. EMP1001)</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  pattern="^EMP\d{4,6}$"
                  placeholder="EMP1001"
                  value={formData.emp_code}
                  onChange={(e) => setFormData({ ...formData, emp_code: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  placeholder="John Doe"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Email Address</label>
                <input
                  type="email"
                  className="form-input"
                  required
                  placeholder="john.doe@company.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Department</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  placeholder="Engineering"
                  value={formData.department}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Shift Start (HH:MM)</label>
                  <input
                    type="text"
                    className="form-input"
                    required
                    pattern="^([01]\d|2[0-3]):[0-5]\d$"
                    value={formData.shift_start}
                    onChange={(e) => setFormData({ ...formData, shift_start: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Shift End (HH:MM)</label>
                  <input
                    type="text"
                    className="form-input"
                    required
                    pattern="^([01]\d|2[0-3]):[0-5]\d$"
                    value={formData.shift_end}
                    onChange={(e) => setFormData({ ...formData, shift_end: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Joined On (YYYY-MM-DD)</label>
                <input
                  type="date"
                  className="form-input"
                  required
                  value={formData.joined_on}
                  onChange={(e) => setFormData({ ...formData, joined_on: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Saving...' : 'Create Employee'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
