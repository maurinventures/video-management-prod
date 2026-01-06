# API Client Documentation

## Overview

The `api.ts` file is the single source of truth for all API communications in the Internal Platform frontend. **ALL API calls must go through this file** - no `fetch()` calls should be scattered throughout components.

## Usage

### Basic Import

```typescript
import api from '../lib/api';
```

### Authentication

```typescript
// Login
const result = await api.auth.login('user@example.com', 'password');

// Logout
await api.auth.logout();

// 2FA verification
await api.auth.verify2FA('123456');
```

### Conversations

```typescript
// List conversations
const conversations = await api.conversations.list();

// Create conversation
const newConv = await api.conversations.create('My Chat');

// Get conversation with messages
const { conversation, messages } = await api.conversations.get('conv-id');

// Update conversation
await api.conversations.update('conv-id', { title: 'New Title' });
```

### Chat

```typescript
// Send a message
const response = await api.chat.sendMessage({
  conversation_id: 'conv-id',
  message: 'Hello, AI!',
  model: 'claude-3-sonnet',
  persona_id: 'persona-id'
});
```

### Projects

```typescript
// List projects
const projects = await api.projects.list();

// Create project
const project = await api.projects.create('My Project', 'Description');
```

## Error Handling

The API client automatically handles:

- **Authentication errors (401)**: Redirects to login page
- **Network errors**: Throws with descriptive error messages
- **JSON parsing**: Falls back to text response if needed

```typescript
try {
  const conversations = await api.conversations.list();
} catch (error) {
  console.error('API error:', error.message);
  // Handle error in UI
}
```

## Best Practices

### ✅ DO

```typescript
// Use the API client in hooks
function useConversations() {
  const fetchData = async () => {
    const data = await api.conversations.list();
    setConversations(data);
  };
}

// Use proper error handling
try {
  await api.conversations.create(title);
} catch (error) {
  setError(error.message);
}
```

### ❌ DON'T

```typescript
// Don't use fetch() directly in components
const response = await fetch('/api/conversations'); // ❌ WRONG

// Don't handle auth manually
const response = await fetch('/api/conversations', {
  headers: { 'Authorization': 'Bearer ' + token } // ❌ WRONG
});
```

## Session Management

The API client uses session-based authentication with cookies:

- `credentials: 'include'` is set on all requests
- No manual token management needed
- Automatic redirect to login on 401 errors

## Environment Configuration

Set the API base URL in your environment:

```bash
# .env.local
REACT_APP_API_URL=http://localhost:5000
```

For development, the Create React App proxy handles this automatically.

## TypeScript Support

All API methods are fully typed with interfaces from `../types/index.ts`:

- Request and response types
- Proper error handling types
- Autocomplete and type safety

## Extending the API Client

To add new endpoints:

1. Add the route to the appropriate section (auth, conversations, etc.)
2. Define types in `../types/index.ts`
3. Follow existing patterns for consistency
4. Test the new endpoint

Example:

```typescript
// In ApiClient class
notifications = {
  list: () => this.get<Notification[]>('/api/notifications'),
  markRead: (id: string) => this.put(`/api/notifications/${id}/read`),
};
```