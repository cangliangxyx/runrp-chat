import React, {useEffect, useRef, useState} from 'react';
import {Sidebar} from './components/Sidebar.tsx';
import {api} from './services/api.ts';
import {ChatConfig, Message, Persona} from './types.ts';
import {BotIcon, CheckIcon, CopyIcon, MenuIcon, SendIcon, SettingsIcon} from './components/Icons.tsx';

// --- Helper Components ---

const CodeBlock = ({language, code}: { language: string; code: string }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const lineCount = code.split('\n').length;
    // Collapse if content is longer than 5 lines
    const isLong = lineCount > 5;

    if (!isLong) {
        return (
            <div
                className="my-2 rounded-lg bg-gray-950 border border-gray-800 overflow-hidden font-mono text-xs md:text-sm"
                onClick={(e) => e.stopPropagation()}
            >
                <div
                    className="bg-gray-900/50 px-3 py-1 border-b border-gray-800/50 text-[10px] text-gray-500 font-bold uppercase flex justify-between">
                    <span>{language || 'TEXT'}</span>
                </div>
                <div className="p-3 overflow-x-auto">
                    <pre className="whitespace-pre font-mono text-gray-300">{code}</pre>
                </div>
            </div>
        );
    }

    return (
        <div
            className={`group my-3 rounded-lg border border-gray-800 bg-gray-950 overflow-hidden transition-all duration-300 ease-in-out ${isExpanded ? 'shadow-lg' : 'cursor-pointer hover:border-gray-700'}`}
            onClick={(e) => {
                e.stopPropagation();
                setIsExpanded(!isExpanded);
            }}
        >
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-1.5 bg-gray-900/50 border-b border-gray-800/50">
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-gray-500 uppercase">{language || 'CODE'}</span>
                    {!isExpanded && <span className="text-[10px] text-gray-600 animate-pulse">• Click to expand</span>}
                </div>
                <button
                    className={`text-[10px] font-medium transition-colors ${isExpanded ? 'text-blue-400 hover:text-blue-300' : 'text-gray-500'}`}
                >
                    {isExpanded ? 'Collapse' : 'Expand'}
                </button>
            </div>

            {/* Content */}
            <div className={`relative ${isExpanded ? '' : 'max-h-32 overflow-hidden'}`}>
                <div className="p-3 overflow-x-auto">
                    <pre className="whitespace-pre font-mono text-xs md:text-sm text-gray-300">{code}</pre>
                </div>

                {/* Gradient Mask for collapsed state */}
                {!isExpanded && (
                    <div
                        className="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-950/40 to-transparent flex items-end justify-center pointer-events-none">
                    </div>
                )}
            </div>
        </div>
    );
};

const MessageContent = ({content, fontSizeClass}: { content: string, fontSizeClass: string }) => {
    // 1. Try to detect pure JSON response (e.g. if the model outputs raw JSON)
    try {
        const trimmed = content.trim();
        // Simple heuristic to avoid aggressive parsing of normal text
        if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
            const parsed = JSON.parse(trimmed);
            return <CodeBlock language="json" code={JSON.stringify(parsed, null, 2)}/>;
        }
    } catch (e) {
    }

    // 2. Parse Markdown Code Blocks
    // Split by code block regex: ```lang ... ```
    const parts = content.split(/```(\w*)\n?([\s\S]*?)```/g);

    if (parts.length === 1) {
        return <div className={`whitespace-pre-wrap break-words ${fontSizeClass}`}>{content}</div>;
    }

    return (
        <div className="w-full min-w-0">
            {parts.map((part, i) => {
                // The split creates: [text, lang, code, text, lang, code, ...]
                if (i % 3 === 0) {
                    if (!part) return null;
                    return <div key={i} className={`whitespace-pre-wrap break-words ${fontSizeClass}`}>{part}</div>;
                }
                if (i % 3 === 2) {
                    const lang = parts[i - 1];
                    return <CodeBlock key={i} language={lang} code={part.trim()}/>;
                }
                return null;
            })}
        </div>
    );
};

function App() {
  // --- State ---
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

    // UI State for Context Menu
    const [activeMessageId, setActiveMessageId] = useState<string | null>(null);
    const [copyFeedbackId, setCopyFeedbackId] = useState<string | null>(null);

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
      fontSize: 'normal',
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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

    // Close context menu when clicking outside
    useEffect(() => {
        const handleClickOutside = () => setActiveMessageId(null);
        window.addEventListener('click', handleClickOutside);
        return () => window.removeEventListener('click', handleClickOutside);
    }, []);

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
      setActiveMessageId(null); // Close any open menus

      // Reset height of textarea
    if (textareaRef.current) {
        textareaRef.current.style.height = '60px';
    }

    try {
      const response = await api.chat(
        config.model,
        userMsg.content,
        config.systemRule,
        config.webInput,
        config.nsfw,
        config.stream
      );

      // Placeholder for AI response
      const aiMsgId = (Date.now() + 1).toString();
      setMessages(prev => [
        ...prev,
        { id: aiMsgId, role: 'assistant', content: '', timestamp: Date.now() }
      ]);

      if (config.stream) {
        // --- STREAMING HANDLING ---
        if (!response.body) throw new Error("No response body received from server.");

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');

        let accumulatedContent = '';
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // Decode the chunk and append to buffer
          buffer += decoder.decode(value, { stream: true });

          // Split by newline to handle NDJSON
          const lines = buffer.split('\n');

          // The last line might be incomplete, so we keep it in the buffer
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (!line.trim()) continue;

            try {
              const parsed = JSON.parse(line);

              // 1. Handle "end" signal or control messages
              if (parsed && typeof parsed === 'object' && parsed.type === 'end') {
                continue;
              }

              // 2. Extract content
              let textPart = '';
              if (typeof parsed === 'string') {
                textPart = parsed;
              } else if (typeof parsed === 'object' && parsed !== null) {
                 // Prioritize 'content' or 'text' fields.
                 textPart = parsed.content || parsed.text || '';
              }

              // 3. Update UI
              if (textPart) {
                accumulatedContent += textPart;
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === aiMsgId ? { ...msg, content: accumulatedContent } : msg
                  )
                );
              }
            } catch (e) {
              console.warn('Error parsing stream line:', line, e);
            }
          }
        }

        // Process any remaining buffer content
        if (buffer.trim()) {
             try {
                const parsed = JSON.parse(buffer);
                 if (parsed && (!parsed.type || parsed.type !== 'end')) {
                     const textPart = typeof parsed === 'string' ? parsed : (parsed.content || parsed.text || '');
                     if (textPart) {
                        setMessages(prev =>
                            prev.map(msg =>
                                msg.id === aiMsgId ? { ...msg, content: accumulatedContent + textPart } : msg
                            )
                        );
                     }
                 }
             } catch (e) { /* Ignore incomplete JSON at end */ }
        }

      } else {
        // --- NON-STREAMING HANDLING ---
        // Parse the entire response as a single JSON object
        const data = await response.json();

        let fullContent = '';

        // Check for the specific structure returned by the python backend in non-stream mode:
        // {"results": [{"type": "chunk", "content": "..."}, {"type": "end", "full": "..."}]}
        if (data.results && Array.isArray(data.results)) {
            fullContent = data.results
                .filter((item: any) => item.type !== 'end') // Filter out the 'end' signal
                .map((item: any) => item.content || item.text || '')
                .join('');
        } else if (data.content) {
            // Fallback for simple structures
            fullContent = data.content;
        }

        setMessages(prev =>
          prev.map(msg =>
            msg.id === aiMsgId ? { ...msg, content: fullContent } : msg
          )
        );
      }

    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [
        ...prev,
        { id: Date.now().toString(), role: 'system', content: 'Error: Failed to send message. Please check the connection.', timestamp: Date.now() }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.shiftKey) {
        return;
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

    const handleMessageClick = (e: React.MouseEvent, msgId: string) => {
        // If text is selected (highlighted), do not toggle the menu
        if (window.getSelection()?.toString().length) return;

        e.stopPropagation(); // Prevent global click handler from immediately closing it
        setActiveMessageId(prev => prev === msgId ? null : msgId);
    };

    const handleCopy = async (content: string, id: string) => {
        try {
            await navigator.clipboard.writeText(content);
            setCopyFeedbackId(id);
            setTimeout(() => {
                setCopyFeedbackId(null);
                setActiveMessageId(null);
            }, 1500);
        } catch (err) {
            console.error('Failed to copy', err);
        }
    };

  const quickActions = [
    { label: 'Main Story', value: 'Continue the main story' },
    { label: 'Warm', value: 'Create a warm atmosphere' },
    { label: 'Intimate', value: 'Add intimate tension' },
    { label: 'Desire', value: 'Focus on desire' },
  ];

    const getFontSizeClass = (size?: string) => {
        switch (size) {
            case 'small':
                return 'text-xs md:text-sm';
            case 'large':
                return 'text-base md:text-lg';
            case 'xl':
                return 'text-lg md:text-xl';
            default:
                return 'text-sm md:text-base';
        }
    };

  return (
    // Use [100dvh] for dynamic viewport height to fix mobile address bar issues
    <div className="flex h-[100dvh] bg-gray-950 text-gray-100 font-sans selection:bg-blue-500/30 overflow-hidden">

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
      <div className={`flex-1 flex flex-col relative transition-all duration-300 ${isSidebarOpen ? 'md:ml-80' : ''} w-full`}>

        {/* Top Navigation Bar - Sticky & Blur */}
        <header className="flex-none h-14 md:h-16 flex items-center justify-between px-3 md:px-4 border-b border-gray-800/50 bg-gray-950/80 backdrop-blur-md sticky top-0 z-30 pt-safe">
          <div className="flex items-center gap-2 md:gap-3 overflow-hidden">
              <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-1.5 md:p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white transition-colors shrink-0"
            >
              <MenuIcon className="w-5 h-5 md:w-6 md:h-6" />
            </button>
            <h1 className="text-base md:text-lg font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent truncate">
              Runchat
            </h1>
          </div>

          <div className="flex items-center gap-2 md:gap-4 shrink-0">
            {/* Model Selector - Compact on Mobile */}
            <div className="flex items-center gap-1 md:gap-2 bg-gray-900 border border-gray-800 rounded-lg px-2 py-1 md:px-3 md:py-1.5 max-w-[120px] md:max-w-xs">
               <SettingsIcon className="w-3 h-3 md:w-4 md:h-4 text-gray-500 shrink-0" />
                <select
                 value={config.model}
                 onChange={(e) => setConfig({...config, model: e.target.value})}
                 className="bg-transparent border-none outline-none text-xs md:text-sm text-gray-200 cursor-pointer w-full text-ellipsis"
               >
                 {models.map(m => <option key={m} value={m} className="bg-gray-900">{m}</option>)}
               </select>
            </div>

            {/* Rule Selector - Visible but compact on mobile */}
            <div className="flex items-center gap-1 md:gap-2 bg-gray-900 border border-gray-800 rounded-lg px-2 py-1 md:px-3 md:py-1.5 max-w-[100px] md:max-w-xs">
               <span className="text-[10px] md:text-xs text-gray-500 font-bold uppercase shrink-0 hidden xs:block">Rule</span>
                <select
                 value={config.systemRule}
                 onChange={(e) => setConfig({...config, systemRule: e.target.value})}
                 className="bg-transparent border-none outline-none text-xs md:text-sm text-gray-200 cursor-pointer w-full text-ellipsis"
               >
                 {rules.map(r => <option key={r} value={r} className="bg-gray-900">{r}</option>)}
               </select>
            </div>
          </div>
        </header>

        {/* Chat Area */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-3 md:p-8 scroll-smooth w-full">
          <div className="max-w-4xl mx-auto space-y-6 pb-2">

              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-[40vh] md:h-[50vh] text-gray-500">
                    <div className="w-14 h-14 md:w-16 md:h-16 bg-gray-900 rounded-full flex items-center justify-center mb-4 border border-gray-800">
                        <BotIcon className="w-6 h-6 md:w-8 md:h-8 text-blue-500/50" />
                    </div>
                    <p className="text-base md:text-lg font-medium">Start a new conversation</p>
                    <p className="text-xs md:text-sm opacity-60">Select a persona and model to begin.</p>
                </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-2 md:gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                  <div
                      onClick={(e) => handleMessageClick(e, msg.id)}
                      className={`relative cursor-pointer max-w-[90%] md:max-w-[80%] rounded-2xl px-4 py-3 md:px-5 md:py-3.5 leading-relaxed shadow-md transition-shadow hover:shadow-lg ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : msg.role === 'system'
                      ? 'bg-red-900/50 border border-red-800 text-red-200'
                      : 'bg-gray-800 text-gray-100 border border-gray-700/50 rounded-bl-none'
                  }`}
                >
                      <MessageContent
                          content={msg.content}
                          fontSizeClass={getFontSizeClass(config.fontSize)}
                      />

                      {/* Copy Popup Menu */}
                      {activeMessageId === msg.id && (
                          <div
                              className={`absolute z-20 top-full mt-2 ${msg.role === 'user' ? 'right-0' : 'left-0'} animate-in fade-in zoom-in-95 duration-150`}
                          >
                              <div
                                  className="bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden p-1 flex items-center">
                                  <button
                                      onClick={(e) => {
                                          e.stopPropagation();
                                          handleCopy(msg.content, msg.id);
                                      }}
                                      className="flex items-center gap-2 px-3 py-2 hover:bg-gray-800 rounded text-xs md:text-sm text-gray-200 transition-colors whitespace-nowrap"
                                  >
                                      {copyFeedbackId === msg.id ? (
                                          <>
                                              <CheckIcon className="w-4 h-4 text-green-400"/>
                                              <span className="text-green-400 font-medium">Copied!</span>
                                          </>
                                      ) : (
                                          <>
                                              <CopyIcon className="w-4 h-4"/>
                                              <span>Copy Text</span>
                                          </>
                                      )}
                                  </button>
                              </div>
                          </div>
                      )}
                </div>
              </div>
            ))}

              {loading && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
                  <div className="flex gap-4 justify-start">
                      <div
                          className="bg-gray-800 rounded-2xl px-5 py-4 rounded-bl-none flex items-center gap-1 shadow-md border border-gray-700/50">
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
        {/* pb-safe accounts for iPhone Home Indicator */}
        <footer className="flex-none p-3 md:p-4 bg-gray-950/90 backdrop-blur border-t border-gray-800/50 pb-safe">
          <div className="max-w-4xl mx-auto space-y-3">
            
            {/* Quick Actions - Scrollable on mobile */}
            <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar mask-gradient-right">
                {quickActions.map(action => (
                    <button
                        key={action.label}
                        onClick={() => setInput(action.value)}
                        className="whitespace-nowrap px-3 py-1.5 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-full md:rounded-md text-xs font-medium text-gray-400 hover:text-blue-400 transition-colors flex-shrink-0"
                    >
                        {action.label}
                    </button>
                ))}
            </div>

            <div className="relative group">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message..."
                // text-base on mobile prevents iOS zoom, text-sm on desktop looks cleaner
                className="w-full bg-gray-900 border border-gray-800 text-gray-100 rounded-xl pl-4 pr-12 md:pr-14 py-3 md:py-4 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 resize-none h-[50px] md:h-[60px] max-h-[150px] shadow-inner transition-all text-base md:text-sm"
                style={{ minHeight: '50px' }}
              />
              <button
                onClick={handleSendMessage}
                disabled={loading || !input.trim()}
                className={`absolute right-2 bottom-2 md:bottom-2.5 p-2 rounded-lg transition-all duration-200 ${
                  input.trim() && !loading
                    ? 'bg-blue-600 text-white shadow-lg hover:bg-blue-500 hover:scale-105'
                    : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                }`}
              >
                <SendIcon className="w-4 h-4 md:w-5 md:h-5" />
              </button>
            </div>
            
             <div className="hidden md:block text-center">
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