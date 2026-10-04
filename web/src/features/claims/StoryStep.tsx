import { useEffect, useRef, useState } from 'react';
import { useTranscribe, useVoiceLanguages } from '../../api/hooks';
import { isFeatureOn } from '../../lib/featureFlags';
import type { TranscriptionVM } from '../../types/vm';
import { MapContainer, Marker, TileLayer, useMapEvents } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';

type Props = {
  claimantName: string;
  setClaimantName: (value: string) => void;
  description: string;
  setDescription: (value: string) => void;
  amount: string;
  setAmount: (value: string) => void;
  location: [number, number] | null;
  setLocation: (value: [number, number]) => void;
  onAudio: (blob: Blob | null) => void;
  incidentDate: string;
  setIncidentDate: (value: string) => void;
  incidentTime: string;
  setIncidentTime: (value: string) => void;
  voiceLang: string;
  setVoiceLang: (value: string) => void;
  t: any;
};
function PinPicker({ onPick }: { onPick: (point: [number, number]) => void }) {
  useMapEvents({ click: (event) => onPick([event.latlng.lat, event.latlng.lng]) });
  return null;
}
export default function StoryStep({ claimantName, setClaimantName,
  description,
  setDescription,
  amount,
  setAmount,
  location,
  setLocation,
  onAudio,
  incidentDate,
  setIncidentDate,
  incidentTime,
  setIncidentTime,
  voiceLang,
  setVoiceLang,
  t,
}: Props) {
  const voiceOn = isFeatureOn('voice');
  const languages = useVoiceLanguages(voiceOn);
  const transcribe = useTranscribe();
  const [audio, setAudio] = useState<Blob | null>(null);
  const [heard, setHeard] = useState<TranscriptionVM>();
  const [voiceNote, setVoiceNote] = useState('');
  const runTranscription = async () => {
    if (!audio) return;
    setVoiceNote('');
    try {
      const out = await transcribe.mutateAsync({ audio, language: voiceLang });
      setHeard(out);
      // Only fill fields the claimant left empty – never overwrite what they typed.
      let filled = false;
      if (!description.trim() && out.translationEn) {
        setDescription(
          out.transcript ? `${out.transcript}\n\n${out.translationEn}` : out.translationEn,
        );
        filled = true;
      }
      if (!amount && out.extracted.amount !== undefined) {
        setAmount(String(out.extracted.amount));
        filled = true;
      }
      if (!incidentDate && out.extracted.incidentDate) {
        setIncidentDate(out.extracted.incidentDate);
        filled = true;
      }
      if (!incidentTime && out.extracted.incidentTime) {
        setIncidentTime(out.extracted.incidentTime);
        filled = true;
      }
      if (filled) setVoiceNote(t.autofilled);
    } catch {
      setVoiceNote(t.transcriptionUnavailable);
    }
  };
  const clearAudio = () => {
    setAudio(null);
    setHeard(undefined);
    onAudio(null);
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(undefined);
  };
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string>();
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  useEffect(
    () => () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    },
    [audioUrl],
  );
  useEffect(() => {
    if (!recording) return;
    const timer = window.setInterval(() => {
      setSeconds((value) => {
        if (value >= 89) {
          recorder.current?.stop();
          return value;
        }
        return value + 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [recording]);
  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks.current = [];
      const current = new MediaRecorder(stream);
      recorder.current = current;
      current.ondataavailable = (event) => event.data.size && chunks.current.push(event.data);
      current.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunks.current, { type: current.mimeType || 'audio/webm' });
        onAudio(blob);
        setAudio(blob);
        setHeard(undefined);
        setAudioUrl(URL.createObjectURL(blob));
        setRecording(false);
      };
      current.start();
      setSeconds(0);
      setRecording(true);
    } catch {
      /* permission error is handled by the browser and submit validation */
    }
  };
  const center: LatLngExpression = location ?? [23.3441, 85.3096];
  return (
          <div>
        <h2 className="font-display text-xl font-semibold mb-4">Claimant Details</h2>
        <label className="text-sm block mb-6">
          <span className="mb-2 block font-medium">Claimant Name</span>
          <input
            type="text"
            value={claimantName}
            onChange={(event) => setClaimantName(event.target.value)}
            className="w-full rounded-lg border px-3 py-2.5"
            placeholder="Enter your full name"
          />
        </label>
        <h2 className="font-display text-xl font-semibold">{t.story}</h2>
      <textarea
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        className="mt-5 min-h-36 w-full rounded-xl border p-4 text-sm"
        placeholder={t.descriptionLabel}
      />
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-2 block font-medium">{t.incidentDate}</span>
          <input
            type="date"
            value={incidentDate}
            max={new Date().toISOString().slice(0, 10)}
            onChange={(event) => setIncidentDate(event.target.value)}
            className="w-full rounded-lg border px-3 py-2.5"
          />
        </label>
        <label className="text-sm">
          <span className="mb-2 block font-medium">{t.incidentTime}</span>
          <input
            type="time"
            value={incidentTime}
            onChange={(event) => setIncidentTime(event.target.value)}
            className="w-full rounded-lg border px-3 py-2.5"
          />
        </label>
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-2 block font-medium">{t.amount}</span>
          <input
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            inputMode="decimal"
            className="w-full rounded-lg border px-3 py-2.5"
            placeholder="₹ 0"
          />
        </label>
        <div className="rounded-xl border p-3">
          <div className="text-sm font-medium">{t.voice}</div>
          {recording ? (
            <button
              onClick={() => recorder.current?.stop()}
              className="mt-2 rounded-lg bg-primary-dark px-3 py-2 text-sm text-white"
            >
              {t.stop} · {seconds}s
            </button>
          ) : (
            <button onClick={start} className="mt-2 rounded-lg border px-3 py-2 text-sm">
              {t.record}
            </button>
          )}
          {voiceOn && (
            <label className="mt-3 block text-xs">
              <span className="mb-1 block text-muted">{t.language}</span>
              <select
                value={voiceLang}
                onChange={(event) => setVoiceLang(event.target.value)}
                className="w-full rounded-lg border px-2 py-1.5 text-sm"
              >
                {(
                  languages.data ?? [
                    { code: 'hi', label: 'Hindi · हिंदी' },
                    { code: 'en', label: 'English' },
                  ]
                ).map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          {audioUrl && <audio className="mt-3 w-full" controls src={audioUrl} />}
          {audio && (
            <div className="mt-2 flex flex-wrap gap-2">
              {voiceOn && (
                <button
                  onClick={runTranscription}
                  disabled={transcribe.isPending}
                  className="rounded-lg bg-primary-dark px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
                >
                  {transcribe.isPending ? t.transcribing : t.transcribe}
                </button>
              )}
              <button onClick={clearAudio} className="rounded-lg border px-3 py-1.5 text-xs">
                {t.removeRecording}
              </button>
            </div>
          )}
          {heard && (
            <div className="mt-3 space-y-2 text-xs">
              <div>
                <div className="text-muted">{t.transcript}</div>
                <p className="rounded bg-bg p-2">{heard.transcript}</p>
              </div>
              {heard.translationEn && heard.language !== 'en' && (
                <div>
                  <div className="text-muted">{t.translation}</div>
                  <p className="rounded bg-bg p-2">{heard.translationEn}</p>
                </div>
              )}
            </div>
          )}
          {voiceNote && (
            <p className="mt-2 text-xs text-slate-700" role="status">
              {voiceNote}
            </p>
          )}
        </div>
      </div>
      <div className="mt-5 overflow-hidden rounded-xl border">
        <div className="border-b bg-bg p-3 text-sm font-medium">
          {t.location} · {t.locationHint}
        </div>
        <MapContainer center={center} zoom={13} style={{ height: 320 }}>
          <TileLayer
            attribution="&copy;
  OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <PinPicker onPick={setLocation} />
          {location && <Marker position={location} />}
        </MapContainer>
      </div>
    </div>
  );
}
