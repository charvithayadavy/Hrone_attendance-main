import { useState } from 'react';
import { Navbar } from './components/Navbar';
import { EmployeeList } from './components/EmployeeList';
import { PunchWidget } from './components/PunchWidget';
import { AttendanceList } from './components/AttendanceList';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';

export function App() {
  const [activeTab, setActiveTab] = useState<'employees' | 'punch' | 'attendance' | 'analytics'>('employees');
  const [selectedEmpCode, setSelectedEmpCode] = useState<string>('');

  const handleSelectEmployee = (empCode: string) => {
    setSelectedEmpCode(empCode);
    setActiveTab('attendance');
  };

  return (
    <div className="app-container">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {activeTab === 'employees' && <EmployeeList onSelectEmployee={handleSelectEmployee} />}
      {activeTab === 'punch' && <PunchWidget />}
      {activeTab === 'attendance' && <AttendanceList initialEmpCode={selectedEmpCode} />}
      {activeTab === 'analytics' && <AnalyticsDashboard />}
    </div>
  );
}

export default App;
