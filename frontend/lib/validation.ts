import { UserDetails } from '@/types'

const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20MB
const ALLOWED_MIME = 'application/pdf'

export function validateUserDetails(details: UserDetails): string | null {
  if (!details.fullName.trim()) {
    return 'Please enter your full name.'
  }
  if (!details.accountType) {
    return 'Please select an account type.'
  }
  if (!details.bankName) {
    return 'Please select a bank.'
  }
  return null
}

export function validateFile(file: File): string | null {
  if (file.type !== ALLOWED_MIME) {
    return 'Only PDF files are accepted.'
  }
  if (file.size > MAX_FILE_SIZE) {
    return 'File size must be under 20MB.'
  }
  return null
}
