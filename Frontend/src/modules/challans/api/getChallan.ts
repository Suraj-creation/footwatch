import { apiRequest } from '@/shared/api/client'
import { endpoints } from '@/shared/api/endpoints'
import { Challan, challanSchema } from '@/modules/challans/types/challan'

export async function getChallan(id: string): Promise<Challan> {
  return apiRequest(endpoints.challanById(id), {
    schema: challanSchema,
  })
}
