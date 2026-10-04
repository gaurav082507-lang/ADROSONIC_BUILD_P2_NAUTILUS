import React, { useState, useEffect } from 'react';
import { MapPin, Navigation, AlertTriangle, CheckCircle2, Info, Camera } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Offline-safe DivIcons (no external CDN icon images needed)
const claimedIcon = L.divIcon({
  className: 'custom-claimed-pin',
  html: `<div style="background:#2563eb;width:20px;height:20px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:white;font-size:10px;font-weight:bold;">C</div>`,
  iconSize: [20, 20],
  iconAnchor: [10, 10],
  popupAnchor: [0, -10],
});

const photoIcon = L.divIcon({
  className: 'custom-photo-pin',
  html: `<div style="background:#ea580c;width:20px;height:20px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:white;font-size:10px;font-weight:bold;">P</div>`,
  iconSize: [20, 20],
  iconAnchor: [10, 10],
  popupAnchor: [0, -10],
});

export default function LocationTab({ location, evidenceList }) {
  const [mapError, setMapError] = useState(false);

  const loc = location || {};
  const claimed = loc.claimed || {};
  const photos = loc.photos || [];
  const maxDistance = loc.max_distance_km || 0.0;

  const hasClaimed = claimed.lat != null && claimed.lng != null;
  const hasPhotosGps = photos.length > 0;

  const gpsEvidence = (evidenceList || []).find((e) => e.id === 'CLM-X-06');

  // Determine center of map
  let center = [19.076, 72.8777]; // Default Mumbai
  if (hasClaimed) {
    center = [claimed.lat, claimed.lng];
  } else if (hasPhotosGps) {
    center = [photos[0].lat, photos[0].lng];
  }

  return (
    <div className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-rule pb-4">
        <div>
          <h3 className="text-base font-bold text-ink flex items-center gap-2">
            <Navigation className="w-4 h-4 text-marker" />
            Geographic Location & Photo GPS Verification
          </h3>
          <p className="text-xs text-muted mt-0.5">
            Cross-checks the claimed incident location against embedded EXIF GPS coordinates in photos.
          </p>
        </div>
        {maxDistance > 0 && (
          <span
            className={`text-xs font-mono font-bold px-3 py-1 rounded border ${
              maxDistance > 50
                ? 'bg-red-100 text-red-800 border-red-200'
                : 'bg-green-100 text-green-800 border-green-200'
            }`}
          >
            Max Discrepancy: {maxDistance.toFixed(1)} km
          </span>
        )}
      </div>

      {/* Flag banner if CLM-X-06 present */}
      {gpsEvidence && (
        <div className="p-4 rounded-lg bg-red-50 border-2 border-red-400 space-y-1">
          <div className="flex items-center gap-2 text-red-900 font-bold text-xs uppercase tracking-wider">
            <AlertTriangle className="w-4 h-4 text-red-600" />
            Location Discrepancy Flag (CLM-X-06)
          </div>
          <p className="text-xs text-red-800">{gpsEvidence.reason}</p>
        </div>
      )}

      {!hasPhotosGps && (
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 flex items-start gap-2.5 text-xs text-amber-800">
          <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <b>No Photo GPS Data:</b> Uploaded claim photos have no embedded GPS metadata (very common after messaging apps like WhatsApp or Telegram strip EXIF). Per the specification, this check is <b>skipped</b> rather than marked failed, and does not alter risk scores.
          </div>
        </div>
      )}

      {/* Interactive Map View */}
      {(hasClaimed || hasPhotosGps) && !mapError ? (
        <div className="space-y-2">
          <div className="h-80 w-full rounded-xl overflow-hidden border border-rule relative z-0">
            <MapContainer
              center={center}
              zoom={hasPhotosGps && hasClaimed && maxDistance > 50 ? 6 : 12}
              scrollWheelZoom={false}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {/* Claimed location pin */}
              {hasClaimed && (
                <Marker position={[claimed.lat, claimed.lng]} icon={claimedIcon}>
                  <Popup>
                    <div className="text-xs font-sans">
                      <b>Stated Incident Location</b>
                      <br />
                      {claimed.text || `${claimed.lat}, ${claimed.lng}`}
                    </div>
                  </Popup>
                </Marker>
              )}

              {/* Photo GPS pins */}
              {photos.map((p, pIdx) => (
                <React.Fragment key={pIdx}>
                  <Marker position={[p.lat, p.lng]} icon={photoIcon}>
                    <Popup>
                      <div className="text-xs font-sans">
                        <b>Photo GPS ({p.image})</b>
                        <br />
                        Lat: {p.lat}, Lng: {p.lng}
                        <br />
                        Distance from claimed: {p.distance_km?.toFixed(1)} km
                      </div>
                    </Popup>
                  </Marker>

                  {/* Draw distance line between claimed and photo GPS */}
                  {hasClaimed && (
                    <Polyline
                      positions={[
                        [claimed.lat, claimed.lng],
                        [p.lat, p.lng],
                      ]}
                      color={p.distance_km > 50 ? 'red' : 'blue'}
                      dashArray={p.distance_km > 50 ? '6, 6' : undefined}
                      weight={3}
                    />
                  )}
                </React.Fragment>
              ))}
            </MapContainer>
          </div>
          <div className="text-[11px] text-muted flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-600 inline-block"></span>
                Stated Incident Pin
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-orange-500 inline-block"></span>
                Photo EXIF GPS Pin
              </span>
            </div>
            <span>Map tiles from OpenStreetMap (requires internet)</span>
          </div>
        </div>
      ) : null}

      {/* Offline Coordinate Breakdown Fallback Table */}
      <div className="space-y-3 pt-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-muted">
          Offline Coordinate Analysis & Distance Table
        </h4>
        <div className="overflow-x-auto rounded-lg border border-rule">
          <table className="w-full text-left text-xs text-ink">
            <thead className="bg-paper uppercase text-muted font-semibold border-b border-rule">
              <tr>
                <th className="px-4 py-2.5">Source Point</th>
                <th className="px-4 py-2.5">Latitude</th>
                <th className="px-4 py-2.5">Longitude</th>
                <th className="px-4 py-2.5">Distance Discrepancy</th>
                <th className="px-4 py-2.5">Evaluation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule font-medium">
              <tr className="bg-blue-50/30">
                <td className="px-4 py-2.5 font-bold text-blue-900 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-blue-600" />
                  Stated Incident (Claimant)
                </td>
                <td className="px-4 py-2.5 font-mono">{hasClaimed ? claimed.lat.toFixed(6) : '—'}</td>
                <td className="px-4 py-2.5 font-mono">{hasClaimed ? claimed.lng.toFixed(6) : '—'}</td>
                <td className="px-4 py-2.5 text-muted">Reference Point (0.0 km)</td>
                <td className="px-4 py-2.5 text-green-700 font-semibold">Stated Anchor</td>
              </tr>
              {photos.length > 0 ? (
                photos.map((p, idx) => (
                  <tr key={idx} className={p.distance_km > 50 ? 'bg-red-50/50' : ''}>
                    <td className="px-4 py-2.5 font-semibold flex items-center gap-1.5">
                      <Camera className="w-3.5 h-3.5 text-orange-600" />
                      {p.image} (EXIF GPS)
                    </td>
                    <td className="px-4 py-2.5 font-mono">{p.lat.toFixed(6)}</td>
                    <td className="px-4 py-2.5 font-mono">{p.lng.toFixed(6)}</td>
                    <td className="px-4 py-2.5 font-mono font-bold">
                      {p.distance_km != null ? `${p.distance_km.toFixed(1)} km` : '—'}
                    </td>
                    <td className="px-4 py-2.5">
                      {p.distance_km > 50 ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-100 text-red-800">
                          Discrepancy (&gt; 50 km)
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-green-100 text-green-800">
                          Consistent
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-4 py-3 text-center text-muted italic">
                    No photo GPS coordinates available. Offline location fallback active.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
