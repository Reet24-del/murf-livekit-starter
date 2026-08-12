export interface CallerProfileSummary {
  name: string | null;
  crops_grown: string | null;
  district: string | null;
  conversation_memory: string | null;
  last_interaction: string | null;
}

export function getStoredCallerId(): string | null {
  return typeof window === 'undefined' ? null : localStorage.getItem('user_id');
}

export async function fetchCallerProfile(
  userId: string,
  signal?: AbortSignal
): Promise<CallerProfileSummary | null> {
  const response = await fetch(`/api/profile?user_id=${encodeURIComponent(userId)}`, { signal });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Profile request failed with ${response.status}`);
  return (await response.json()) as CallerProfileSummary;
}
