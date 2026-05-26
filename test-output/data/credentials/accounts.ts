import { UserRole } from '../../core/types/enums';

export interface AccountCredentials {
  role: UserRole;
  username: string;
  password: string;
  description: string;
}

const accounts: AccountCredentials[] = [
  {
    role: UserRole.DIRECTOR,
    username: process.env.DIRECTOR_USERNAME || "director@abmail.co.za",
    password: process.env.DIRECTOR_PASSWORD || "Test1234",
    description: "Sarah Director â€” Director role with highest permissions",
  },

  {
    role: UserRole.PM,
    username: process.env.PM_USERNAME || "pm@abmail.co.za",
    password: process.env.PM_PASSWORD || "Test1234",
    description: "James ProjectManager â€” Project Manager role",
  },

  {
    role: UserRole.ANALYST,
    username: process.env.ANALYST_USERNAME || "analyst@abmail.co.za",
    password: process.env.ANALYST_PASSWORD || "Test1234",
    description: "Emily Analyst â€” Analyst role with basic permissions",
  },

];

export function getAccountByRole(role: string): AccountCredentials {
  const account = accounts.find(a => a.role === role);
  if (!account) throw new Error(`No account found for role: ${role}`);
  return account;
}

export function getAllAccounts(): AccountCredentials[] {
  return accounts;
}
