import type { ScoreVM } from '../../types/vm';
import type { ReactElement } from 'react';
import { useState } from 'react';
import { Download, Trash2 } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { useClaimActions, useClaimEntities, useDeleteResult, useResult } from '../../api/hooks';
import { raw } from '../../api/raw/endpoints';
import { downloadBlob } from '../../lib/download';
import { dateLabel } from '../../lib/format';
import { friendlyError } from '../../lib/errorMessages';
import { Loading, ErrorState } from '../../components/States';
import { RiskBadge } from '../../components/RiskBadge';
import { ConfidencePill } from '../../components/ConfidencePill';
import { ScoreGauge } from '../../components/ScoreGauge';
import DecisionDialog from '../decisions/DecisionDialog';
import ImageTab from './tabs/ImageTab';
import DocumentTab from './tabs/DocumentTab';
import IdentityTab from './tabs/IdentityTab';
import ClaimChecksTab from './tabs/ClaimChecksTab';
import TimelineTab from './tabs/TimelineTab';
import LocationTab from './tabs/LocationTab';
import EvidenceTab from './tabs/EvidenceTab';
import WhyThisScoreTab from './tabs/WhyThisScoreTab';
import ChecksRunTab from './tabs/ChecksRunTab';
import NetworkTab from './tabs/NetworkTab';
import StoryTab from './tabs/StoryTab';
import VoiceTab from './tabs/VoiceTab';
import { isFeatureOn } from '../../lib/featureFlags';

const allTabs = [
  'Image',
  'Document',
  'Identity',
  'Voice',
  'Claim checks',
  'Network',
  'Story review',
  'Timeline',
  'Location',
  'Evidence',
  'Why this score',
  'Checks run',
] as const;
type Tab = (typeof allTabs)[number];
const tabFeature: Partial<Record<Tab, string>> = {
  Voice: 'voice',
  Network: 'network',
  'Story review': 'story',
};
const tabs = allTabs.filter((t) => !tabFeature[t] || isFeatureOn(tabFeature[t]!));

export default function ResultPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const resultQuery = useResult(id);
  const claimId = resultQuery.data?.claimId ?? '';
  const actions = useClaimActions(claimId);
  const entities = useClaimEntities(claimId);
  const remove = useDeleteResult();
  const [tab, setTab] = useState<Tab>('Image');
  const [decision, setDecision] = useState(false);
  if (resultQuery.isLoading) return <Loading label="Loading forensic result..." />;
  if (resultQuery.error) {
    if ((resultQuery.error as any).status === 404 || (resultQuery.error as any).status === 0) {
      return <Loading label="Analysis in progress..." />;
    }
    return (
      <ErrorState
        message={friendlyError((resultQuery.error as any).code, (resultQuery.error as any).message)}
        retry={() => resultQuery.refetch()}
      />
    );
  }
  if (!resultQuery.data) return <Loading label="Loading forensic result..." />;
  const result = resultQuery.data!;
  const downloadReport = async (format: 'pdf' | 'json') => {
    const blob = await raw.report(id, format);
    downloadBlob(blob, `lucen-${id}.${format}`);
  };
  const content: Record<Tab, ReactElement> = {
    Image: <ImageTab result={result} />,
    Document: <DocumentTab result={result} />,
    Identity: <IdentityTab result={result} />,
    Voice: <VoiceTab result={result} />,
    Network: result.claimId ? (
      <NetworkTab claimId={result.claimId} />
    ) : (
      <div className="card p-6 text-sm text-muted">
        This analysis was run directly (not as part of a claim), so it has no claim network.
      </div>
    ),
    'Story review': <StoryTab result={result} />,
    'Claim checks': <ClaimChecksTab result={result} />,
    Timeline: <TimelineTab result={result} />,
    Location: <LocationTab result={result} />,
    Evidence: <EvidenceTab result={result} />,
    'Why this score': <WhyThisScoreTab result={result} />,
    'Checks run': <ChecksRunTab result={result} />,
  };
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mono text-xs text-muted">{result.id}</div>
          <h1 className="font-display mt-1 text-3xl font-bold">Claim intelligence</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted">{result.summary}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => downloadReport('pdf')}
            className="rounded-lg border px-3 py-2 text-sm"
          >
            <Download className="mr-1 inline" size={15} />
            PDF
          </button>
          <button
            onClick={() => downloadReport('json')}
            className="rounded-lg border px-3 py-2 text-sm"
          >
            JSON
          </button>
          <button
            onClick={async () => {
              if (confirm('Delete this result?')) {
                await remove.mutateAsync(id);
                navigate('/app/history');
              }
            }}
            className="rounded-lg border px-3 py-2 text-sm text-red-700"
          >
            <Trash2 className="mr-1 inline" size={15} />
            Delete
          </button>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-wide text-muted">
                Overall fraud likelihood
              </div>
              <div className="mt-2 flex items-center gap-3">
                <RiskBadge band={result.overall.band} />
                <ConfidencePill value={result.overall.confidence} />
              </div>
            </div>
            <ScoreGauge label="Risk" risk={result.overall.risk} band={result.overall.band} />
          </div>
          <p className="mt-4 text-sm text-muted">{result.recommendedAction}</p>
          {result.overall.confidence !== 'high' && (
            <div className="mt-3 rounded-lg bg-yellow-50 p-3 text-xs text-yellow-900">
              Some checks were limited; see Checks run.
            </div>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3">
          {(
            [
              ['Image', result.image],
              ['Document', result.document],
              ['Identity', result.identity],
              ['Claim checks', result.claim],
              ...(isFeatureOn('voice') ? [['Voice', result.voice]] : []),
            ] as [string, ScoreVM | undefined][]
          ).map(([name, score]) => (
            <div key={String(name)} className="card p-4">
              <div className="text-xs text-muted">{name}</div>
              <div className="mt-2 text-xl font-bold">
                {score?.analysed ? `${Math.round(score.risk * 100)}%` : 'Not analysed'}
              </div>
            </div>
          ))}
        </div>
      </div>
      {result.qualityWarnings.length > 0 && (
        <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4 text-sm">
          {result.qualityWarnings.join(' ')}
        </div>
      )}
      {result.decision && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
          <b>Decision recorded:</b> {result.decision.status} by {result.decision.by} ·{' '}
          {dateLabel(result.decision.at)}
          {result.decision.claimantMessage && (
            <div className="mt-1 text-muted">
              Message to claimant: {result.decision.claimantMessage}
            </div>
          )}
        </div>
      )}
      {!!result.links.length && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
          <b>Related analyses:</b>{' '}
          {result.links.map((l, i) => (
            <span key={l.resultId}>
              {i > 0 && ' · '}
              <a className="text-signal underline" href={`/app/results/${l.resultId}`}>
                {l.resultId}
              </a>{' '}
              ({l.reason})
            </span>
          ))}
        </div>
      )}
      {result.duplicate && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm">
          <b>Duplicate evidence match</b>
          <span className="ml-2">
            {Math.round(result.duplicate.similarity * 100)}% similarity · earlier claim{' '}
            {result.duplicate.earlierClaim}
          </span>
        </div>
      )}
      <div className="flex gap-1 overflow-x-auto rounded-lg border border-border bg-white p-1">
        {tabs.map((item) => (
          <button
            key={item}
            onClick={() => setTab(item)}
            className={`whitespace-nowrap rounded-md px-3 py-2 text-sm ${tab === item ? 'bg-primary-dark text-white' : 'text-muted'}`}
          >
            {item}
          </button>
        ))}
      </div>
      {content[tab]}
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="font-display font-semibold">Audit log</h2>
          <div className="mt-3 space-y-2 text-sm">
            {(actions.data ?? []).map((item, index) => (
              <div key={index} className="rounded-lg bg-bg p-3">
                {dateLabel(item.at)} · {item.action} · {item.actor}
                {item.note ? ` · ${item.note}` : ''}
              </div>
            ))}
            {!actions.data?.length && <div className="text-sm text-muted">Not available</div>}
          </div>
        </div>
        <div className="card p-5">
          <h2 className="font-display font-semibold">Related entities</h2>
          <div className="mt-3 space-y-2 text-sm">
            {(entities.data ?? []).map((item: any, index: number) => (
              <div key={index} className="flex justify-between rounded-lg bg-bg p-3">
                <span>{item.type}</span>
                <span>
                  {item.value} · {item.matches}
                </span>
              </div>
            ))}
            {!entities.data?.length && <div className="text-sm text-muted">Not available</div>}
          </div>
        </div>
      </div>
      <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
        <div>
          <div className="font-semibold">Investigator decision</div>
          <div className="text-sm text-muted">
            Generate an editable bilingual decision from the backend.
          </div>
        </div>
        <button
          onClick={() => setDecision(true)}
          className="rounded-lg bg-primary-dark px-4 py-2.5 text-sm font-semibold text-white"
        >
          Open decision
        </button>
      </div>
      {decision && <DecisionDialog id={id} onClose={() => setDecision(false)} />}
    </div>
  );
}
