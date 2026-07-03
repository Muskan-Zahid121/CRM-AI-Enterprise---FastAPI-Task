export function formatRoleLabel(role?: string): string {
  if (!role) return 'Sales Rep';
  return role
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}
