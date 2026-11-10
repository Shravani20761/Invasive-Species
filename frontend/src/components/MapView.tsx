import { useEffect } from "react";
import { Circle, CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import type { Cluster, Sighting } from "../types";
import { formatDate, formatPercent, markerColor } from "../utils/format";

type HeatPoint = { latitude: number; longitude: number; weight: number };

type MapViewProps = {
  sightings?: Sighting[];
  clusters?: Cluster[];
  heatmap?: HeatPoint[];
  height?: string;
  onPick?: (latitude: number, longitude: number) => void;
  picked?: { latitude: number; longitude: number } | null;
  fit?: boolean;
};

function pin(color: string) {
  return L.divIcon({
    className: "isr-pin",
    html: `<span style="background:${color}"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  const signature = points.map((point) => point.map((value) => value.toFixed(4)).join(",")).join("|");
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 11);
    else if (points.length > 1) map.fitBounds(points, { padding: [28, 28] });
  }, [map, signature]);
  return null;
}

function PickHandler({ onPick }: { onPick: (latitude: number, longitude: number) => void }) {
  useMapEvents({
    click(event) {
      onPick(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

function ResizeMap() {
  const map = useMap();
  useEffect(() => {
    const timer = window.setTimeout(() => map.invalidateSize(), 150);
    return () => window.clearTimeout(timer);
  }, [map]);
  return null;
}

export function MapView({ sightings = [], clusters = [], heatmap = [], height = "520px", onPick, picked, fit = true }: MapViewProps) {
  const points: [number, number][] = [
    ...sightings.map((item) => [item.latitude, item.longitude] as [number, number]),
    ...(picked ? [[picked.latitude, picked.longitude] as [number, number]] : []),
  ];
  return (
    <div className="overflow-hidden rounded-2xl border border-pale bg-white shadow-card" style={{ height }}>
      <MapContainer center={[12.8, 77.2]} zoom={7} scrollWheelZoom className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ResizeMap />
        {fit && <FitBounds points={points} />}
        {onPick && <PickHandler onPick={onPick} />}
        {heatmap.map((point) => (
          <CircleMarker
            key={`${point.latitude}-${point.longitude}`}
            center={[point.latitude, point.longitude]}
            radius={8 + Math.min(point.weight, 8)}
            pathOptions={{ color: "#123C2D", fillColor: "#1B513C", fillOpacity: 0.25, weight: 1 }}
          />
        ))}
        {clusters.map((cluster) => (
          <Circle
            key={cluster.id}
            center={[cluster.center_latitude, cluster.center_longitude]}
            radius={Math.max(cluster.radius_km, 0.4) * 1000}
            pathOptions={{ color: markerColor(cluster.classification, cluster.risk_level), weight: 2, fillOpacity: 0.12 }}
          >
            <Popup>
              <strong>{cluster.common_name}</strong>
              <div>{cluster.sighting_count} sightings · {cluster.growth_indicator}</div>
              <div>Radius about {cluster.radius_km.toFixed(1)} km</div>
            </Popup>
          </Circle>
        ))}
        <MarkerClusterGroup chunkedLoading>
          {sightings.map((sighting) => (
            <Marker key={sighting.id} position={[sighting.latitude, sighting.longitude]} icon={pin(markerColor(sighting.classification, sighting.risk_level))}>
              <Popup>
                <div className="w-52">
                  {sighting.image_url && <img src={sighting.image_url} alt="" className="mb-2 h-28 w-full rounded object-cover" />}
                  <strong>{sighting.common_name}</strong>
                  {sighting.scientific_name && <div className="italic text-slate-600">{sighting.scientific_name}</div>}
                  <div>Confidence {formatPercent(sighting.confidence)}</div>
                  <div>{formatDate(sighting.observed_at)}</div>
                  <div>{sighting.location_name}</div>
                  {sighting.is_demonstration && <div className="mt-1 text-xs">Synthetic demonstration record</div>}
                </div>
              </Popup>
            </Marker>
          ))}
        </MarkerClusterGroup>
        {picked && <Marker position={[picked.latitude, picked.longitude]} icon={pin("#123C2D")} />}
      </MapContainer>
    </div>
  );
}
