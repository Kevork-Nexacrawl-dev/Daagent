'use client';

import { useState, useEffect } from 'react';
import { FileUploader } from 'react-drag-drop-files';
import { DndContext, closestCenter, DragEndEvent } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Card } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion';

interface PromptLayer {
  name: string;
  priority: number;
  content: string;
  description: string;
  mode: 'stackable' | 'hierarchical';
  priority_group: string;
  filePath: string;
  enabled: boolean;
}

function SortablePromptCard({ layer, onToggle }: { layer: PromptLayer; onToggle: (name: string) => void }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: layer.name });

  return (
    <Card
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className="p-4 mb-2"
    >
      <div className="flex items-center gap-4">
        <div {...attributes} {...listeners} className="cursor-grab">
          ☰
        </div>

        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold">{layer.name}</span>
            <Badge variant={layer.mode === 'stackable' ? 'default' : 'secondary'}>
              {layer.mode}
            </Badge>
            <span className="text-sm text-gray-400">Priority: {layer.priority}</span>
            <Badge variant="outline">{layer.priority_group}</Badge>
          </div>
          <p className="text-sm text-gray-500 mt-1">{layer.description}</p>
        </div>

        <Switch checked={layer.enabled} onCheckedChange={() => onToggle(layer.name)} />
      </div>
    </Card>
  );
}

export default function PromptsPage() {
  const [promptLayers, setPromptLayers] = useState<PromptLayer[]>([]);
  const [composedPrompt, setComposedPrompt] = useState('');

  useEffect(() => {
    fetchLayers();
  }, []);

  const fetchLayers = async () => {
    const res = await fetch('/api/prompts');
    const data = await res.json();
    setPromptLayers(data.layers);
  };

  const handleFileUpload = async (files: File | File[]) => {
    const fileArray = Array.isArray(files) ? files : [files];
    const formData = new FormData();
    for (const file of fileArray) {
      formData.append('files', file);
    }
    await fetch('/api/prompts', {
      method: 'POST',
      body: formData,
    });
    fetchLayers();
  };

  const toggleLayer = (name: string) => {
    setPromptLayers(layers =>
      layers.map(layer =>
        layer.name === name ? { ...layer, enabled: !layer.enabled } : layer
      )
    );
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = promptLayers.findIndex(layer => layer.name === active.id);
    const newIndex = promptLayers.findIndex(layer => layer.name === over.id);

    const newLayers = [...promptLayers];
    const [moved] = newLayers.splice(oldIndex, 1);
    newLayers.splice(newIndex, 0, moved);

    // Update priorities based on new order
    const updatedLayers = newLayers.map((layer, index) => ({
      ...layer,
      priority: index + 1, // Simple priority assignment
    }));

    setPromptLayers(updatedLayers);

    // Save to backend
    for (const layer of updatedLayers) {
      await fetch('/api/prompts', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filePath: layer.filePath, newPriority: layer.priority }),
      });
    }
  };

  useEffect(() => {
    const updateComposed = async () => {
      const enabledLayers = promptLayers.filter(p => p.enabled).map(p => p.filePath);
      const res = await fetch('/api/prompts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'compose', enabledLayers }),
      });
      const data = await res.json();
      setComposedPrompt(data.composed);
    };
    if (promptLayers.length) updateComposed();
  }, [promptLayers]);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(composedPrompt);
  };

  const applyToSession = () => {
    // TODO: Implement apply to session
    alert('Apply to session not implemented yet');
  };

  const groupedLayers = promptLayers.reduce((acc, layer) => {
    const group = layer.priority_group;
    if (!acc[group]) acc[group] = [];
    acc[group].push(layer);
    return acc;
  }, {} as { [key: string]: PromptLayer[] });

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Prompt Management Dashboard</h1>

      <div className="mb-6">
        <FileUploader
          handleChange={handleFileUpload}
          name="prompt"
          types={["YAML", "YML"]}
          multiple={true}
          label="Drag YAML prompt files here or click to browse"
        />
      </div>

      <DndContext onDragEnd={handleDragEnd} collisionDetection={closestCenter}>
        <Accordion type="multiple">
          {Object.entries(groupedLayers).map(([group, layers]) => (
            <AccordionItem key={group} value={group}>
              <AccordionTrigger>{group} ({layers.length} layers)</AccordionTrigger>
              <AccordionContent>
                <SortableContext items={layers.map(p => p.name)} strategy={verticalListSortingStrategy}>
                  {layers.map((layer) => (
                    <SortablePromptCard key={layer.name} layer={layer} onToggle={toggleLayer} />
                  ))}
                </SortableContext>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </DndContext>

      <Card className="p-4 bg-gray-950 mt-6">
        <h3 className="text-lg font-semibold mb-2">Live Composed Prompt</h3>
        <pre className="text-sm text-gray-300 whitespace-pre-wrap max-h-96 overflow-y-auto">
          {composedPrompt}
        </pre>
        <div className="flex gap-2 mt-4">
          <Button onClick={copyToClipboard}>Copy Prompt</Button>
          <Button onClick={applyToSession} variant="outline">Apply to Current Session</Button>
        </div>
      </Card>
    </div>
  );
}