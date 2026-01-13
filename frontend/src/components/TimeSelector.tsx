import { Calendar, Clock } from 'lucide-react';

interface TimeSelectorProps {
  year: number;
  month?: number | null;
  months?: number[];  // For multi-month selection
  day?: number;
  onYearChange: (year: number) => void;
  onMonthChange?: (month: number | null) => void;
  onMonthsChange?: (months: number[]) => void;  // For multi-month selection
  onDayChange?: (day: number | undefined) => void;
  showDay?: boolean;
  showFullYear?: boolean;
  availableYears?: number[];
  multiSelect?: boolean;  // Enable checkbox-based multi-select
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const MONTH_ABBREV = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
];

const DEFAULT_YEARS = [2020];

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

export default function TimeSelector({
  year,
  month,
  months = [],
  day,
  onYearChange,
  onMonthChange,
  onMonthsChange,
  onDayChange,
  showDay = false,
  showFullYear = true,
  availableYears = DEFAULT_YEARS,
  multiSelect = false,
}: TimeSelectorProps) {
  const daysInMonth = month ? getDaysInMonth(year, month) : 31;
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const years = availableYears.length > 0 ? availableYears : DEFAULT_YEARS;

  const handleMonthToggle = (monthNum: number) => {
    if (!onMonthsChange) return;
    if (months.includes(monthNum)) {
      onMonthsChange(months.filter(m => m !== monthNum));
    } else {
      onMonthsChange([...months, monthNum].sort((a, b) => a - b));
    }
  };

  const handleSelectAll = () => {
    if (!onMonthsChange) return;
    onMonthsChange([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
  };

  const handleClearAll = () => {
    if (!onMonthsChange) return;
    onMonthsChange([]);
  };

  const allSelected = months.length === 12;
  const noneSelected = months.length === 0;

  return (
    <div className="time-selector">
      <div className="time-selector-row">
        <div className="time-selector-field">
          <label className="form-label">
            <Calendar size={14} style={{ marginRight: 4 }} />
            Year
          </label>
          <select
            className="form-select"
            value={year}
            onChange={(e) => onYearChange(Number(e.target.value))}
          >
            {years.map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        {!multiSelect && onMonthChange && (
          <div className="time-selector-field">
            <label className="form-label">
              <Calendar size={14} style={{ marginRight: 4 }} />
              Month
            </label>
            <select
              className="form-select"
              value={month || ''}
              onChange={(e) => onMonthChange(e.target.value ? Number(e.target.value) : null)}
            >
              {showFullYear && <option value="">Full Year</option>}
              {MONTHS.map((name, idx) => (
                <option key={idx + 1} value={idx + 1}>{name}</option>
              ))}
            </select>
          </div>
        )}

        {showDay && onDayChange && month && (
          <div className="time-selector-field">
            <label className="form-label">
              <Clock size={14} style={{ marginRight: 4 }} />
              Day
            </label>
            <select
              className="form-select"
              value={day || ''}
              onChange={(e) => onDayChange(e.target.value ? Number(e.target.value) : undefined)}
            >
              <option value="">All days</option>
              {days.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {multiSelect && onMonthsChange && (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <label className="form-label" style={{ margin: 0 }}>
              <Calendar size={14} style={{ marginRight: 4 }} />
              Months
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                type="button"
                onClick={handleSelectAll}
                disabled={allSelected}
                style={{
                  padding: '4px 8px',
                  fontSize: 11,
                  background: allSelected ? 'var(--gray-100)' : 'var(--gray-50)',
                  border: '1px solid var(--gray-200)',
                  borderRadius: 4,
                  cursor: allSelected ? 'not-allowed' : 'pointer',
                  color: allSelected ? 'var(--gray-400)' : 'var(--gray-600)',
                }}
              >
                Select All
              </button>
              <button
                type="button"
                onClick={handleClearAll}
                disabled={noneSelected}
                style={{
                  padding: '4px 8px',
                  fontSize: 11,
                  background: noneSelected ? 'var(--gray-100)' : 'var(--gray-50)',
                  border: '1px solid var(--gray-200)',
                  borderRadius: 4,
                  cursor: noneSelected ? 'not-allowed' : 'pointer',
                  color: noneSelected ? 'var(--gray-400)' : 'var(--gray-600)',
                }}
              >
                Clear All
              </button>
            </div>
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gap: 6,
          }}>
            {MONTH_ABBREV.map((name, idx) => {
              const monthNum = idx + 1;
              const isSelected = months.includes(monthNum);
              return (
                <label
                  key={monthNum}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 4,
                    padding: '8px 4px',
                    background: isSelected ? 'var(--primary)' : 'white',
                    color: isSelected ? 'white' : 'var(--gray-600)',
                    border: `1px solid ${isSelected ? 'var(--primary)' : 'var(--gray-200)'}`,
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontSize: 13,
                    fontWeight: isSelected ? 500 : 400,
                    transition: 'all 0.15s',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleMonthToggle(monthNum)}
                    style={{ display: 'none' }}
                  />
                  {name}
                </label>
              );
            })}
          </div>
          <p style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 8, textAlign: 'center' }}>
            {months.length === 0
              ? 'Select months to filter (or leave empty for full year)'
              : months.length === 12
              ? 'Showing full year average'
              : `Showing average for ${months.length} selected month${months.length > 1 ? 's' : ''}`}
          </p>
        </div>
      )}
    </div>
  );
}
