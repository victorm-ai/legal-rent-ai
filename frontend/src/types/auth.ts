export type UserRole = 'lawyer' | 'client';

export interface AuthToken {
  token: string;
  expiresAt: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
}

export interface LoginResponse {
  access_token: string;
  expires_in_minutes: number;
  user_id: string;
  email: string;
  name: string;
  role: UserRole;
}

export type ContractStatus = 'approved' | 'pending' | 'rejected';

export interface RecentContract {
  id: string;
  name: string;
  date: string;
  status: ContractStatus;
}
