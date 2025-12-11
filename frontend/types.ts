export interface Persona {
  name: string;
  selected: boolean;
}

export interface ChatConfig {
  model: string;
  systemRule: string;
  webInput: string;
  nsfw: boolean;
  stream: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export interface StreamChunk {
  content?: string;
  // Add other fields if your backend sends more structure in the stream
}

export interface ApiStatus {
  loading: boolean;
  error: string | null;
}