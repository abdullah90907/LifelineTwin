import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

export function useWorkspace(analytical = true) {
  const health = useQuery({ queryKey: ['health'], queryFn: ({ signal }) => api.health(signal) })
  const atlas = useQuery({ enabled: analytical, queryKey: ['atlas','houston-v1'], queryFn: ({ signal }) => api.atlas(signal), staleTime: Infinity })
  const baseline = useQuery({ enabled: analytical, queryKey: ['baseline','houston-v1'], queryFn: ({ signal }) => api.baseline(signal), staleTime: 300_000 })
  return { health, atlas, baseline }
}
export type Workspace = ReturnType<typeof useWorkspace>
