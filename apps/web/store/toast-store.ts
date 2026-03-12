"use client";

import { create } from "zustand";

type ToastVariant = "default" | "error";

export type ToastMessage = {
  id: string;
  title: string;
  description?: string;
  variant?: ToastVariant;
};

type ToastState = {
  messages: ToastMessage[];
  push: (message: Omit<ToastMessage, "id">) => void;
  dismiss: (id: string) => void;
};

export const useToastStore = create<ToastState>((set) => ({
  messages: [],
  push: (message) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    set((state) => ({
      messages: [...state.messages, { ...message, id }],
    }));
    window.setTimeout(() => {
      set((state) => ({ messages: state.messages.filter((item) => item.id !== id) }));
    }, 4000);
  },
  dismiss: (id) => set((state) => ({ messages: state.messages.filter((item) => item.id !== id) })),
}));
