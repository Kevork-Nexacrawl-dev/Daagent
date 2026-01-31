'use client'

import { useState } from 'react'
import { Moon, Sun, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTheme } from 'next-themes'

export function TopNav() {
  const { theme, setTheme } = useTheme()
  
  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex-shrink-0">
            <a href="/" className="text-2xl font-bold bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
              Daagent
            </a>
          </div>
          
          {/* Center Navigation */}
          <div className="hidden md:flex items-center space-x-1">
            <Button variant="ghost" className="text-foreground">
              Explore
            </Button>
            <Button variant="ghost" className="text-foreground">
              Docs
            </Button>
          </div>
          
          {/* Right Actions */}
          <div className="flex items-center space-x-4">
            <Button variant="outline" className="hidden sm:inline-flex bg-transparent">
              Create Tool
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="text-foreground"
            >
              {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="text-foreground"
            >
              <User className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>
    </nav>
  )
}
