/**
 * Global Store Module
 *
 * Provides a simple key-value store for global variables that persist
 * across all MCP servers within the same conversation thread.
 *
 * Global variables are appropriate for data that should be shared
 * across all MCP servers in a conversation, such as:
 * - Customer ID (authenticated user)
 * - Authentication tokens
 * - User permissions
 *
 * NOTE: This is a sample implementation using in-memory storage.
 * In production, use a persistent store (Redis, database, etc.).
 */

/**
 * In-memory store: Map<thread_id, Map<variableName, value>>
 */
const globalStore = new Map<string, Map<string, any>>();

/**
 * Set a variable in the global store for a specific thread
 *
 * @param threadId - The unique thread identifier from system context
 * @param variableName - Name of the variable to store
 * @param value - Value to store (any type)
 */
export function setGlobalVariable(
  threadId: string,
  variableName: string,
  value: any,
): void {
  if (!globalStore.has(threadId)) {
    globalStore.set(threadId, new Map());
  }
  const threadData = globalStore.get(threadId);
  if (threadData) {
    threadData.set(variableName, value);
  }
}

/**
 * Get a variable from the global store for a specific thread
 *
 * @param threadId - The unique thread identifier from system context
 * @param variableName - Name of the variable to retrieve
 * @returns The stored value, or undefined if not found
 */
export function getGlobalVariable(threadId: string, variableName: string): any {
  return globalStore.get(threadId)?.get(variableName);
}

/**
 * Delete a variable from the global store for a specific thread
 *
 * @param threadId - The unique thread identifier from system context
 * @param variableName - Name of the variable to delete
 * @returns true if the variable was deleted, false if it didn't exist
 */
export function deleteGlobalVariable(
  threadId: string,
  variableName: string,
): boolean {
  return globalStore.get(threadId)?.delete(variableName) ?? false;
}
