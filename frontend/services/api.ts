import { Persona } from '../types.ts';

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
      const data = await res.json();
      return data.rules || [];
    } catch (e) {
      console.error('Failed to fetch models', e);
      return [];
    }
  },

  getRules: async (): Promise<string[]> => {
    try {
      const res = await fetch('/system_rules');
      const data = await res.json();
      return data.rules || [];
    } catch (e) {
      console.error('Failed to fetch rules', e);
      return [];
    }
  },

  getPersonas: async (): Promise<Persona[]> => {
    try {
      const res = await fetch('/personas');
      const data = await res.json();
      return data.personas || [];
    } catch (e) {
      console.error('Failed to fetch personas', e);
      return [];
    }
  },

  updatePersonas: async (selectedNames: string[]): Promise<void> => {
    const formData = new FormData();
    formData.append('selected', selectedNames.join(','));
    await fetch('/personas', {
      method: 'POST',
      body: formData,
    });
  },

  clearHistory: async (): Promise<void> => {
    await fetch('/clear_history', { method: 'POST' });
  },

  reloadHistory: async (): Promise<void> => {
    await fetch('/reload_history', { method: 'POST' });
  },

  removeLastEntry: async (): Promise<void> => {
    await fetch('/remove_last_entry', { method: 'POST' });
  },

  chat: async (
    model: string,
    prompt: string,
    systemRule: string,
    webInput: string,
    nsfw: boolean,
    stream: boolean
  ): Promise<Response> => {
    const formData = createFormData({
      model,
      prompt,
      system_rule: systemRule,
      web_input: webInput,
      nsfw,
      stream,
    });

    return fetch('/chat', {
      method: 'POST',
      body: formData,
    });
  },
};