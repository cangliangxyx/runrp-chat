import {GoogleGenAI} from "@google/genai";
import {Persona} from '../types.ts';

// Helper to handle form data creation
const createFormData = (data: Record<string, string | boolean>) => {
  const formData = new FormData();
  Object.entries(data).forEach(([key, value]) => {
    formData.append(key, String(value));
  });
  return formData;
};

export const api = {
  getModels: async (): Promise<string[]> => {
    try {
      const res = await fetch('/system_model');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.rules || [];
    } catch (e) {
        console.warn('Backend unavailable, using default Gemini models');
        return ['gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro', 'gemini-2.0-flash-thinking-exp-01-21'];
    }
  },

  getRules: async (): Promise<string[]> => {
    try {
      const res = await fetch('/system_rules');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.rules || [];
    } catch (e) {
        console.warn('Backend unavailable, returning empty rules');
      return [];
    }
  },

  getPersonas: async (): Promise<Persona[]> => {
    try {
      const res = await fetch('/personas');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.personas || [];
    } catch (e) {
        console.warn('Backend unavailable, returning empty personas');
      return [];
    }
  },

  updatePersonas: async (selectedNames: string[]): Promise<void> => {
      try {
          const formData = new FormData();
          formData.append('selected', selectedNames.join(','));
          await fetch('/personas', {
              method: 'POST',
              body: formData,
          });
      } catch (e) {
          // Ignore errors in fallback mode
      }
  },

  clearHistory: async (): Promise<void> => {
      try {
          await fetch('/clear_history', {method: 'POST'});
      } catch (e) {
          // Ignore errors in fallback mode
      }
  },

  reloadHistory: async (): Promise<void> => {
      try {
          await fetch('/reload_history', {method: 'POST'});
      } catch (e) {
          // Ignore errors in fallback mode
      }
  },

  removeLastEntry: async (): Promise<void> => {
      try {
          await fetch('/remove_last_entry', {method: 'POST'});
      } catch (e) {
          // Ignore errors in fallback mode
      }
  },

  chat: async (
    model: string,
    prompt: string,
    systemRule: string,
    webInput: string,
    nsfw: boolean,
    stream: boolean
  ): Promise<Response> => {
      try {
          // Try backend first
          const formData = createFormData({
              model,
              prompt,
              system_rule: systemRule,
              web_input: webInput,
              nsfw,
              stream,
          });

          const res = await fetch('/chat', {
              method: 'POST',
              body: formData,
          });

          if (!res.ok) {
              throw new Error(`Chat API Failed: ${res.status} ${res.statusText}`);
          }

          return res;
      } catch (error) {
          console.warn('Backend chat failed, falling back to direct Gemini API', error);

          // Fallback to Gemini SDK
          const apiKey = process.env.API_KEY;
          if (!apiKey) {
              const msg = "Error: API_KEY is missing in environment variables. Cannot use fallback mode.";
              return new Response(JSON.stringify({content: msg}), {
                  headers: {'Content-Type': 'application/json'}
              });
          }

          const ai = new GoogleGenAI({apiKey});

          // Construct effective prompt with webInput context
          let fullPrompt = prompt;
          if (webInput) {
              fullPrompt = `Context info:\n${webInput}\n\nUser Request:\n${prompt}`;
          }

          // Ensure we have a valid model string
          const targetModel = model || 'gemini-2.5-flash';

          const config: any = {};
          if (systemRule && systemRule !== 'default') {
              config.systemInstruction = systemRule;
          }

          if (stream) {
              // Create a ReadableStream that mimics the backend's NDJSON output
              // We move the generation inside the start method to catch startup errors (like 403 Invalid Key)
              // and stream them to the UI instead of crashing the promise.
              const readable = new ReadableStream({
                  async start(controller) {
                      const encoder = new TextEncoder();
                      try {
                          const responseStream = await ai.models.generateContentStream({
                              model: targetModel,
                              contents: fullPrompt,
                              config
                          });

                          for await (const chunk of responseStream) {
                              const text = chunk.text;
                              if (text) {
                                  // Format as JSON line expected by App.tsx
                                  const line = JSON.stringify({content: text}) + '\n';
                                  controller.enqueue(encoder.encode(line));
                              }
                          }
                      } catch (err: any) {
                          console.error("Gemini Fallback Error:", err);
                          // Provide a user-friendly error in the chat
                          const errorMessage = `\n[System: Connection to Gemini API failed. ${err.message || 'Unknown error'}]`;
                          const line = JSON.stringify({content: errorMessage}) + '\n';
                          controller.enqueue(encoder.encode(line));
                      }
                      controller.close();
                  }
              });

              return new Response(readable, {
                  headers: {'Content-Type': 'application/x-ndjson'}
              });
          } else {
              // Non-streaming fallback
              try {
                  const response = await ai.models.generateContent({
                      model: targetModel,
                      contents: fullPrompt,
                      config
                  });

                  return new Response(JSON.stringify({content: response.text}), {
                      headers: {'Content-Type': 'application/json'}
                  });
              } catch (err: any) {
                  return new Response(JSON.stringify({content: `[System Error: ${err.message}]`}), {
                      headers: {'Content-Type': 'application/json'}
                  });
              }
          }
      }
  },
};