import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { raw } from '../raw/endpoints';
import {
  adaptClaimNetwork,
  adaptGraph,
  adaptLanguages,
  adaptRingDetail,
  adaptRings,
  adaptSummary,
  adaptTranscription,
  adaptTrends,
  adaptJob,
  adaptResult,
  adaptQueue,
  adaptHistory,
  adaptPolicies,
  adaptClaimStatus,
  adaptClaimsMine,
  adaptActions,
  adaptTimeline,
  asList,
} from '../adapters';
import { queryKeys } from '../queryKeys';
export type QueueParams = Parameters<typeof raw.queue>[0];
export type HistoryParams = Parameters<typeof raw.history>[0];
export const useQueue = (params: QueueParams = {}) =>
  useQuery({
    queryKey: queryKeys.queue(JSON.stringify(params)),
    queryFn: async () => adaptQueue(await raw.queue(params)),
  });
export const useHistory = (params: HistoryParams = {}) =>
  useQuery({
    queryKey: queryKeys.history(JSON.stringify(params)),
    queryFn: async () => adaptHistory(await raw.history(params)),
  });
export const useResult = (id: string) =>
  useQuery({
    queryKey: queryKeys.result(id),
    queryFn: async () => adaptResult(await raw.result(id)),
    enabled: !!id,
  });
export const useJobPolling = (id: string) =>
  useQuery({
    queryKey: queryKeys.job(id),
    queryFn: async () => adaptJob(await raw.job(id)),
    enabled: !!id,
    refetchInterval: (q: any) => {
      const d = q.state.data;
      return d?.status === 'queued' || d?.status === 'running' ? 1000 : false;
    },
  });
export const usePolicies = () =>
  useQuery({
    queryKey: queryKeys.policies,
    queryFn: async () => adaptPolicies(await raw.policies()),
  });
/** Status + evidence checklist come from two endpoints; merged into one view-model. */
export const useClaimStatus = (id: string) =>
  useQuery({
    queryKey: queryKeys.claimStatus(id),
    queryFn: async () => {
      const [status, evidence] = await Promise.all([
        raw.claimStatus(id),
        raw.claimTimeline(id).catch(() => []),
      ]);
      return adaptClaimStatus(status, asList(evidence as never));
    },
    enabled: !!id,
  });
export const useClaimsMine = () =>
  useQuery({
    queryKey: ['claims', 'mine'],
    queryFn: async () => adaptClaimsMine(await raw.claimsMine()),
  });
export const useResultTimeline = (id: string, enabled = true) =>
  useQuery({
    queryKey: ['result', id, 'timeline'],
    queryFn: async () => adaptTimeline(await raw.timeline(id)),
    enabled: enabled && !!id,
  });
export const useLogin = () =>
  useMutation({
    mutationFn: (x: { email: string; password: string }) => raw.login(x.email, x.password),
  });
export const useDeleteResult = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => raw.deleteResult(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['history'] }),
  });
};

export const useClaimActions = (id: string) =>
  useQuery({
    queryKey: ['claims', id, 'actions'],
    queryFn: async () => adaptActions(await raw.actions(id)),
    enabled: !!id,
  });
export const useClaimEntities = (id: string) =>
  useQuery({
    queryKey: ['claims', id, 'entities'],
    queryFn: () => raw.entities(id),
    enabled: !!id,
  });

/* ---------- Network ---------- */
export type GraphParams = {
  focusType?: 'claim' | 'claimant' | 'ring';
  focusId?: string;
  hops?: number;
  minStrength?: number;
  limit?: number;
};
export const useNetworkGraph = (params: GraphParams, enabled = true) =>
  useQuery({
    queryKey: queryKeys.networkGraph(params),
    queryFn: async () => adaptGraph(await raw.networkGraph(params)),
    enabled,
  });
export const useRings = (params: { minScore?: number; status?: string } = {}, enabled = true) =>
  useQuery({
    queryKey: queryKeys.rings(params),
    queryFn: async () => adaptRings(await raw.rings(params)),
    enabled,
  });
export const useRing = (ringId: string) =>
  useQuery({
    queryKey: queryKeys.ring(ringId),
    queryFn: async () => adaptRingDetail(await raw.ring(ringId)),
    enabled: !!ringId,
  });
export const useRingStatus = (ringId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (x: { status: string; note: string }) => raw.ringStatus(ringId, x.status, x.note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['network'] });
    },
  });
};
export const useClaimNetwork = (claimId: string, enabled = true) =>
  useQuery({
    queryKey: queryKeys.claimNetwork(claimId),
    queryFn: async () => adaptClaimNetwork(await raw.claimNetwork(claimId)),
    enabled: enabled && !!claimId,
  });

/* ---------- Analytics ---------- */
export const useAnalyticsSummary = (enabled = true) =>
  useQuery({
    queryKey: queryKeys.analyticsSummary,
    queryFn: async () => adaptSummary(await raw.analyticsSummary()),
    enabled,
  });
export const useAnalyticsTrends = (range: '7d' | '30d' | '90d', type?: string, enabled = true) =>
  useQuery({
    queryKey: queryKeys.analyticsTrends(range, type),
    queryFn: async () => adaptTrends(await raw.analyticsTrends(range, type)),
    enabled,
  });

/* ---------- Voice ---------- */
export const useVoiceLanguages = (enabled = true) =>
  useQuery({
    queryKey: queryKeys.voiceLanguages,
    queryFn: async () => adaptLanguages(await raw.voiceLanguages()),
    enabled,
    staleTime: 60 * 60 * 1000,
  });
export const useTranscribe = () =>
  useMutation({
    mutationFn: async (x: { audio: Blob; language: string }) =>
      adaptTranscription(await raw.voiceTranscribe(x.audio, x.language)),
  });
