import React, { useState, useEffect } from 'react';
import { X, Database, AlertCircle } from 'lucide-react';
import { api } from '../api/client';
import type { ExplainResponse } from '../types';

interface ExplainModalProps {
  endpoint: string;
  params: Record<string, string>;
  onClose: () => void;
}

export const ExplainModal: React.FC<ExplainModalProps> = ({ endpoint, params, onClose }) => {
  const [data, setData] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.getExplain(endpoint, params)
      .then((res) => setData(res))
      .catch((err: any) => setError(err.message || 'Failed to fetch explain execution stats'))
      .finally(() => setLoading(false));
  }, [endpoint]);

  return (
    <div className="modal-overlay">
      <div className="modal-card" style={{ maxWidth: '800px' }}>
        <div className="modal-header">
          <h2 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Database size={22} style={{ color: 'var(--accent-primary)' }} />
            MongoDB Explain Execution Stats ({endpoint})
          </h2>
          <button className="close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>Running MongoDB aggregation pipeline explain...</div>
        ) : error ? (
          <div className="alert-box alert-error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        ) : data ? (
          <div>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', fontSize: '0.85rem' }}>
              <span className="badge badge-wfh">Target Collection: {data.collection}</span>
              <span className="badge badge-present">Verbosity: executionStats</span>
            </div>

            <pre className="code-block">
              {JSON.stringify(data.explain, null, 2)}
            </pre>
          </div>
        ) : null}
      </div>
    </div>
  );
};
