import React, { useEffect, useState } from 'react';
import { Persona, ChatConfig } from '../types.ts';
import { XIcon, TrashIcon, RefreshIcon, UserIcon } from './Icons.tsx';
import { api } from '../services/api.ts';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  config: ChatConfig;
  setConfig: React.Dispatch<React.SetStateAction<ChatConfig>>;
  personas: Persona[];
  setPersonas: React.Dispatch<React.SetStateAction<Persona[]>>;
  onClearHistory: () => void;
  onRemoveLast: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  config,
  setConfig,
  personas,
  setPersonas,
  onClearHistory,
  onRemoveLast,
}) => {
  // Sync selected personas with backend when they change locally
  const handlePersonaToggle = async (name: string) => {
    const updated = personas.map((p) =>
      p.name === name ? { ...p, selected: !p.selected } : p
    );
    setPersonas(updated);
    
    // Fire and forget update
    const selectedNames = updated.filter((p) => p.selected).map((p) => p.name);
    await api.updatePersonas(selectedNames);
  };

  const handleUpdate = async () => {
    const selectedNames = personas.filter((p) => p.selected).map((p) => p.name);
    await api.updatePersonas(selectedNames);
  };

  return (
    <>
      {/* Backdrop for mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <div
        className={`fixed top-0 left-0 h-full w-72 md:w-80 max-w-[85vw] bg-gray-900 border-r border-gray-800 z-50 transform transition-transform duration-300 ease-in-out shadow-2xl flex flex-col pt-safe ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <h2 className="text-xl font-bold text-white tracking-tight">Configuration</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-800 rounded-md text-gray-400 hover:text-white transition-colors"
          >
            <XIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          
          {/* History Controls */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Session Control</h3>
            <div className="flex gap-2">
               <button
                onClick={onClearHistory}
                className="flex-1 flex items-center justify-center gap-2 bg-red-900/20 hover:bg-red-900/40 text-red-400 border border-red-900/50 py-2 px-3 rounded-lg text-sm transition-all"
              >
                <TrashIcon className="w-4 h-4" /> Clear
              </button>
              <button
                onClick={onRemoveLast}
                className="flex-1 flex items-center justify-center gap-2 bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 py-2 px-3 rounded-lg text-sm transition-all"
              >
                Undo Last
              </button>
            </div>
            <button
                onClick={() => api.reloadHistory()}
                className="w-full flex items-center justify-center gap-2 bg-blue-900/20 hover:bg-blue-900/40 text-blue-400 border border-blue-900/50 py-2 px-3 rounded-lg text-sm transition-all"
              >
                <RefreshIcon className="w-4 h-4" /> Reload History
            </button>
          </div>

          <hr className="border-gray-800" />

          {/* Web Input */}
          <div className="space-y-2">
             <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Context Injection</h3>
             <label className="block text-sm text-gray-400">Web Input / Context</label>
             <textarea
                value={config.webInput}
                onChange={(e) => setConfig({ ...config, webInput: e.target.value })}
                className="w-full bg-gray-950 border border-gray-800 rounded-lg p-3 text-sm text-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none h-24 transition-all"
                placeholder="Enter background context..."
             />
          </div>

          <hr className="border-gray-800" />

          {/* Personas */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
               <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Cast & Characters</h3>
               <button onClick={handleUpdate} className="text-xs text-blue-400 hover:text-blue-300">Save</button>
            </div>
            
            <div className="space-y-1 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
              {personas.map((persona) => (
                <label
                  key={persona.name}
                  className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors ${
                    persona.selected ? 'bg-blue-900/20 border border-blue-900/30' : 'hover:bg-gray-800 border border-transparent'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={persona.selected}
                    onChange={() => handlePersonaToggle(persona.name)}
                    className="w-4 h-4 rounded border-gray-600 text-blue-600 focus:ring-blue-500 bg-gray-700"
                  />
                  <div className="flex items-center gap-2">
                    <UserIcon className={`w-4 h-4 ${persona.selected ? 'text-blue-400' : 'text-gray-500'}`} />
                    <span className={`text-sm ${persona.selected ? 'text-blue-100 font-medium' : 'text-gray-400'}`}>
                      {persona.name}
                    </span>
                  </div>
                </label>
              ))}
              {personas.length === 0 && <div className="text-gray-500 text-sm italic">No personas loaded.</div>}
            </div>
          </div>

          <hr className="border-gray-800" />

          {/* Settings Toggles */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Parameters</h3>
            
            <label className="flex items-center justify-between group cursor-pointer">
              <span className="text-sm text-gray-300 group-hover:text-white transition-colors">NSFW Mode</span>
              <div className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.nsfw}
                  onChange={(e) => setConfig({ ...config, nsfw: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600"></div>
              </div>
            </label>

            <label className="flex items-center justify-between group cursor-pointer">
              <span className="text-sm text-gray-300 group-hover:text-white transition-colors">Stream Responses</span>
              <div className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.stream}
                  onChange={(e) => setConfig({ ...config, stream: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
              </div>
            </label>
          </div>
        </div>
        
        <div className="p-4 border-t border-gray-800 bg-gray-900/50 pb-safe">
           <p className="text-xs text-gray-600 text-center">Nebula Chat v1.1</p>
        </div>
      </div>
    </>
  );
};