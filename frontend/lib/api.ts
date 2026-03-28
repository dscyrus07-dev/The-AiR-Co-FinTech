import { ProcessingResult, ProcessingMode, UserDetails } from '@/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function uploadStatement(
  file: File,
  userDetails: UserDetails,
  mode: ProcessingMode = 'free',
  apiKey?: string,
  pdfPassword?: string,
): Promise<ProcessingResult> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('full_name', userDetails.fullName)
  formData.append('account_type', userDetails.accountType)
  formData.append('bank_name', userDetails.bankName)
  formData.append('mode', mode)

  if (mode === 'hybrid' && apiKey) {
    formData.append('api_key', apiKey)
  }

  if (pdfPassword) {
    formData.append('pdf_password', pdfPassword)
  }

  const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(errorData?.message || 'Failed to process statement. Please try again.')
  }

  return response.json()
}
