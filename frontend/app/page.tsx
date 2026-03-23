'use client'

import { useState, useEffect } from 'react'
import Header from './components/Header'
import StepForm from './components/StepForm'
import UploadStep from './components/UploadStep'
import ModeSelection from './components/ModeSelection'
import ProcessingStep from './components/ProcessingStep'
import ResultStep from './components/ResultStep'
import { UserDetails, ProcessingResult, ProcessingMode, Step } from '@/types'
import { uploadStatement } from '@/lib/api'

const BANKS = [
  { name: 'HDFC Bank', available: true },
  { name: 'ICICI Bank', available: true },
  { name: 'Axis Bank', available: true },
  { name: 'Kotak Bank', available: true },
  { name: 'SBI', available: true },
  { name: 'HSBC Bank', available: false },
]

export default function Home() {
  const [step, setStep] = useState<Step>(1)
  const [userDetails, setUserDetails] = useState<UserDetails>({
    fullName: '',
    accountType: '',
    bankName: '',
  })
  const [file, setFile] = useState<File | null>(null)
  const [pdfPassword, setPdfPassword] = useState<string | undefined>(undefined)
  const [mode, setMode] = useState<ProcessingMode>('free')
  const [apiKey, setApiKey] = useState('')
  const [result, setResult] = useState<ProcessingResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  // Load saved form data on mount
  useEffect(() => {
    const savedData = localStorage.getItem('airco-form-data')
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData)
        setUserDetails(parsed.userDetails || {
          fullName: '',
          accountType: '',
          bankName: '',
        })
        setMode(parsed.mode || 'free')
        setApiKey(parsed.apiKey || '')
        setStep(parsed.step || 1)
      } catch (e) {
        console.error('Failed to load saved form data:', e)
      }
    }
  }, [])

  // Save form data on changes
  useEffect(() => {
    const dataToSave = {
      userDetails,
      mode,
      apiKey,
      step,
      timestamp: Date.now()
    }
    localStorage.setItem('airco-form-data', JSON.stringify(dataToSave))
  }, [userDetails, mode, apiKey, step])

  const handleUserDetails = (details: UserDetails) => {
    setUserDetails(details)
    setStep(2)
  }

  const handleFileSelected = (selectedFile: File, password?: string) => {
    setFile(selectedFile)
    setPdfPassword(password)
    setStep(3)
  }

  const handleModeSelect = async (selectedMode: ProcessingMode, key?: string) => {
    setMode(selectedMode)
    if (key) setApiKey(key)
    setIsProcessing(true)
    setError(null)
    setStep(4)

    try {
      const data = await uploadStatement(file!, userDetails, selectedMode, key, pdfPassword)
      setResult(data)
      setStep(5)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong. Please try again.'
      )
      setStep(3)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleBack = () => {
    if (step === 2) setStep(1)
    else if (step === 3) setStep(2)
    else if (step === 5) setStep(3)
  }

  const handleReset = () => {
    setStep(1)
    setUserDetails({ fullName: '', accountType: '', bankName: '' })
    setFile(null)
    setPdfPassword(undefined)
    setMode('free')
    setApiKey('')
    setResult(null)
    setError(null)
    setIsProcessing(false)
    // Clear saved data
    localStorage.removeItem('airco-form-data')
  }

  const stepLabels = ['Details', 'Upload', 'Mode', 'Processing', 'Report']

  return (
    <main className="min-h-screen bg-white">
      <div className="max-w-[960px] mx-auto px-6 pb-16">
        <Header />

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-1.5 mb-8">
          {[1, 2, 3, 4, 5].map((s) => (
            <div key={s} className="flex items-center gap-1.5">
              <div className="flex flex-col items-center">
                <div
                  className={`h-1 w-10 rounded-full transition-colors ${
                    s <= step ? 'bg-black' : 'bg-neutral-200'
                  }`}
                />
                <span className={`text-[9px] mt-1 ${
                  s <= step ? 'text-neutral-600' : 'text-neutral-300'
                }`}>
                  {stepLabels[s - 1]}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Card Container */}
        <div className="border border-border rounded-lg p-6 sm:p-8">
          {/* Error Banner */}
          {error && step !== 4 && (
            <div className="mb-6 px-4 py-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {step === 1 && <StepForm onSubmit={handleUserDetails} initialDetails={userDetails} />}

          {step === 2 && (
            <UploadStep onUpload={handleFileSelected} isProcessing={false} />
          )}

          {step === 3 && (
            <ModeSelection onSelect={handleModeSelect} isProcessing={isProcessing} />
          )}

          {step === 4 && <ProcessingStep mode={mode} />}

          {step === 5 && result && <ResultStep result={result} />}

          {/* Back / Forward Navigation */}
          {step !== 4 && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t border-neutral-100">
              {step > 1 ? (
                <button
                  onClick={handleBack}
                  className="text-sm text-neutral-500 hover:text-black flex items-center gap-1 transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
                  Back
                </button>
              ) : <div />}
              {step === 5 ? (
                <button
                  onClick={handleReset}
                  className="text-sm font-medium text-white bg-black hover:bg-neutral-800 px-4 py-2 rounded-md flex items-center gap-1 transition-colors"
                >
                  New Statement
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>
                </button>
              ) : <div />}
            </div>
          )}
        </div>

        {/* Footer with Legal Disclaimer */}
        <footer className="text-center mt-12 space-y-3">
          <p className="text-xs font-medium text-neutral-400">
            Airco Insights &mdash; Financial Categorization Engine
          </p>
          <p className="text-[11px] text-neutral-400 max-w-lg mx-auto leading-relaxed">
            Upload your bank statement PDF and get a fully categorized, structured Excel report &mdash;
            with monthly summaries, category breakdowns, recurring transaction detection, and weekly analysis.
            No data is stored. Processing happens in real time.
          </p>

          {/* Supported Banks */}
          <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
            {BANKS.map(({ name, available }) => (
              <span
                key={name}
                className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border ${
                  available
                    ? 'border-neutral-200 text-neutral-500 bg-neutral-50'
                    : 'border-dashed border-neutral-200 text-neutral-300 bg-white'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${
                  available ? 'bg-green-400' : 'bg-neutral-300'
                }`} />
                {name}
                {!available && <span className="text-[9px] text-neutral-300 ml-0.5">soon</span>}
              </span>
            ))}
          </div>

          <p className="text-[10px] text-neutral-300 max-w-md mx-auto leading-relaxed">
            Airco Insights does not provide financial advice, predictions, or recommendations.
            The system only categorizes and structures transaction data.
          </p>
        </footer>
      </div>
    </main>
  )
}
