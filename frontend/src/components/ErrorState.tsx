import { AlertCircle } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message: string;
}

export function ErrorState({ title = 'Error Loading Data', message }: ErrorStateProps) {
  return (
    <div style={{
      padding: 24,
      background: 'var(--red-50)',
      border: '1px solid var(--red-200)',
      borderRadius: 8,
      display: 'flex',
      gap: 12,
      alignItems: 'flex-start'
    }}>
      <AlertCircle size={20} style={{ color: 'var(--red-700)', flexShrink: 0, marginTop: 2 }} />
      <div>
        <p style={{ fontWeight: 500, color: 'var(--red-700)', marginBottom: 4 }}>{title}</p>
        <p style={{ color: 'var(--red-700)', fontSize: 14 }}>{message}</p>
      </div>
    </div>
  );
}

export default ErrorState;
