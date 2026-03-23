'use client'

import { Download, FileSpreadsheet, FileText } from 'lucide-react'

interface DownloadButtonsProps {
  excelUrl: string
  pdfUrl?: string
}

export default function DownloadButtons({
  excelUrl,
  pdfUrl,
}: DownloadButtonsProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-3 mt-8">
      <a
        href={excelUrl}
        download
        className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-black text-white text-sm font-medium rounded-md hover:bg-neutral-800 transition-colors"
      >
        <FileSpreadsheet className="w-4 h-4" />
        Download Excel
      </a>

      {pdfUrl && (
        <a
          href={pdfUrl}
          download
          className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 border border-border text-black text-sm font-medium rounded-md hover:bg-neutral-50 transition-colors"
        >
          <FileText className="w-4 h-4" />
          Download PDF
        </a>
      )}
    </div>
  )
}
