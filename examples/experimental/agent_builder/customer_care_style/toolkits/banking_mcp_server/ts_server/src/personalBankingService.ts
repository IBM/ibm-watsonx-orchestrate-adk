/**
 * Personal Banking Service - Mock Implementation
 *
 * Contains mock business logic for personal banking operations
 */

export interface Account {
  accountId: string;
  accountName: string;
  accountType: string;
  canTransferFrom: boolean;
  canTransferTo: boolean;
  isLocked: boolean; // Indicates if the account is locked
  accountHolder?: string; // Optional field for accounts held by others (e.g., son's account)
}

export interface Transaction {
  date: string;
  description: string;
  amount: number;
  balance: number;
}

export interface TransferResult {
  customerId: string;
  fromAccountId: string;
  toAccountId: string;
  amount: number;
  scheduledDate?: string;
  memo?: string;
  transferId: string;
  status: string;
  timestamp: string;
}

export interface PreparedTransfer {
  transactionId: string;
  fromAccountId: string;
  fromAccountName: string;
  toAccountId: string;
  toAccountName: string;
  amount: number;
  scheduledDate?: string;
  memo?: string;
}

/**
 * Mock Personal Banking Service
 */
export class PersonalBankingService {
  /**
   * Get list of accounts for a customer
   * Includes owned accounts and registered external accounts for transfers
   */
  static getAccounts(customerId: string): Account[] {
    // Mock account data - in a real system, this would query a database
    return [
      {
        accountId: 'acc_checking_001',
        accountName: 'Primary Checking',
        accountType: 'checking',
        canTransferFrom: true,
        canTransferTo: true,
        isLocked: true, // This account is locked - requires customer service
      },
      {
        accountId: 'acc_savings_001',
        accountName: 'High Yield Savings',
        accountType: 'savings',
        canTransferFrom: true,
        canTransferTo: true,
        isLocked: false,
      },
      {
        accountId: 'acc_checking_002',
        accountName: 'Business Checking',
        accountType: 'checking',
        canTransferFrom: true,
        canTransferTo: true,
        isLocked: false,
      },
      {
        accountId: 'acc_investment_001',
        accountName: 'Investment Account',
        accountType: 'investment',
        canTransferFrom: false, // Cannot transfer from investment accounts
        canTransferTo: true,
        isLocked: false,
      },
      {
        accountId: 'acc_external_son_001',
        accountName: "Son's College Fund",
        accountType: 'external_savings',
        canTransferFrom: false, // Cannot transfer from son's account
        canTransferTo: true,
        isLocked: false,
        accountHolder: 'Michael Johnson (Son)',
      },
      {
        accountId: 'acc_investment_002',
        accountName: 'Retirement IRA',
        accountType: 'retirement',
        canTransferFrom: false, // Cannot transfer from retirement accounts
        canTransferTo: true,
        isLocked: false,
      },
    ];
  }

  /**
   * Get account balance by account type
   */
  static getAccountBalance(
    customerId: string,
    accountType: string,
  ): {
    customerId: string;
    accountType: string;
    balance: number;
    currency: string;
    asOfDate: string;
  } {
    // Mock balance data
    const balance = accountType === 'checking' ? 5432.18 : 12750.5;
    return {
      customerId,
      accountType,
      balance,
      currency: 'USD',
      asOfDate: new Date().toISOString(),
    };
  }

  /**
   * Get account statement with transactions
   */
  static getAccountStatement(
    customerId: string,
    accountType: string,
    days: number = 30,
  ): {
    customerId: string;
    accountType: string;
    startDate: string;
    endDate: string;
    transactions: Transaction[];
  } {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    // Mock transaction data
    const transactions: Transaction[] = [
      {
        date: '2025-12-18',
        description: 'Direct Deposit - Salary',
        amount: 3500.0,
        balance: 5432.18,
      },
      {
        date: '2025-12-15',
        description: 'Online Purchase - Amazon',
        amount: -87.43,
        balance: 1932.18,
      },
      {
        date: '2025-12-12',
        description: 'ATM Withdrawal',
        amount: -100.0,
        balance: 2019.61,
      },
      {
        date: '2025-12-10',
        description: 'Transfer to Savings',
        amount: -500.0,
        balance: 2119.61,
      },
    ];

    return {
      customerId,
      accountType,
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0],
      transactions,
    };
  }

  /**
   * Transfer money between accounts
   */
  static transferMoney(
    customerId: string,
    fromAccountId: string,
    toAccountId: string,
    amount: number,
    scheduledDate?: string,
    memo?: string,
  ): TransferResult {
    // Validate that from and to accounts are different
    if (fromAccountId === toAccountId) {
      throw new Error('Cannot transfer to the same account');
    }

    // Generate a mock transfer ID
    const transferId = `TXN-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const timestamp = new Date().toISOString();
    const status =
      scheduledDate !== undefined && scheduledDate !== ''
        ? 'scheduled'
        : 'completed';

    return {
      customerId,
      fromAccountId,
      toAccountId,
      amount,
      scheduledDate,
      memo,
      transferId,
      status,
      timestamp,
    };
  }

  /**
   * Validate a transfer request
   * Returns account details if valid, throws error if invalid
   */
  static validateTransfer(
    customerId: string,
    fromAccountId: string,
    toAccountId: string,
    amount: number,
  ): {
    fromAccount: Account;
    toAccount: Account;
  } {
    const accounts = this.getAccounts(customerId);
    const fromAccount = accounts.find(acc => acc.accountId === fromAccountId);
    const toAccount = accounts.find(acc => acc.accountId === toAccountId);

    if (!fromAccount) {
      throw new Error(`Source account ${fromAccountId} not found`);
    }

    if (!toAccount) {
      throw new Error(`Destination account ${toAccountId} not found`);
    }

    if (!fromAccount.canTransferFrom) {
      throw new Error(
        `Cannot transfer from ${fromAccount.accountName} - transfers not allowed`,
      );
    }

    if (!toAccount.canTransferTo) {
      throw new Error(
        `Cannot transfer to ${toAccount.accountName} - transfers not allowed`,
      );
    }

    if (amount <= 0) {
      throw new Error('Transfer amount must be greater than zero');
    }

    return { fromAccount, toAccount };
  }

  /**
   * Get mock transaction for confirmation/cancellation
   * In a real implementation, this would look up the transaction from storage
   */
  static getMockTransaction(customerId: string, transactionId: string) {
    const accounts = this.getAccounts(customerId);
    return {
      customerId,
      fromAccountId: accounts[0].accountId,
      fromAccountName: accounts[0].accountName,
      toAccountId: accounts[1].accountId,
      toAccountName: accounts[1].accountName,
      amount: 500.0,
      scheduledDate: new Date().toISOString().split('T')[0],
    };
  }
}
