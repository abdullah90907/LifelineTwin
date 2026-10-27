import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

export function useWorkspace() {
  const health = useQuery({ queryKey: ['health'], queryFn: ({ signal }) => api.health(signal) })
  const atlas = useQuery({ queryKey: ['atlas'], queryFn: ({ signal }) => api.atlas(signal), staleTime: Infinity })
  const baseline = useQuery({ queryKey: ['baseline'], queryFn: ({ signal }) => api.baseline(signal), staleTime: 300_000 })
  return { health, atlas, baseline }
}
export type Workspace = ReturnType<typeof useWorkspace>
