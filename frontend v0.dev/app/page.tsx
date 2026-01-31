'use client'

import { useState, useMemo, useCallback } from 'react'
import { Search, Star, Play, Download, Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'
import { Toaster } from '@/components/ui/toaster'
import { TopNav } from '@/components/marketplace/top-nav'
import { FilterChips } from '@/components/marketplace/filter-chips'
import { ToolCard } from '@/components/marketplace/tool-card'
import { FeaturedWorkflows } from '@/components/marketplace/featured-workflows'
import { Footer } from '@/components/marketplace/footer'

export default function Page() {
  const { toast } = useToast()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFilters, setSelectedFilters] = useState<string[]>([])
  const [copiedId, setCopiedId] = useState<string | null>(null)

  // Mock data for tools
  const tools = [
    {
      id: '1',
      name: 'GitHub Integration',
      description: 'Connect your repositories and automate workflows with GitHub',
      icon: '🐙',
      rating: 4.8,
      reviews: 234,
      tags: ['#automation', '#github', '#devops'],
      installs: '1.2K',
      badges: ['github', 'slack'],
    },
    {
      id: '2',
      name: 'Slack Bot Builder',
      description: 'Build powerful Slack bots with natural language understanding',
      icon: '💬',
      rating: 4.9,
      reviews: 512,
      tags: ['#slack', '#automation', '#messaging'],
      installs: '3.5K',
      badges: ['slack', 'github'],
    },
    {
      id: '3',
      name: 'Data Analytics Suite',
      description: 'Real-time analytics and data visualization for your metrics',
      icon: '📊',
      rating: 4.7,
      reviews: 189,
      tags: ['#data', '#analytics', '#visualization'],
      installs: '892',
      badges: ['github'],
    },
    {
      id: '4',
      name: 'Email Automation',
      description: 'Automate email campaigns and notifications intelligently',
      icon: '✉️',
      rating: 4.6,
      reviews: 156,
      tags: ['#email', '#automation', '#marketing'],
      installs: '2.1K',
      badges: ['slack'],
    },
    {
      id: '5',
      name: 'Database Query Tool',
      description: 'Natural language SQL query generation and execution',
      icon: '🗄️',
      rating: 4.9,
      reviews: 445,
      tags: ['#database', '#data', '#apis'],
      installs: '2.8K',
      badges: ['github', 'slack'],
    },
    {
      id: '6',
      name: 'Web Scraper',
      description: 'Intelligent web scraping with automatic data structuring',
      icon: '🕷️',
      rating: 4.5,
      reviews: 203,
      tags: ['#data', '#web', '#apis'],
      installs: '1.6K',
      badges: ['github'],
    },
    {
      id: '7',
      name: 'Calendar Manager',
      description: 'Manage calendars and schedule meetings automatically',
      icon: '📅',
      rating: 4.7,
      reviews: 178,
      tags: ['#automation', '#calendar', '#productivity'],
      installs: '943',
      badges: ['slack'],
    },
    {
      id: '8',
      name: 'File Storage',
      description: 'Cloud file storage integration with smart organization',
      icon: '📁',
      rating: 4.8,
      reviews: 267,
      tags: ['#files', '#storage', '#cloud'],
      installs: '1.9K',
      badges: ['github', 'slack'],
    },
    {
      id: '9',
      name: 'Python Executor',
      description: 'Execute Python code safely with isolated environments',
      icon: '🐍',
      rating: 4.9,
      reviews: 334,
      tags: ['#python', '#automation', '#code'],
      installs: '2.3K',
      badges: ['github'],
    },
  ]

  const filterOptions = ['Popular', 'Recently Added', 'Data', 'APIs', 'Automation', 'Files']

  // Filter tools based on search and selected filters
  const filteredTools = useMemo(() => {
    return tools.filter((tool) => {
      const matchesSearch = tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tool.description.toLowerCase().includes(searchQuery.toLowerCase())
      
      if (selectedFilters.length === 0) return matchesSearch
      
      return matchesSearch && selectedFilters.some(filter => {
        if (filter === 'Popular') return tool.rating >= 4.7
        if (filter === 'Recently Added') return true
        return tool.tags.some(tag => tag.toLowerCase().includes(filter.toLowerCase()))
      })
    })
  }, [searchQuery, selectedFilters])

  const handleFilterToggle = useCallback((filter: string) => {
    setSelectedFilters(prev => 
      prev.includes(filter) 
        ? prev.filter(f => f !== filter)
        : [...prev, filter]
    )
  }, [])

  const handleCopyInstall = useCallback((toolId: string, toolName: string) => {
    const command = `npm install @daagent/${toolName.toLowerCase().replace(/\s+/g, '-')}`
    navigator.clipboard.writeText(command)
    setCopiedId(toolId)
    toast({
      title: 'Copied!',
      description: 'Installation command copied to clipboard',
    })
    setTimeout(() => setCopiedId(null), 2000)
  }, [toast])

  return (
    <div className="min-h-screen bg-background">
      <TopNav />
      
      {/* Hero Section */}
      <section className="border-b border-border bg-gradient-to-b from-card to-background">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold tracking-tight text-foreground mb-4">
              Discover AI Agent Tools
            </h1>
            <p className="text-lg text-muted-foreground mb-8">
              Access 1,000+ MCP tools and integrations to power your agent platform
            </p>
          </div>
          
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-4 top-3 h-5 w-5 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search 1,000+ MCP tools..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-11 h-12 text-base"
            />
          </div>
        </div>
      </section>

      {/* Filter Chips */}
      <section className="sticky top-16 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6 lg:px-8">
          <FilterChips
            options={filterOptions}
            selected={selectedFilters}
            onToggle={handleFilterToggle}
          />
        </div>
      </section>

      {/* Main Content */}
      <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        {/* Tool Grid */}
        <div className="mb-16">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {filteredTools.map((tool) => (
              <ToolCard
                key={tool.id}
                tool={tool}
                onInstall={handleCopyInstall}
                isCopied={copiedId === tool.id}
              />
            ))}
          </div>
          
          {filteredTools.length === 0 && (
            <div className="text-center py-12">
              <p className="text-lg text-muted-foreground">
                No tools found matching your search
              </p>
            </div>
          )}
        </div>

        {/* Featured Workflows */}
        <FeaturedWorkflows />
      </main>

      {/* Footer */}
      <Footer />
      
      <Toaster />
    </div>
  )
}
