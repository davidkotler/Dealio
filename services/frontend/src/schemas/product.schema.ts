import { z } from 'zod'

export const addProductSchema = z.object({
  url: z
    .string()
    .url('Please enter a valid URL')
    .startsWith('https://', 'URL must start with https://'),
})

export type AddProductSchema = z.infer<typeof addProductSchema>