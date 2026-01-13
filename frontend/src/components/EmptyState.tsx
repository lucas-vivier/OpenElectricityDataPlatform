import { Info, type LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  message: string;
  icon?: LucideIcon;
}

export function EmptyState({ title, message, icon: Icon = Info }: EmptyStateProps) {
  return (
    <div style={{
      padding: 24,
      background: 'var(--gray-50)',
      border: '1px solid var(--gray-200)',
      borderRadius: 8,
      display: 'flex',
      gap: 12,
      alignItems: 'flex-start'
    }}>
      <Icon size={20} style={{ color: 'var(--gray-500)', flexShrink: 0, marginTop: 2 }} />
      <div>
        <p style={{ fontWeight: 500, color: 'var(--gray-700)', marginBottom: 4 }}>{title}</p>
        <p style={{ color: 'var(--gray-600)', fontSize: 14 }}>{message}</p>
      </div>
    </div>
  );
}

export default EmptyState;
