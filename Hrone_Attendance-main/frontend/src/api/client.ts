import type {
  Employee,
  EmployeeCreatePayload,
  EmployeeListResponse,
  AttendanceLog,
  AttendanceListResponse,
  PunchInPayload,
  PunchOutPayload,
  RegularizePayload,
  EmployeeMonthlyAnalytics,
  DepartmentSummaryResponse,
  LateLeaderboardResponse,
  DepartmentTrendResponse,
  ExplainResponse,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) {
        if (Array.isArray(body.detail)) {
          errorMsg = body.detail.map((err: any) => `${err.loc?.join('.')} ${err.msg}`).join(', ');
        } else {
          errorMsg = body.detail;
        }
      }
    } catch {
      errorMsg = res.statusText || errorMsg;
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

export const api = {
  // Health
  checkHealth: async (): Promise<{ status: string }> => {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse(res);
  },

  // Employees
  createEmployee: async (payload: EmployeeCreatePayload): Promise<Employee> => {
    const res = await fetch(`${API_BASE}/employees`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<Employee>(res);
  },

  listEmployees: async (department?: string, page = 1, pageSize = 20): Promise<EmployeeListResponse> => {
    const params = new URLSearchParams({ page: page.toString(), page_size: pageSize.toString() });
    if (department) params.append('department', department);
    const res = await fetch(`${API_BASE}/employees?${params.toString()}`);
    return handleResponse<EmployeeListResponse>(res);
  },

  // Attendance
  punchIn: async (payload: PunchInPayload): Promise<AttendanceLog> => {
    const res = await fetch(`${API_BASE}/attendance/punch-in`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<AttendanceLog>(res);
  },

  punchOut: async (payload: PunchOutPayload): Promise<AttendanceLog> => {
    const res = await fetch(`${API_BASE}/attendance/punch-out`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<AttendanceLog>(res);
  },

  listAttendance: async (
    filters: { emp_code?: string; date_from?: string; date_to?: string; status?: string; page?: number; page_size?: number } = {}
  ): Promise<AttendanceListResponse> => {
    const params = new URLSearchParams();
    if (filters.emp_code) params.append('emp_code', filters.emp_code);
    if (filters.date_from) params.append('date_from', filters.date_from);
    if (filters.date_to) params.append('date_to', filters.date_to);
    if (filters.status) params.append('status', filters.status);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());

    const res = await fetch(`${API_BASE}/attendance?${params.toString()}`);
    return handleResponse<AttendanceListResponse>(res);
  },

  regularize: async (empCode: string, date: string, payload: RegularizePayload): Promise<AttendanceLog> => {
    const res = await fetch(`${API_BASE}/attendance/${encodeURIComponent(empCode)}/${encodeURIComponent(date)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<AttendanceLog>(res);
  },

  // Analytics
  getEmployeeMonthly: async (empCode: string, month: string): Promise<EmployeeMonthlyAnalytics> => {
    const params = new URLSearchParams({ month });
    const res = await fetch(`${API_BASE}/analytics/employees/${encodeURIComponent(empCode)}/monthly?${params.toString()}`);
    return handleResponse<EmployeeMonthlyAnalytics>(res);
  },

  getDepartmentSummary: async (month: string, department?: string): Promise<DepartmentSummaryResponse> => {
    const params = new URLSearchParams({ month });
    if (department) params.append('department', department);
    const res = await fetch(`${API_BASE}/analytics/departments/summary?${params.toString()}`);
    return handleResponse<DepartmentSummaryResponse>(res);
  },

  getLateLeaderboard: async (month: string, limit = 10, department?: string): Promise<LateLeaderboardResponse> => {
    const params = new URLSearchParams({ month, limit: limit.toString() });
    if (department) params.append('department', department);
    const res = await fetch(`${API_BASE}/analytics/leaderboard/late?${params.toString()}`);
    return handleResponse<LateLeaderboardResponse>(res);
  },

  getDepartmentTrend: async (department: string, fromDate: string, toDate: string): Promise<DepartmentTrendResponse> => {
    const params = new URLSearchParams({ from: fromDate, to: toDate });
    const res = await fetch(`${API_BASE}/analytics/departments/${encodeURIComponent(department)}/trend?${params.toString()}`);
    return handleResponse<DepartmentTrendResponse>(res);
  },

  // Explain Diagnostics
  getExplain: async (endpoint: string, paramsObj: Record<string, string>): Promise<ExplainResponse> => {
    const params = new URLSearchParams(paramsObj);
    const res = await fetch(`${API_BASE}/admin/explain/${encodeURIComponent(endpoint)}?${params.toString()}`);
    return handleResponse<ExplainResponse>(res);
  },
};
