import { Zap, Droplets, Sun, Wind } from 'lucide-react';

export interface MapLayer {
  id: string;
  name: string;
  icon: React.ReactNode;
  color: string;
  enabled: boolean;
}

interface MapLayerControlProps {
  layers: MapLayer[];
  onToggle: (layerId: string) => void;
  inline?: boolean;
}

export const DEFAULT_LAYERS: Omit<MapLayer, 'enabled'>[] = [
  { id: 'power_plants', name: 'Power Plants', icon: <Zap size={14} />, color: '#f97316' },
  { id: 'hydropower', name: 'Hydropower', icon: <Droplets size={14} />, color: '#0ea5e9' },
  { id: 'solar_potential', name: 'Solar Sites', icon: <Sun size={14} />, color: '#eab308' },
  { id: 'wind_potential', name: 'Wind Sites', icon: <Wind size={14} />, color: '#22c55e' },
];

export default function MapLayerControl({ layers, onToggle, inline = false }: MapLayerControlProps) {
  return (
    <div className={inline ? 'map-layer-control-inline' : 'map-layer-control'}>
      {!inline && (
        <div className="map-layer-header">
          <span>Layers</span>
        </div>
      )}
      <div className="map-layer-list">
        {layers.map(layer => (
          <label key={layer.id} className="map-layer-item">
            <input
              type="checkbox"
              checked={layer.enabled}
              onChange={() => onToggle(layer.id)}
            />
            <span className="map-layer-icon" style={{ color: layer.color }}>
              {layer.icon}
            </span>
            <span className="map-layer-name">{layer.name}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
