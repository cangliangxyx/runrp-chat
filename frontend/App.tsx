import React, { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar.tsx';
import { api } from './services/api.ts';
import { ChatConfig, Message, Persona } from './types.ts';
import { MenuIcon, SendIcon, BotIcon, UserIcon, SettingsIcon } from './components/Icons.tsx';

function App() {
  // --- State ---
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Configuration State
  const [models, setModels] = useState<string[]>([]);
  const [rules, setRules] = useState<string[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  
  const [config, setConfig] = useState<ChatConfig>({
    model: '',
    systemRule: 'default',
    webInput: '',
    nsfw: true,
    stream: true,
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // --- Effects ---

  // Initial Data Load
  useEffect(() => {
    const init = async () => {
      const [m, r, p] = await Promise.all([
        api.getModels(),
        api.getRules(),
        api.getPersonas(),
      ]);
      setModels(m);
      setRules(r);
      setPersonas(p);

      // Set defaults if available
      if (m.length > 0) setConfig(c => ({ ...c, model: m[0] }));
    };
    init();
  }, []);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // --- Handlers ---

  const handleSendMessage = async () => {
    if (!input.trim() || loading || !config.model) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await api.chat(
        config.model,
        userMsg.content,
        config.systemRule,
        config.webInput,
        config.nsfw,
        config.stream
      );

      if (config.stream && response.body) {
        // Streaming Logic
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        
        // Placeholder for AI response
        const aiMsgId = (Date.now() + 1).toString();
        setMessages(prev => [
          ...prev,
          { id: aiMsgId, role: 'assistant', content: '', timestamp: Date.now() }
        ]);

        let accumulatedContent = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n').filter(line => line.trim() !== '');

          for (const line of lines) {
            try {
              // The backend sends `json.dumps(chunk)`
              const parsed = JSON.parse(line);
              
              // Handle various potential formats from the generic python generator
              let textPart = '';
              if (typeof parsed === 'string') {
                textPart = parsed;
              } else if (typeof parsed === 'object' && parsed !== null) {
                 textPart = parsed.content || parsed.text || JSON.stringify(parsed);
              }

              accumulatedContent += textPart;
              
              setMessages(prev => 
                prev.map(msg => 
                  msg.id === aiMsgId ? { ...msg, content: accumulatedContent } : msg
                )
              );
            } catch (e) {
              console.warn('Error parsing stream chunk', e);
            }
          }
        }
      } else {
        // Non-streaming logic (fallback)
        const data = await response.json();
        const content = typeof data === 'string' ? data : JSON.stringify(data);
         setMessages(prev => [
          ...prev,
          { id: Date.now().toString(), role: 'assistant', content: content, timestamp: Date.now() }
        ]);
      }

    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [
        ...prev,
        { id: Date.now().toString(), role: 'system', content: 'Error: Failed to send message.', timestamp: Date.now() }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.shiftKey) {
        // Allow new line
        return;
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const quickActions = [
    { label: 'Main Story', value: 'Continue the main story' },
    { label: 'Warm', value: 'Create a warm atmosphere' },
    { label: 'Intimate', value: 'Add intimate tension' },
    { label: 'Desire', value: 'Focus on desire' },
  ];

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 font-sans selection:bg-blue-500/30">
      
      <Sidebar 
        isOpen={isSidebarOpen} 
        onClose={() => setIsSidebarOpen(false)} 
        config={config}
        setConfig={setConfig}
        personas={personas}
        setPersonas={setPersonas}
        onClearHistory={async () => {
            await api.clearHistory();
            setMessages([]);
        }}
        onRemoveLast={async () => {
            await api.removeLastEntry();
            setMessages(prev => prev.slice(0, -1)); // Optimistic update
        }}
      />

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col relative transition-all duration-300 ${isSidebarOpen ? 'md:ml-80' : ''}`}>
        
        {/* Top Navigation Bar */}
        <header className="h-16 flex items-center justify-between px-4 border-b border-gray-800/50 bg-gray-950/80 backdrop-blur-md sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white transition-colors"
            >
              <MenuIcon className="w-5 h-5" />
            </button>
            <h1 className="text-lg font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Nebula Chat
            </h1>
          </div>

          <div className="flex items-center gap-4">
            {/* Model Selector */}
            <div className="flex items-center gap-2 bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5">
               <SettingsIcon className="w-4 h-4 text-gray-500" />
               <select 
                 value={config.model}
                 onChange={(e) => setConfig({...config, model: e.target.value})}
                 className="bg-transparent border-none outline-none text-sm text-gray-200 cursor-pointer min-w-[100px]"
               >
                 {models.map(m => <option key={m} value={m} className="bg-gray-900">{m}</option>)}
               </select>
            </div>

            {/* Rule Selector */}
            <div className="hidden md:flex items-center gap-2 bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5">
               <span className="text-xs text-gray-500 font-bold uppercase">Rule</span>
               <select 
                 value={config.systemRule}
                 onChange={(e) => setConfig({...config, systemRule: e.target.value})}
                 className="bg-transparent border-none outline-none text-sm text-gray-200 cursor-pointer max-w-[120px]"
               >
                 {rules.map(r => <option key={r} value={r} className="bg-gray-900">{r}</option>)}
               </select>
            </div>
          </div>
        </header>

        {/* Chat Area */}
        <main className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth">
          <div className="max-w-4xl mx-auto space-y-6">
            
            {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-[50vh] text-gray-500">
                    <div className="w-16 h-16 bg-gray-900 rounded-full flex items-center justify-center mb-4 border border-gray-800">
                        <BotIcon className="w-8 h-8 text-blue-500/50" />
                    </div>
                    <p className="text-lg font-medium">Start a new conversation</p>
                    <p className="text-sm opacity-60">Select a persona and model to begin.</p>
                </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role !== 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg mt-1">
                    <BotIcon className="w-5 h-5 text-white" />
                  </div>
                )}
                
                <div
                  className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-5 py-3.5 leading-relaxed shadow-md ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : msg.role === 'system'
                      ? 'bg-red-900/50 border border-red-800 text-red-200'
                      : 'bg-gray-800 text-gray-100 border border-gray-700/50 rounded-bl-none'
                  }`}
                >
                  <div className="whitespace-pre-wrap text-sm md:text-base">
                      {msg.content}
                  </div>
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0 mt-1">
                    <UserIcon className="w-5 h-5 text-gray-300" />
                  </div>
                )}
              </div>
            ))}
            
            {loading && messages.length > 0 && messages[messages.length -1].role === 'user' && (
                <div className="flex gap-4">
                     <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg">
                        <BotIcon className="w-5 h-5 text-white" />
                    </div>
                    <div className="bg-gray-800 rounded-2xl px-5 py-4 rounded-bl-none flex items-center gap-1">
                        <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></span>
                        <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-75"></span>
                        <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-150"></span>
                    </div>
                </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </main>

        {/* Input Area */}
        <footer className="p-4 bg-gray-950/90 backdrop-blur border-t border-gray-800/50">
          <div className="max-w-4xl mx-auto space-y-3">
            
            {/* Quick Actions */}
            <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                {quickActions.map(action => (
                    <button
                        key={action.label}
                        onClick={() => setInput(action.value)}
                        className="whitespace-nowrap px-3 py-1.5 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-md text-xs font-medium text-gray-400 hover:text-blue-400 transition-colors"
                    >
                        {action.label}
                    </button>
                ))}
            </div>

            <div className="relative group">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask me a question or give me a command..."
                className="w-full bg-gray-900 border border-gray-800 text-gray-100 rounded-xl pl-4 pr-14 py-4 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 resize-none h-[60px] max-h-[200px] shadow-inner transition-all"
                style={{ minHeight: '60px' }}
              />
              <button
                onClick={handleSendMessage}
                disabled={loading || !input.trim()}
                className={`absolute right-2 bottom-2.5 p-2 rounded-lg transition-all duration-200 ${
                  input.trim() && !loading
                    ? 'bg-blue-600 text-white shadow-lg hover:bg-blue-500 hover:scale-105'
                    : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                }`}
              >
                <SendIcon className="w-5 h-5" />
              </button>
            </div>
            
             <div className="text-center">
                <p className="text-[10px] text-gray-600">
                    Shift + Enter for new line. AI output can be unpredictable.
                </p>
             </div>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;