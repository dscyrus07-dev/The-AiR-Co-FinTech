'use client'

import { useState } from 'react'
import { UserDetails, BankName, AccountType } from '@/types'
import { validateUserDetails } from '@/lib/validation'

const BANKS: { name: BankName; available: boolean }[] = [
  { name: 'HDFC Bank',  available: true  },
  { name: 'ICICI Bank', available: true  },
  { name: 'Axis Bank',  available: true  },
  { name: 'Kotak Bank', available: true  },
  { name: 'SBI',        available: true  },
  { name: 'HSBC Bank',  available: false },
  { name: 'Other',      available: false },
]

interface StepFormProps {
  onSubmit: (details: UserDetails) => void
  initialDetails?: UserDetails
}

export default function StepForm({ onSubmit, initialDetails }: StepFormProps) {
  const [details, setDetails] = useState<UserDetails>(
    initialDetails || {
      fullName: '',
      accountType: '',
      bankName: '',
    }
  )
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = () => {
    const validationError = validateUserDetails(details)
    if (validationError) {
      setError(validationError)
      return
    }
    setError(null)
    onSubmit(details)
  }

  const isComplete =
    details.fullName.trim() !== '' &&
    details.accountType !== '' &&
    details.bankName !== ''

  return (
    <div className="animate-fade-in">
      <div className="space-y-6">
        {/* Full Name */}
        <div>
          <label
            htmlFor="fullName"
            className="block text-sm font-medium text-black mb-1.5"
          >
            Full Name
          </label>
          <input
            id="fullName"
            type="text"
            placeholder="Enter your full name"
            value={details.fullName}
            onChange={(e) =>
              setDetails({ ...details, fullName: e.target.value })
            }
            className="w-full px-4 py-2.5 border border-border rounded-md text-sm text-black placeholder:text-neutral-400 bg-white focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-1 transition-shadow"
          />
        </div>

        {/* Account Type */}
        <div>
          <label className="block text-sm font-medium text-black mb-2">
            Account Type
          </label>
          <div className="flex gap-6">
            {(['salaried', 'business'] as AccountType[]).map((type) => (
              <label
                key={type}
                className="flex items-center gap-2 cursor-pointer group"
              >
                <input
                  type="radio"
                  name="accountType"
                  value={type}
                  checked={details.accountType === type}
                  onChange={() =>
                    setDetails({ ...details, accountType: type })
                  }
                  className="w-4 h-4 accent-black"
                />
                <span className="text-sm text-neutral-700 group-hover:text-black transition-colors capitalize">
                  {type}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Bank Name */}
        <div>
          <label
            htmlFor="bankName"
            className="block text-sm font-medium text-black mb-1.5"
          >
            Bank Name
          </label>
          <select
            id="bankName"
            value={details.bankName}
            onChange={(e) =>
              setDetails({
                ...details,
                bankName: e.target.value as BankName,
              })
            }
            className="w-full px-4 py-2.5 border border-border rounded-md text-sm bg-white text-black appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-1 transition-shadow"
          >
            <option value="" disabled>
              Select your bank
            </option>
            {BANKS.map(({ name, available }) => (
              <option key={name} value={available ? name : ''} disabled={!available}>
                {available ? name : `${name} — Coming Soon`}
              </option>
            ))}
          </select>
        </div>

        {/* Error */}
        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        {/* Continue Button */}
        <button
          onClick={handleSubmit}
          disabled={!isComplete}
          className="w-full py-2.5 bg-black text-white text-sm font-medium rounded-md hover:bg-neutral-800 disabled:bg-neutral-300 disabled:cursor-not-allowed transition-colors"
        >
          Continue
        </button>
      </div>
    </div>
  )
}
