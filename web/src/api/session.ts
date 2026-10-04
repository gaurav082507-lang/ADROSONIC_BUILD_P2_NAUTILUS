const KEY = 'lucen_token';
const ROLE = 'lucen_role';
let memoryToken: string | null = null;
export function getToken() {
  if (memoryToken) return memoryToken;
  try {
    memoryToken = sessionStorage.getItem(KEY);
  } catch {}
  return memoryToken;
}
export function setToken(token: string, role: string) {
  memoryToken = token;
  try {
    sessionStorage.setItem(KEY, token);
    sessionStorage.setItem(ROLE, role);
  } catch {}
}
export function getRole() {
  try {
    return sessionStorage.getItem(ROLE) as 'claimant' | 'investigator' | null;
  } catch {
    return null;
  }
}
export function logout() {
  memoryToken = null;
  try {
    sessionStorage.removeItem(KEY);
    sessionStorage.removeItem(ROLE);
  } catch {}
}
