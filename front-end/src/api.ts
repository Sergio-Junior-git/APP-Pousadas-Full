import AsyncStorage from '@react-native-async-storage/async-storage';

declare const process: { env: { EXPO_PUBLIC_API_URL?: string } };
export const API_URL = (process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8001').replace(/\/$/, '');
const TOKEN_KEY = '@pousada/token';
export type User = { id: number; name: string; login: string; role: string; token?: string };
export type Page<T> = { items: T[]; total: number; page: number; page_size: number };
export type Guest = { id: number; full_name: string; cpf: string; email?: string; phone?: string; active: boolean };
export type Room = { id: number; number: string; floor: number; status: string; room_type_id: number; room_type?: { name: string; capacity: number; base_price: number }; active: boolean };
export type Reservation = { id: number; code: string; guest_id: number; room_id: number; guest_name?: string; room_number?: string; check_in_date: string; check_out_date: string; adults: number; children: number; nights: number; daily_rate: number; total_amount: number; total_paid: number; balance_due: number; status: string };
export type Summary = { total_rooms: number; rooms_available: number; rooms_occupied: number; rooms_cleaning: number; rooms_maintenance: number; occupancy_rate: number; checkins_today: number; checkouts_today: number; pending_housekeeping: number; open_maintenance: number; revenue_month: number; reservations_today: number };
export type Bootstrap = { summary: Summary; arrivals: Reservation[]; departures: Reservation[]; rooms: Room[]; pending_housekeeping: any[]; open_maintenance: any[] };

export async function token() { return AsyncStorage.getItem(TOKEN_KEY); }
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const auth = await token();
  const res = await fetch(`${API_URL}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(auth ? { Authorization: `Bearer ${auth}` } : {}), ...options.headers } });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) await AsyncStorage.removeItem(TOKEN_KEY);
    const detail = body.detail;
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((e: any) => e.msg).join('\n') : `Falha na comunicação (${res.status})`);
  }
  return body as T;
}
export async function login(loginName: string, password: string): Promise<User> {
  const data = await request<User>('/auth/login', { method: 'POST', body: JSON.stringify({ login: loginName, password }) });
  if (!data.token) throw new Error('A API não retornou o token de acesso.');
  await AsyncStorage.setItem(TOKEN_KEY, data.token); return data;
}
export async function logout() { await AsyncStorage.removeItem(TOKEN_KEY); }
export const qs = (params: Record<string, string | number | undefined>) => { const q = new URLSearchParams(); Object.entries(params).forEach(([k,v]) => v !== undefined && q.set(k,String(v))); return q.toString() ? `?${q}` : ''; };
