import React, { useEffect, useState } from 'react';
import { Users, Clock, CalendarCheck, BarChart3, Activity } from 'lucide-react';
import { api } from '../api/client';

interface NavbarProps {
  activeTab: 'employees' | 'punch' | 'attendance' | 'analytics';
  setActiveTab: (tab: 'employees' | 'punch' | 'attendance' | 'analytics') => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        await api.checkHealth();
        setIsOnline(true);
      } catch {
        setIsOnline(false);
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="navbar">
      <div className="brand-logo">
        <Activity size={28} />
        <span>HROne Analytics</span>
      </div>

      <nav className="nav-tabs">
        <button
          className={`nav-tab-btn ${activeTab === 'employees' ? 'active' : ''}`}
          onClick={() => setActiveTab('employees')}
        >
          <Users size={16} />
          Employees
        </button>
        <button
          className={`nav-tab-btn ${activeTab === 'punch' ? 'active' : ''}`}
          onClick={() => setActiveTab('punch')}
        >
          <Clock size={16} />
          Punch Portal
        </button>
        <button
          className={`nav-tab-btn ${activeTab === 'attendance' ? 'active' : ''}`}
          onClick={() => setActiveTab('attendance')}
        >
          <CalendarCheck size={16} />
          Attendance Logs
        </button>
        <button
          className={`nav-tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          <BarChart3 size={16} />
          Analytics & Explain
        </button>
      </nav>

      <div className="system-status">
        <span className={`status-dot ${isOnline === false ? 'offline' : ''}`} />
        <span>{isOnline === null ? 'Connecting...' : isOnline ? 'Backend API Ready' : 'API Offline'}</span>
      </div>
    </header>
  );
};
