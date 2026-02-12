/**
 * Credit Card Service - Mock Implementation
 *
 * Contains mock business logic for credit card operations
 */

export interface CreditCardBalance {
  cardNumber: string;
  cardType: string;
  currentBalance: number;
  availableCredit: number;
  creditLimit: number;
  minimumPayment: number;
  paymentDueDate: string;
  lastStatementDate: string;
  lastStatementBalance: number;
}

/**
 * Mock Credit Card Service
 */
export class CreditCardService {
  /**
   * Get credit card balance and details using JWT authentication
   *
   * @param jwtToken - JWT token for authentication with backend service
   * @returns Credit card balance information
   */
  static getCreditCardBalance(jwtToken: string): CreditCardBalance {
    // In a real implementation, this would:
    // 1. Validate the JWT token
    // 2. Extract customer ID from the token claims
    // 3. Make an authenticated API call to the backend service
    // 4. Return the actual credit card data

    // For demo purposes, we'll just validate the token exists
    if (!jwtToken) {
      throw new Error('JWT token is required');
    }

    // Mock response - in production this would come from your backend API
    return {
      cardNumber: `**** **** **** 4532`,
      cardType: 'Platinum Rewards',
      currentBalance: 2847.63,
      availableCredit: 7152.37,
      creditLimit: 10000.0,
      minimumPayment: 85.43,
      paymentDueDate: '2026-01-28',
      lastStatementDate: '2025-12-28',
      lastStatementBalance: 2654.21,
    };
  }
}
