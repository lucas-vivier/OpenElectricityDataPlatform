import { Loader2 } from 'lucide-react';

interface LoadingProgressProps {
  message?: string;
  isVisible: boolean;
}

/**
 * A loading progress bar that appears at the top of the page
 * when data is being loaded from the backend.
 */
export default function LoadingProgress({ message = 'Loading data...', isVisible }: LoadingProgressProps) {
  if (!isVisible) return null;

  return (
    <div className="loading-progress">
      <div className="loading-progress-bar" />
      <div className="loading-progress-content">
        <Loader2 size={16} className="animate-spin" />
        <span>{message}</span>
      </div>
    </div>
  );
}
