import { useQuery } from '@tanstack/react-query'
import { listChallans, ChallanListQuery } from '@/modules/challans/api/listChallans'
import { polling } from '@/shared/config/polling'

export function useChallansQuery(filters: ChallanListQuery) {
  return useQuery({
    queryKey: ['challans', filters],
    queryFn: () => listChallans(filters),
    refetchInterval: polling.violationsMs,
  })
}
