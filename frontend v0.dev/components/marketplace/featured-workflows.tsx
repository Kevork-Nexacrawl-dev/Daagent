'use client'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ChevronRight } from 'lucide-react'

interface Workflow {
  id: string
  name: string
  tools: string[]
  toolIcons: string[]
}

export function FeaturedWorkflows() {
  const workflows: Workflow[] = [
    {
      id: '1',
      name: 'GitHub to Slack Notifications',
      tools: ['GitHub', 'Slack'],
      toolIcons: ['🐙', '💬'],
    },
    {
      id: '2',
      name: 'Data Pipeline Automation',
      tools: ['Data Analytics', 'Database', 'Slack'],
      toolIcons: ['📊', '🗄️', '💬'],
    },
    {
      id: '3',
      name: 'Email Campaign Manager',
      tools: ['Email', 'Database', 'Analytics'],
      toolIcons: ['✉️', '🗄️', '📊'],
    },
    {
      id: '4',
      name: 'Content Scraper & Storage',
      tools: ['Web Scraper', 'File Storage', 'Database'],
      toolIcons: ['🕷️', '📁', '🗄️'],
    },
  ]
  
  return (
    <section className="py-12 border-t border-border">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Featured Workflows
        </h2>
        <p className="text-muted-foreground">
          Pre-built workflows combining multiple tools for common tasks
        </p>
      </div>
      
      <div className="overflow-x-auto pb-4">
        <div className="flex gap-4 min-w-max">
          {workflows.map((workflow) => (
            <Card key={workflow.id} className="w-80 flex-shrink-0 hover:shadow-lg transition-shadow duration-200">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-foreground mb-4">
                  {workflow.name}
                </h3>
                
                {/* Tool Icons */}
                <div className="flex items-center gap-2 mb-6">
                  {workflow.toolIcons.map((icon, idx) => (
                    <div key={idx} className="flex items-center">
                      <span className="text-2xl">{icon}</span>
                      {idx < workflow.toolIcons.length - 1 && (
                        <ChevronRight className="h-4 w-4 mx-2 text-muted-foreground" />
                      )}
                    </div>
                  ))}
                </div>
                
                {/* Fork Button */}
                <Button className="w-full bg-purple-500 hover:bg-purple-600 text-white">
                  Fork Workflow
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
