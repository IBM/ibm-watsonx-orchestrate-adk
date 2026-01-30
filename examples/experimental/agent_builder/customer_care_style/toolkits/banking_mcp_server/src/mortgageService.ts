/**
 * Mortgage Service - Mock Implementation
 *
 * Contains mock business logic for mortgage operations
 */

export interface MortgageBalance {
  loanNumber: string;
  originalAmount: number;
  outstandingBalance: number;
  interestRate: number;
  monthlyPayment: number;
  nextPaymentDate: string;
  remainingTermMonths: number;
}

export interface MortgagePayment {
  paymentDate: string;
  amount: number;
  principal: number;
  interest: number;
  escrow: number;
  balanceAfter: number;
}

export interface MortgagePaymentHistory {
  customerId: string;
  loanNumber: string;
  payments: MortgagePayment[];
}

export interface PreparedPayment {
  transactionId: string;
  loanNumber: string;
  amount: number;
  paymentDate: string;
  currentBalance: number;
  expiresAt: string;
}

export interface PaymentValidationError {
  isValid: false;
  errorMessage: string;
}

export interface PaymentValidationSuccess {
  isValid: true;
}

export type PaymentValidationResult =
  | PaymentValidationError
  | PaymentValidationSuccess;

/**
 * Mock Mortgage Service
 */
export class MortgageService {
  /**
   * Get mortgage balance and details
   */
  static getMortgageBalance(customerId: string): MortgageBalance {
    return {
      loanNumber: `MTG-${customerId}-001`,
      originalAmount: 350000.0,
      outstandingBalance: 287450.32,
      interestRate: 3.75,
      monthlyPayment: 1620.5,
      nextPaymentDate: '2026-01-01',
      remainingTermMonths: 276,
    };
  }

  /**
   * Get mortgage payment history
   */
  static getMortgagePayments(
    customerId: string,
    count: number = 6,
  ): MortgagePaymentHistory {
    const loanNumber = `MTG-${customerId}-001`;
    const allPayments: MortgagePayment[] = [
      {
        paymentDate: '2025-12-01',
        amount: 1620.5,
        principal: 722.15,
        interest: 898.35,
        escrow: 0,
        balanceAfter: 287450.32,
      },
      {
        paymentDate: '2025-11-01',
        amount: 1620.5,
        principal: 719.88,
        interest: 900.62,
        escrow: 0,
        balanceAfter: 288172.47,
      },
      {
        paymentDate: '2025-10-01',
        amount: 1620.5,
        principal: 717.61,
        interest: 902.89,
        escrow: 0,
        balanceAfter: 288892.35,
      },
      {
        paymentDate: '2025-09-01',
        amount: 1620.5,
        principal: 715.35,
        interest: 905.15,
        escrow: 0,
        balanceAfter: 289609.96,
      },
      {
        paymentDate: '2025-08-01',
        amount: 1620.5,
        principal: 713.1,
        interest: 907.4,
        escrow: 0,
        balanceAfter: 290325.31,
      },
      {
        paymentDate: '2025-07-01',
        amount: 1620.5,
        principal: 710.86,
        interest: 909.64,
        escrow: 0,
        balanceAfter: 291038.41,
      },
    ];

    return {
      customerId,
      loanNumber,
      payments: allPayments.slice(0, count),
    };
  }

  /**
   * Validate payment date
   */
  static validatePaymentDate(paymentDate: string): PaymentValidationResult {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const paymentDateObj = new Date(paymentDate);
    paymentDateObj.setHours(0, 0, 0, 0);
    const thirtyDaysFromNow = new Date(today);
    thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);

    // Check if date is in the past
    if (paymentDateObj < today) {
      return {
        isValid: false,
        errorMessage: `We're unable to schedule a payment for ${paymentDate} as this date has already passed. Please select today's date or a date within the next 30 days.`,
      };
    }

    // Check if date is more than 30 days in the future
    if (paymentDateObj > thirtyDaysFromNow) {
      const latestDate = thirtyDaysFromNow.toISOString().split('T')[0];
      return {
        isValid: false,
        errorMessage: `We can only schedule payments up to 30 days in advance. The date you selected (${paymentDate}) is beyond this window. Please choose a date on or before ${latestDate}.`,
      };
    }

    return { isValid: true };
  }

  /**
   * Prepare a mortgage payment
   */
  static preparePayment(
    customerId: string,
    amount: number,
    paymentDate: string,
  ): PreparedPayment {
    const loanNumber = `MTG-${customerId}-001`;
    const currentBalance = 287450.32;
    const transactionId = `TXN-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const expiresAt = new Date(Date.now() + 5 * 60 * 1000).toISOString(); // 5 minutes from now

    return {
      transactionId,
      loanNumber,
      amount,
      paymentDate,
      currentBalance,
      expiresAt,
    };
  }

  /**
   * Get mock transaction for confirmation/cancellation
   * In a real implementation, this would look up the transaction from storage
   */
  static getMockTransaction(customerId: string) {
    return {
      loanNumber: `MTG-${customerId}-001`,
      amount: 1620.5,
      paymentDate: new Date().toISOString().split('T')[0],
    };
  }

  /**
   * Process a mortgage payment
   * In a real implementation, this would call your mortgage system to process the payment
   */
  static processMortgagePayment(
    customerId: string,
    loanNumber: string,
    amount: number,
    paymentDate: string,
  ): string {
    // Mock implementation - in production this would:
    // - Process the payment with your mortgage system
    // - Update the mortgage balance
    // - Create payment records
    // - Return confirmation number from mortgage system

    return `CONF-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}
