'use client'

import { useState } from 'react'
import { MessageSquare, Send, CheckCircle } from 'lucide-react'

interface FeedbackSectionProps {
  onFeedbackSubmit?: (transactionId: string, correctedCategory: string) => void
}

export default function FeedbackSection({ onFeedbackSubmit }: FeedbackSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [transactionId, setTransactionId] = useState('')
  const [correctedCategory, setCorrectedCategory] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const categories = [
    'Shopping',
    'Food & Dining',
    'Transport',
    'Utilities',
    'Bill Payment',
    'ATM Withdrawal',
    'Bank Transfer Debit',
    'Bank Transfer Credit',
    'UPI Payment',
    'UPI Credit',
    'Salary',
    'Investment',
    'Loan EMI',
    'Rent',
    'Entertainment',
    'Others'
  ]

  const handleSubmit = async () => {
    if (!transactionId || !correctedCategory) return

    setIsSubmitting(true)
    try {
      // Send to WhatsApp
      const whatsappMessage = `📊 *Feedback from Airco Insights*\n\n🔹 *Issue Type:* ${transactionId}\n🔹 *Category:* ${correctedCategory}\n🔹 *Time:* ${new Date().toLocaleString()}\n\n_Thank you for helping us improve!_`
      
      // Create WhatsApp URL
      const whatsappUrl = `https://wa.me/917021320783?text=${encodeURIComponent(whatsappMessage)}`
      
      // Open WhatsApp in new tab
      window.open(whatsappUrl, '_blank')
      
      setSubmitted(true)
      onFeedbackSubmit?.(transactionId, correctedCategory)
      
      // Reset form after 3 seconds
      setTimeout(() => {
        setSubmitted(false)
        setTransactionId('')
        setCorrectedCategory('')
      }, 3000)
    } catch (error) {
      console.error('Feedback submission failed:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-center gap-2 text-green-700">
          <CheckCircle className="w-4 h-4" />
          <span className="text-sm font-medium">Feedback submitted successfully!</span>
        </div>
        <p className="text-xs text-green-600 mt-1">
          Your correction helps improve the system accuracy.
        </p>
      </div>
    )
  }

  return (
    <div className="mt-6 border-t border-neutral-100 pt-6">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-sm text-neutral-600 hover:text-black transition-colors"
      >
        <MessageSquare className="w-4 h-4" />
        {isExpanded ? 'Hide' : 'Show'} Feedback Options
      </button>

      {isExpanded && (
        <div className="mt-4 p-6 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl shadow-sm">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full mb-3">
              <MessageSquare className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Please provide your valuable feedback
            </h3>
            <p className="text-sm text-gray-600 max-w-md mx-auto">
              so we make our system more better and perfect for you
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                What type of problem is faced?
              </label>
              <input
                type="text"
                value={transactionId}
                onChange={(e) => setTransactionId(e.target.value)}
                placeholder="e.g., Wrong categorization, Missing transaction, etc."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <select
                value={correctedCategory}
                onChange={(e) => setCorrectedCategory(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              >
                <option value="">Select category</option>
                {categories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleSubmit}
              disabled={!transactionId || !correctedCategory || isSubmitting}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-medium rounded-lg hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-400 disabled:cursor-not-allowed transition-all transform hover:scale-[1.02] active:scale-[0.98]"
            >
              {isSubmitting ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Submitting...
                </div>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Submit Feedback
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
