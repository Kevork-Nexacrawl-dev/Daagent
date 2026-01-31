'use client'

import { useState } from 'react'
import { Play, Download, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent } from '@/components/ui/dialog'

interface Tool {
  id: string
  name: string
  description: string
  icon: string
  rating: number
  reviews: number
  tags: string[]
  installs: string
  badges: string[]
}

interface ToolCardProps {
  tool: Tool
  onInstall: (toolId: string, toolName: string) => void
  isCopied: boolean
}

export function ToolCard({ tool, onInstall, isCopied }: ToolCardProps) {
  const [showPreview, setShowPreview] = useState(false)
  
  const integrationIcons: Record<string, string> = {
    github: '🐙',
    slack: '💬',
  }
  
  return (
    <>
      <Card className="overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-200 cursor-pointer group">
        <div className="p-6">
          {/* Header with icon and rating */}
          <div className="flex items-start justify-between mb-4">
            <div className="text-4xl">{tool.icon}</div>
            <div className="flex items-center gap-1 bg-yellow-50 dark:bg-yellow-950 px-3 py-1 rounded-full">
              <span className="text-yellow-500">⭐</span>
              <span className="text-sm font-semibold text-foreground">
                {tool.rating}
              </span>
              <span className="text-sm text-muted-foreground">
                ({tool.reviews})
              </span>
            </div>
          </div>
          
          {/* Tool info */}
          <h3 className="text-lg font-bold text-foreground mb-2">
            {tool.name}
          </h3>
          <p className="text-sm text-muted-foreground line-clamp-2 mb-6">
            {tool.description}
          </p>
          
          {/* Action Buttons */}
          <div className="flex gap-2 mb-6">
            <Button
              onClick={() => setShowPreview(true)}
              size="sm"
              className="flex-1 bg-blue-500 hover:bg-blue-600 text-white"
            >
              <Play className="h-4 w-4 mr-2" />
              Live Preview
            </Button>
            <Button
              onClick={() => onInstall(tool.id, tool.name)}
              variant="outline"
              size="sm"
              className="flex-1"
            >
              {isCopied ? (
                <>
                  <Check className="h-4 w-4 mr-2" />
                  Copied
                </>
              ) : (
                <>
                  <Download className="h-4 w-4 mr-2" />
                  Install
                </>
              )}
            </Button>
          </div>
          
          {/* Tags */}
          <div className="flex flex-wrap gap-2 mb-4">
            {tool.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
          
          {/* Footer */}
          <div className="flex items-center justify-between pt-4 border-t border-border">
            <div className="flex items-center gap-2">
              {tool.badges.map((badge) => (
                <span key={badge} className="text-xl" title={badge}>
                  {integrationIcons[badge] || badge}
                </span>
              ))}
            </div>
            <span className="text-xs text-muted-foreground">
              {tool.installs} installs
            </span>
          </div>
        </div>
      </Card>
      
      {/* Preview Modal */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent className="max-w-4xl h-96">
          <div className="w-full h-full flex items-center justify-center bg-muted rounded-lg">
            <div className="text-center">
              <div className="text-6xl mb-4">{tool.icon}</div>
              <h3 className="text-2xl font-bold text-foreground mb-2">
                {tool.name}
              </h3>
              <p className="text-muted-foreground mb-6">
                {tool.description}
              </p>
              <p className="text-sm text-muted-foreground">
                Interactive preview would load here in production
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
