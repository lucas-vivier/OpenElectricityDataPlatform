import { Circle, Droplets, Sun, Wind, Flame, Atom, Leaf, Zap, CheckCircle, Construction, Clock, XCircle } from 'lucide-react';

export interface MapLayer {
  id: string;
  name: string;
  icon: React.ReactNode;
  color: string;
  enabled: boolean;
}

interface MapLayerControlProps {
  technologyLayers: MapLayer[];
  statusLayers: MapLayer[];
  onToggleTechnology: (layerId: string) => void;
  onToggleStatus: (layerId: string) => void;
}

// Technology-based layers for power plants
export const DEFAULT_TECHNOLOGY_LAYERS: Omit<MapLayer, 'enabled'>[] = [
  { id: 'coal', name: 'Coal', icon: <Circle size={14} />, color: '#4a4a4a' },
  { id: 'gas', name: 'Gas', icon: <Flame size={14} />, color: '#f97316' },
  { id: 'oil', name: 'Oil', icon: <Circle size={14} />, color: '#854d0e' },
  { id: 'nuclear', name: 'Nuclear', icon: <Atom size={14} />, color: '#7c3aed' },
  { id: 'hydro', name: 'Hydro', icon: <Droplets size={14} />, color: '#0ea5e9' },
  { id: 'solar', name: 'Solar', icon: <Sun size={14} />, color: '#eab308' },
  { id: 'wind', name: 'Wind', icon: <Wind size={14} />, color: '#22c55e' },
  { id: 'biomass', name: 'Biomass', icon: <Leaf size={14} />, color: '#84cc16' },
  { id: 'geothermal', name: 'Geothermal', icon: <Circle size={14} />, color: '#dc2626' },
  { id: 'battery', name: 'Battery', icon: <Zap size={14} />, color: '#06b6d4' },
  { id: 'other', name: 'Other', icon: <Circle size={14} />, color: '#9ca3af' },
];

// Status-based layers for power plants
export const DEFAULT_STATUS_LAYERS: Omit<MapLayer, 'enabled'>[] = [
  { id: 'operating', name: 'Operating', icon: <CheckCircle size={14} />, color: '#22c55e' },
  { id: 'construction', name: 'Construction', icon: <Construction size={14} />, color: '#f97316' },
  { id: 'planned', name: 'Planned', icon: <Clock size={14} />, color: '#3b82f6' },
  { id: 'retired', name: 'Retired', icon: <XCircle size={14} />, color: '#9ca3af' },
];

export default function MapLayerControl({
  technologyLayers,
  statusLayers,
  onToggleTechnology,
  onToggleStatus
}: MapLayerControlProps) {
  // Guard against invalid props
  if (!technologyLayers || !Array.isArray(technologyLayers) || technologyLayers.length === 0) {
    return null;
  }

  return (
    <div className="map-layer-control">
      {/* Technology Layers */}
      <div className="map-layer-header">
        <span>Technologies</span>
      </div>
      <div className="map-layer-list" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 8px' }}>
        {technologyLayers.map(layer => (
          <label key={layer.id} className="map-layer-item" style={{ margin: 0 }}>
            <input
              type="checkbox"
              checked={layer.enabled}
              onChange={() => onToggleTechnology(layer.id)}
            />
            <span className="map-layer-icon" style={{ color: layer.color }}>
              {layer.icon}
            </span>
            <span className="map-layer-name">{layer.name}</span>
          </label>
        ))}
      </div>

      {/* Status Layers */}
      {statusLayers && statusLayers.length > 0 && (
        <>
          <div className="map-layer-header" style={{ marginTop: 12 }}>
            <span>Status</span>
          </div>
          <div className="map-layer-list" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 8px' }}>
            {statusLayers.map(layer => (
              <label key={layer.id} className="map-layer-item" style={{ margin: 0 }}>
                <input
                  type="checkbox"
                  checked={layer.enabled}
                  onChange={() => onToggleStatus(layer.id)}
                />
                <span className="map-layer-icon" style={{ color: layer.color }}>
                  {layer.icon}
                </span>
                <span className="map-layer-name">{layer.name}</span>
              </label>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
