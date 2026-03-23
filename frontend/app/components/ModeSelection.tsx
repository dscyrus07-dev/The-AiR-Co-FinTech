'use client'

import { useState } from 'react'
import { Zap, Brain, Lock, Eye, EyeOff, Shield } from 'lucide-react'
import { ProcessingMode } from '@/types'

interface ModeSelectionProps {
  onSelect: (mode: ProcessingMode, apiKey?: string) => void
  isProcessing: boolean
}

export default function ModeSelection({ onSelect, isProcessing }: ModeSelectionProps) {
  const [selectedMode, setSelectedMode] = useState<ProcessingMode | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleContinue = () => {
    if (!selectedMode) return

    if (selectedMode === 'hybrid') {
      if (!apiKey.trim()) {
        setError('Please enter your Anthropic API key.')
        return
      }
      if (!apiKey.trim().startsWith('sk-')) {
        setError('API key should start with "sk-". Please check your key.')
        return
      }
    }

    setError(null)
    onSelect(selectedMode, selectedMode === 'hybrid' ? apiKey.trim() : undefined)
  }

  return (
    <div className="animate-fade-in">
      <h2 className="text-lg font-semibold text-black mb-1">
        Choose Processing Mode
      </h2>
      <p className="text-sm text-neutral-500 mb-6">
        Select how you want your transactions to be categorized.
      </p>

      <div className="space-y-3">
        {/* Free Mode Card */}
        <button
          onClick={() => { setSelectedMode('free'); setError(null) }}
          className={`w-full text-left p-5 rounded-lg border-2 transition-all ${
            selectedMode === 'free'
              ? 'border-black bg-neutral-50'
              : 'border-border hover:border-neutral-300'
          }`}
        >
          <div className="flex items-start gap-3">
            <div className="mt-0.5">
              <Zap className={`w-5 h-5 ${selectedMode === 'free' ? 'text-black' : 'text-neutral-400'}`} />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-black">Free Mode</span>
                <span className="text-[10px] font-medium text-neutral-500 bg-neutral-100 px-1.5 py-0.5 rounded">
                  SYSTEM ONLY
                </span>
              </div>
              <p className="text-xs text-neutral-500 leading-relaxed">
                Coordinate-based PDF parser + deterministic rule engine.
                No AI, no API cost. 100% accurate transaction extraction with strict keyword categorization.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="text-[10px] text-neutral-400 bg-neutral-50 border border-neutral-200 px-2 py-0.5 rounded">
                  Categorized Transactions
                </span>
                <span className="text-[10px] text-neutral-400 bg-neutral-50 border border-neutral-200 px-2 py-0.5 rounded">
                  Monthly Totals
                </span>
                <span className="text-[10px] text-neutral-400 bg-neutral-50 border border-neutral-200 px-2 py-0.5 rounded">
                  Weekly Split
                </span>
                <span className="text-[10px] text-neutral-400 bg-neutral-50 border border-neutral-200 px-2 py-0.5 rounded">
                  Recurring Split
                </span>
                <span className="text-[10px] text-neutral-400 bg-neutral-50 border border-neutral-200 px-2 py-0.5 rounded">
                  5-Sheet Excel
                </span>
              </div>
              <p className="text-[10px] text-neutral-400 mt-2">
                UPI transactions classified generically. Ambiguous merchants remain in Others.
              </p>
            </div>
          </div>
        </button>

        {/* Hybrid Mode Card */}
        <button
          onClick={() => { setSelectedMode('hybrid'); setError(null) }}
          className={`w-full text-left p-5 rounded-lg border-2 transition-all ${
            selectedMode === 'hybrid'
              ? 'border-black bg-neutral-50'
              : 'border-border hover:border-neutral-300'
          }`}
        >
          <div className="flex items-start gap-3">
            <div className="mt-0.5">
              <Brain className={`w-5 h-5 ${selectedMode === 'hybrid' ? 'text-black' : 'text-neutral-400'}`} />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-black">Hybrid Mode</span>
                <span className="text-[10px] font-medium text-neutral-500 bg-neutral-100 px-1.5 py-0.5 rounded">
                  SYSTEM + AI
                </span>
              </div>
              <p className="text-xs text-neutral-500 leading-relaxed">
                Uses deterministic rule engine + Claude AI for ambiguous transactions.
                Higher categorization accuracy. No financial insights or analysis.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="text-[10px] text-neutral-400 bg-neutral-50 border border-neutral-200 px-2 py-0.5 rounded">
                  Everything in Free
                </span>
                <span className="text-[10px] text-black bg-neutral-100 border border-neutral-300 px-2 py-0.5 rounded font-medium">
                  + AI Classification
                </span>
                <span className="text-[10px] text-black bg-neutral-100 border border-neutral-300 px-2 py-0.5 rounded font-medium">
                  + Higher Accuracy
                </span>
              </div>
              <p className="text-[10px] text-neutral-400 mt-2">
                Requires Anthropic API key. Cost shown before execution. Max 300 AI transactions per PDF.
              </p>
            </div>
          </div>
        </button>
      </div>

      {/* API Key Input — only when Hybrid selected */}
      {selectedMode === 'hybrid' && (
        <div className="mt-5 animate-fade-in">
          <label
            htmlFor="apiKey"
            className="block text-sm font-medium text-black mb-1.5"
          >
            Anthropic API Key
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <input
              id="apiKey"
              type={showKey ? 'text' : 'password'}
              placeholder="sk-ant-api03-..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full pl-9 pr-10 py-2.5 border border-border rounded-md text-sm text-black placeholder:text-neutral-400 bg-white focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-1 transition-shadow font-mono"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-black transition-colors"
              aria-label={showKey ? 'Hide key' : 'Show key'}
            >
              {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <p className="text-[10px] text-neutral-400 mt-1.5 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            Your API key is sent directly to Anthropic. It is never stored.
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-sm text-red-600 mt-3" role="alert">
          {error}
        </p>
      )}

      {/* Continue Button */}
      <button
        onClick={handleContinue}
        disabled={!selectedMode || isProcessing}
        className="w-full mt-6 py-2.5 bg-black text-white text-sm font-medium rounded-md hover:bg-neutral-800 disabled:bg-neutral-300 disabled:cursor-not-allowed transition-colors"
      >
        {isProcessing
          ? 'Processing...'
          : selectedMode === 'hybrid'
            ? 'Continue with Hybrid Mode'
            : selectedMode === 'free'
              ? 'Continue with Free Mode'
              : 'Select a Mode'}
      </button>

      {/* Legal Disclaimer */}
      <div className="mt-5 p-3 bg-neutral-50 border border-neutral-200 rounded-md">
        <p className="text-[10px] text-neutral-500 leading-relaxed text-center">
          Airco Insights does not provide financial advice, predictions, or recommendations.
          The system only categorizes and structures transaction data.
        </p>
      </div>
    </div>
  )
}
