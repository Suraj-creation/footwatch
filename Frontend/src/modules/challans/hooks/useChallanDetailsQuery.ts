import { useQuery } from '@tanstack/react-query'
import { getChallan } from '@/modules/challans/api/getChallan'

export function useChallanDetailsQuery(id: string | undefined) {
  return useQuery({
    queryKey: ['challan-details', id],
    queryFn: () => getChallan(String(id)),
    enabled: Boolean(id),
  })
}
