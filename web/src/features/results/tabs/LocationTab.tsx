import { useState } from 'react';
import { MapContainer, Marker, Polyline, Popup, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import type { ResultVM } from '../../../types/vm';
export default function LocationTab({ result }: { result: ResultVM }) {
  const [offline, setOffline] = useState(false);
  const location = result.location;
  if (!location?.claimed) return <div className="card p-8 text-sm text-muted">Not analysed</div>;
  const center: [number, number] = [location.claimed.lat, location.claimed.lng];
  return (
    <div className="grid gap-5 lg:grid-cols-[1.4fr_.8fr]">
      {offline ? (
        <div className="card p-5">
          <div className="font-semibold">Map unavailable</div>
          <p className="mt-1 text-sm text-muted">The evidence list remains available offline.</p>
        </div>
      ) : (
        <div className="card overflow-hidden p-2">
          <MapContainer
            center={center}
            zoom={14}
            style={{ height: 480, width: '100%' }}
            scrollWheelZoom={false}
          >
            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              eventHandlers={{ tileerror: () => setOffline(true) }}
            />
            <Marker position={center}>
              <Popup>Claimed location</Popup>
            </Marker>
            {location.photos.map((photo, index) => (
              <Marker key={index} position={[photo.lat, photo.lng]}>
                <Popup>Photo {index + 1}</Popup>
              </Marker>
            ))}
            {location.photos.map((photo, index) => (
              <Polyline key={`line-${index}`} positions={[center, [photo.lat, photo.lng]]} />
            ))}
          </MapContainer>
        </div>
      )}
      <div className="card p-5">
        <h3 className="font-display font-semibold">Location evidence</h3>
        <div className="mt-4 space-y-3">
          <div className="rounded-lg bg-slate-50 p-3 text-sm">
            Claimed: {center[0].toFixed(5)}, {center[1].toFixed(5)}
          </div>
          {location.photos.map((photo, index) => (
            <div key={index} className="rounded-lg border p-3 text-sm">
              <div>Photo {index + 1}</div>
              <div className="mt-1 text-muted">
                {photo.lat.toFixed(5)}, {photo.lng.toFixed(5)} · {photo.distanceKm ?? '—'} km
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
