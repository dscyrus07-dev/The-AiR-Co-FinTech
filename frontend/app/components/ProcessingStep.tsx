'use client'

import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { ProcessingMode } from '@/types'

const FREE_MESSAGES = [
  'Extracting transactions…',
  'Detecting bank format…',
  'Running rule engine…',
  'Categorizing transactions…',
  'Detecting recurring patterns…',
  'Generating structured report…',
]

const HYBRID_MESSAGES = [
  'Extracting transactions…',
  'Detecting bank format…',
  'Running rule engine…',
  'Classifying with AI…',
  'Validating AI categories…',
  'Detecting recurring patterns…',
  'Generating structured report…',
]

interface ProcessingStepProps {
  mode?: ProcessingMode
}

export default function ProcessingStep({ mode = 'free' }: ProcessingStepProps) {
  const [messageIndex, setMessageIndex] = useState(0)
  const messages = mode === 'hybrid' ? HYBRID_MESSAGES : FREE_MESSAGES

  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % messages.length)
    }, 2500)
    return () => clearInterval(interval)
  }, [messages.length])

  return (
    <div className="animate-fade-in flex flex-col items-center justify-center py-16">
      <Loader2 className="w-10 h-10 text-black animate-spin mb-6" />
      <p className="text-sm font-medium text-black animate-pulse-text">
        {messages[messageIndex]}
      </p>
      <p className="text-xs text-neutral-400 mt-3">
        This may take a moment depending on statement size.
      </p>
      <div className="mt-4 px-3 py-1 bg-neutral-50 border border-neutral-200 rounded-full">
        <span className="text-[10px] text-neutral-500 font-medium">
          {mode === 'hybrid' ? 'System + AI Mode' : 'Free Mode (System Only)'}
        </span>
      </div>
    </div>
  )
}
