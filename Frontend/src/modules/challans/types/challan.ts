import { z } from 'zod'

export const challanSchema = z.object({
  challan_id: z.string(),
  violation_id: z.string().optional(),
  plate_number: z.string().optional().default(''),
  vehicle_type: z.string().optional().default('unknown'),
  vehicle_color: z.string().optional().default('unknown'),
  violation_type: z.string().optional().default('FOOTPATH_ENCROACHMENT'),
  timestamp: z.string(),
  image_url: z.string().optional().default(''),
  fine_amount: z.number().nonnegative().default(0),
  status: z.string().optional().default('GENERATED'),
  camera_id: z.string().optional().default(''),
  location_name: z.string().optional().default(''),
  plate_ocr_confidence: z.number().optional(),
  pdf_generated: z.boolean().optional().default(false),
  pdf_endpoint: z.string().optional(),
  image_endpoint: z.string().optional(),
})

export const challanListResponseSchema = z.object({
  items: z.array(challanSchema),
})

export type Challan = z.infer<typeof challanSchema>
export type ChallanListResponse = z.infer<typeof challanListResponseSchema>
