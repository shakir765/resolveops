import type { Ticket, TicketDetailResponse } from "../types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

export async function checkHealth(): Promise<boolean> {
  try {
    await request<{ status: string }>("/health");
    return true;
  } catch {
    return false;
  }
}

export async function createTicket(input: {
  title: string;
  description: string;
  user_id: string;
}): Promise<Ticket> {
  const data = await request<{ ticket: Ticket }>("/tickets", {
    method: "POST",
    body: JSON.stringify({
      title: input.title,
      description: input.description,
      user_id: input.user_id,
      source: "portal",
    }),
  });
  return data.ticket;
}

export async function processTicket(ticketId: string): Promise<void> {
  await request(`/tickets/${ticketId}/process`, {
    method: "POST",
    body: JSON.stringify({ async_mode: true }),
  });
}

export async function listMyTickets(userId: string): Promise<Ticket[]> {
  const data = await request<{ tickets: Ticket[] }>(
    `/tickets?user_id=${encodeURIComponent(userId)}`,
  );
  return data.tickets;
}

export async function getTicket(ticketId: string): Promise<TicketDetailResponse> {
  return request<TicketDetailResponse>(`/tickets/${ticketId}`);
}
