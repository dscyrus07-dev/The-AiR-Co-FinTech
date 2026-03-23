'use client'

import Image from 'next/image'

export default function Header() {
  return (
    <header className="w-full pt-10 pb-6 text-center">
      <div className="flex items-center justify-center gap-3 mb-2">
        <Image
          src="/logo.png"
          alt="Airco Insights"
          width={36}
          height={36}
          className="rounded"
        />
        <h1 className="text-2xl font-semibold tracking-tight text-black">
          Airco Insights
        </h1>
      </div>
      <p className="text-sm text-neutral-500 tracking-wide">
        Financial Categorization Engine
      </p>
    </header>
  )
}
