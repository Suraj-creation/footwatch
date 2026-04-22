import { z } from 'zod'
import { apiRequest, unknownSchema } from '@/shared/api/client'
import { endpoints } from '@/shared/api/endpoints'
import { ChallanListResponse, challanListResponseSchema, challanSchema } from '@/modules/challans/types/challan'

export type ChallanListQuery = {
  plate_number?: string
  challan_id?: string
  violation_type?: string
  status?: string
  camera_id?: string
  from?: string
  to?: string
  limit?: number
}

const challanArraySchema = z.array(challanSchema)

export async function listChallans(query: ChallanListQuery = {}): Promise<ChallanListResponse> {
  const payload = await apiRequest(endpoints.challans, {
    query,
    schema: unknownSchema,
  })

  if (Array.isArray(payload)) {
    return { items: challanArraySchema.parse(payload) }
  }

  return challanListResponseSchema.parse(payload)
}
