'use client'

import { useState, useRef, DragEvent } from 'react'
import { Upload, FileText, X, Lock, Eye, EyeOff } from 'lucide-react'
import { validateFile } from '@/lib/validation'

interface UploadStepProps {
  onUpload: (file: File, password?: string) => void
  isProcessing: boolean
}

export default function UploadStep({ onUpload, isProcessing }: UploadStepProps) {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isLocked, setIsLocked] = useState(false)
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isCheckingPdf, setIsCheckingPdf] = useState(false)
  const [tempPath, setTempPath] = useState<string | null>(null)
  const [isUnlocking, setIsUnlocking] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = async (selected: File) => {
    const validationError = validateFile(selected)
    if (validationError) {
      setError(validationError)
      setFile(null)
      return
    }
    setError(null)
    setFile(selected)
    setIsLocked(false)
    setPassword('')
    setTempPath(null)
    
    // Check if PDF is password-protected
    setIsCheckingPdf(true)
    try {
      const formData = new FormData()
      formData.append('file', selected)
      
      const response = await fetch('/api/check-pdf', {
        method: 'POST',
        body: formData,
      })
      
      const data = await response.json()
      
      if (data.is_locked) {
        setIsLocked(true)
        setTempPath(data.temp_path)
        setError('This PDF is password-protected. Please enter the password to continue.')
      }
    } catch (err) {
      console.error('Error checking PDF:', err)
      // Continue without password check if it fails
    } finally {
      setIsCheckingPdf(false)
    }
  }

  const handleUnlock = async () => {
    if (!tempPath || !password) return
    
    setIsUnlocking(true)
    setError(null)
    
    try {
      const formData = new FormData()
      formData.append('temp_path', tempPath)
      formData.append('password', password)
      
      const response = await fetch('/api/unlock-pdf', {
        method: 'POST',
        body: formData,
      })
      
      const data = await response.json()
      
      if (data.success) {
        setIsLocked(false)
        setError(null)
        // Create a new File object with the decrypted path info
        // The actual file will be processed from the decrypted path
        setTempPath(data.decrypted_path)
      } else {
        setError(data.error || 'Incorrect password. Please try again.')
      }
    } catch (err) {
      setError('Failed to unlock PDF. Please try again.')
    } finally {
      setIsUnlocking(false)
    }
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) handleFile(dropped)
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) handleFile(selected)
  }

  const clearFile = () => {
    setFile(null)
    setError(null)
    setIsLocked(false)
    setPassword('')
    setTempPath(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const handleSubmit = () => {
    if (file) onUpload(file, password || undefined)
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="animate-fade-in">
      <h2 className="text-lg font-semibold text-black mb-1">
        Upload Bank Statement PDF
      </h2>
      <p className="text-sm text-neutral-500 mb-6">
        We accept PDF bank statements up to 20MB.
      </p>

      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        className={`
          relative border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors
          ${isDragging ? 'border-black bg-neutral-50' : 'border-border hover:border-neutral-400'}
          ${file ? 'border-black' : ''}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          onChange={handleChange}
          className="hidden"
        />

        {!file ? (
          <div className="flex flex-col items-center gap-3">
            <Upload className="w-8 h-8 text-neutral-400" />
            <div>
              <p className="text-sm font-medium text-black">
                Drag & drop your PDF here
              </p>
              <p className="text-xs text-neutral-400 mt-1">
                or click to browse
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-black" />
              <div className="text-left">
                <p className="text-sm font-medium text-black truncate max-w-[300px]">
                  {file.name}
                </p>
                <p className="text-xs text-neutral-400">
                  {formatSize(file.size)}
                </p>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation()
                clearFile()
              }}
              className="p-1 hover:bg-neutral-100 rounded transition-colors"
              aria-label="Remove file"
            >
              <X className="w-4 h-4 text-neutral-500" />
            </button>
          </div>
        )}
      </div>

      {/* Password Input for Locked PDFs */}
      {isLocked && file && (
        <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-center gap-2 mb-3">
            <Lock className="w-4 h-4 text-amber-600" />
            <span className="text-sm font-medium text-amber-800">
              Password Protected PDF
            </span>
          </div>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter PDF password"
                className="w-full px-3 py-2 text-sm border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent pr-10"
                onKeyDown={(e) => e.key === 'Enter' && handleUnlock()}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <button
              onClick={handleUnlock}
              disabled={!password || isUnlocking}
              className="px-4 py-2 bg-amber-600 text-white text-sm font-medium rounded-md hover:bg-amber-700 disabled:bg-neutral-300 disabled:cursor-not-allowed transition-colors"
            >
              {isUnlocking ? 'Unlocking...' : 'Unlock'}
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && !isLocked && (
        <p className="text-sm text-red-600 mt-3" role="alert">
          {error}
        </p>
      )}

      {/* Checking PDF Status */}
      {isCheckingPdf && (
        <p className="text-sm text-neutral-500 mt-3">
          Checking PDF status...
        </p>
      )}

      {/* Process Button */}
      <button
        onClick={handleSubmit}
        disabled={!file || isProcessing || isLocked || isCheckingPdf}
        className="w-full mt-6 py-2.5 bg-black text-white text-sm font-medium rounded-md hover:bg-neutral-800 disabled:bg-neutral-300 disabled:cursor-not-allowed transition-colors"
      >
        {isProcessing ? 'Processing…' : isCheckingPdf ? 'Checking PDF...' : 'Process Statement'}
      </button>

    </div>
  )
}
