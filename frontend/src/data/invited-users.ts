// Single source of truth for invited users

export interface InvitedUser {
  email: string;
  role: "admin" | "user";
}

// Only invited guests are allowed to use this platform
export const INVITED_USERS: InvitedUser[] = [
  { email: "joy@maurinventures.com", role: "admin" },
  { email: "branden@maurinventures.com", role: "user" },
  { email: "stefanie@maurinventures.com", role: "user" },
  { email: "dafneestardo@gmail.com", role: "user" },
  { email: "chikiestardo143@gmail.com", role: "user" },
];

// Helper functions
export const isInvitedUser = (email: string): boolean => {
  return INVITED_USERS.some(user => user.email.toLowerCase() === email.toLowerCase());
};

export const getUserRole = (email: string): "admin" | "user" | null => {
  const user = INVITED_USERS.find(user => user.email.toLowerCase() === email.toLowerCase());
  return user?.role || null;
};

export const isAdmin = (email: string): boolean => {
  return getUserRole(email) === "admin";
};
