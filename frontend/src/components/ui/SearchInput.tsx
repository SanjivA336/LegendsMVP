import { useState, useEffect, useRef } from 'react'

interface SearchInputProps {
  placeholder?: string
  onChange: (value: string) => void
  debounceMs?: number
}

export default function SearchInput({
  placeholder = 'Search...',
  onChange,
  debounceMs = 200,
}: SearchInputProps) {
  const [value, setValue] = useState('')
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => onChange(value), debounceMs)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [value, onChange, debounceMs])

  return (
    <input
      type="text"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 placeholder-zinc-500 px-3 py-1.5 rounded-lg text-sm focus:outline-none focus:border-accent transition-colors duration-150"
    />
  )
}
