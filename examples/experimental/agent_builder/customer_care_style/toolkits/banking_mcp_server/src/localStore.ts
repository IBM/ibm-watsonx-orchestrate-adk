/**
 * Local Store Module
 *
 * Provides a simple key-value store for local variables that are
 * specific to a single MCP server within a conversation thread.
 *
 * Local variables are appropriate for data that should be isolated
 * to a specific MCP server, such as:
 * - Pending transactions awaiting confirmation
 * - Multi-step operation state
 * - Temporary calculations
 * - Draft data before commit
 *
 * NOTE: This is a sample implementation using in-memory storage.
 * In production, use a persistent store (Redis, database, etc.).
 */

/**
 * In-memory store: Map<thread_id, Map<variableName, value>>
 */
const localStore = new Map<string, Map<string, any>>();

/**
 * Set a variable in the local store for a specific thread
 *
 * @param threadId - The unique thread identifier from system context
 * @param variableName - Name of the variable to store
 * @param value - Value to store (any type)
 */
export function setLocalVariable(
  threadId: string,
  variableName: string,
  value: any,
): void {
  if (!localStore.has(threadId)) {
    localStore.set(threadId, new Map());
  }
  const threadData = localStore.get(threadId);
  if (threadData) {
    threadData.set(variableName, value);
  }
}

/**
 * Get a variable from the local store for a specific thread
 *
 * @param threadId - The unique thread identifier from system context
 * @param variableName - Name of the variable to retrieve
 * @returns The stored value, or undefined if not found
 */
export function getLocalVariable(threadId: string, variableName: string): any {
  return localStore.get(threadId)?.get(variableName);
}

/**
 * Delete a variable from the local store for a specific thread
 *
 * @param threadId - The unique thread identifier from system context
 * @param variableName - Name of the variable to delete
 * @returns true if the variable was deleted, false if it didn't exist
 */
export function deleteLocalVariable(
  threadId: string,
  variableName: string,
): boolean {
  return localStore.get(threadId)?.delete(variableName) ?? false;
}
