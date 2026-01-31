'use client'

import { Github, MessageCircle, BookOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function Footer() {
  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand */}
          <div>
            <h3 className="text-lg font-bold bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent mb-4">
              Daagent
            </h3>
            <p className="text-sm text-muted-foreground">
              The open platform for building and sharing AI agent tools
            </p>
          </div>
          
          {/* Product */}
          <div>
            <h4 className="font-semibold text-foreground mb-4">Product</h4>
            <ul className="space-y-2">
              <li><a href="#" className="text-sm text-muted-foreground hover:text-foreground">Marketplace</a></li>
              <li><a href="#" className="text-sm text-muted-foreground hover:text-foreground">Create Tool</a></li>
              <li><a href="#" className="text-sm text-muted-foreground hover:text-foreground">Workflows</a></li>
              <li><a href="#" className="text-sm text-muted-foreground hover:text-foreground">API</a></li>
            </ul>
          </div>
          
          {/* Resources */}
          <div>
            <h4 className="font-semibold text-foreground mb-4">Resources</h4>
            <ul className="space-y-2">
              <li><a href="#" className="text-sm text-muted-foreground hover:text-foreground">Documentation</a></li>
              <li><a href="#" className="text-sm text-muted-foreground hover:text-foreground">Guides</a></li>
              <li><a href="#" className="text-sm text-muted-foreground hover:text-foreground">Examples</a></li>
              <li><a href="#" className="text-sm text-muted-foreground hover:text-foreground">Support</a></li>
            </ul>
          </div>
          
          {/* Community */}
          <div>
            <h4 className="font-semibold text-foreground mb-4">Community</h4>
            <div className="flex gap-2">
              <Button variant="outline" size="icon" className="h-9 w-9 bg-transparent">
                <Github className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" className="h-9 w-9 bg-transparent">
                <MessageCircle className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" className="h-9 w-9 bg-transparent">
                <BookOpen className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
        
        {/* Bottom Section */}
        <div className="border-t border-border pt-8 flex flex-col md:flex-row items-center justify-between">
          <p className="text-sm text-muted-foreground">
            © 2024 Daagent. All rights reserved.
          </p>
          <div className="flex gap-6 mt-4 md:mt-0">
            <a href="#" className="text-sm text-muted-foreground hover:text-foreground">Privacy</a>
            <a href="#" className="text-sm text-muted-foreground hover:text-foreground">Terms</a>
            <a href="#" className="text-sm text-muted-foreground hover:text-foreground">Pricing</a>
          </div>
        </div>
      </div>
    </footer>
  )
}
