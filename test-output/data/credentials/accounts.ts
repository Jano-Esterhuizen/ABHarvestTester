import { UserRole } from '../../core/types/enums';

export interface AccountCredentials {
  role: UserRole;
  username: string;
  password: string;
  description: string;
}

const accounts: AccountCredentials[] = [
];

export function getAccountByRole(role: string): AccountCredentials {
  const account = accounts.find(a => a.role === role);
  if (!account) throw new Error(`No account found for role: ${role}`);
  return account;
}

export function getAllAccounts(): AccountCredentials[] {
  return accounts;
}
