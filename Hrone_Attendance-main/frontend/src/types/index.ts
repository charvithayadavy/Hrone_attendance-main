export interface Employee {
  emp_code: string;
  name: string;
  email: string;
  department: string;
  shift_start: string;
  shift_end: string;
  joined_on: string;
  created_at?: number | null;
}

export interface EmployeeCreatePayload {
  emp_code: string;
  name: string;
  email: string;
  department: string;
  shift_start: string;
  shift_end: string;
  joined_on: string;
}

export interface EmployeeListResponse {
  items: Employee[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditChangeDetail {
  from: any;
  to: any;
}

export interface AuditHistoryEntry {
  at: number | null;
  by: string;
  reason: string;
  changes: Record<string, AuditChangeDetail>;
}

export interface AttendanceLog {
  emp_code: string;
  date: string;
  status: 'PRESENT' | 'ABSENT' | 'LEAVE' | 'WFH' | 'ON_DUTY';
  punch_in: number | null;
  punch_out: number | null;
  work_hours: number | null;
  late_minutes: number;
  overtime_minutes: number;
  half_day: boolean;
  history: AuditHistoryEntry[];
}

export interface AttendanceListResponse {
  items: AttendanceLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface PunchInPayload {
  emp_code: string;
  punched_at?: number;
  status?: string;
}

export interface PunchOutPayload {
  emp_code: string;
  punched_at?: number;
}

export interface RegularizePayload {
  status?: string;
  punch_in?: number;
  punch_out?: number;
  reason: string;
  regularized_by: string;
}

export interface EmployeeMonthlyAnalytics {
  emp_code: string;
  month: string;
  working_days: number;
  present_days: number;
  leave_days: number;
  late_count: number;
  total_late_minutes: number;
  total_overtime_minutes: number;
  attendance_pct: number | null;
}

export interface DepartmentSummaryItem {
  department: string;
  headcount: number;
  present_days: number;
  avg_work_hours: number | null;
  late_count: number;
  total_late_minutes: number;
  leave_count: number;
  on_duty_count: number;
}

export interface DepartmentSummaryResponse {
  month: string;
  items: DepartmentSummaryItem[];
}

export interface LateLeaderboardItem {
  rank: number;
  emp_code: string;
  name: string;
  department: string;
  total_late_minutes: number;
  late_count: number;
}

export interface LateLeaderboardResponse {
  month: string;
  items: LateLeaderboardItem[];
}

export interface DepartmentTrendItem {
  date: string;
  is_working_day: boolean;
  headcount: number;
  present_count: number;
  late_count: number;
  attendance_rate: number | null;
  moving_avg_7d: number | null;
}

export interface DepartmentTrendResponse {
  department: string;
  items: DepartmentTrendItem[];
}

export interface ExplainResponse {
  endpoint: string;
  collection: string;
  explain: any;
}
