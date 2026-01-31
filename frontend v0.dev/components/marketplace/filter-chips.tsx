'use client'

import { Button } from '@/components/ui/button'

interface FilterChipsProps {
  options: string[]
  selected: string[]
  onToggle: (filter: string) => void
}

export function FilterChips({ options, selected, onToggle }: FilterChipsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const isSelected = selected.includes(option)
        return (
          <Button
            key={option}
            onClick={() => onToggle(option)}
            variant={isSelected ? 'default' : 'outline'}
            className="rounded-full"
            size="sm"
          >
            {option}
          </Button>
        )
      })}
    </div>
  )
}
