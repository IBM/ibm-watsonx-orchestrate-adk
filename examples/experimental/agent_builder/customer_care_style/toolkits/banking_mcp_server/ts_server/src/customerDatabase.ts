/**
 * Customer Database Module
 *
 * Manages customer product information and lookup functionality
 */

/**
 * Customer product information
 */
export interface CustomerProducts {
  hasPersonalBanking: boolean;
  hasMortgage: boolean;
  hasCreditCard: boolean;
}

/**
 * Customer profile with personal information
 */
export interface CustomerProfile {
  customerId: string;
  firstName: string;
  lastName: string;
  telephoneNumber: string;
  pin: string;
  products: CustomerProducts;
}

/**
 * Mock customer database - maps customer IDs to their profiles
 */
const customerDatabase: Record<string, CustomerProfile> = {
  CUST001: {
    customerId: 'CUST001',
    firstName: 'John',
    lastName: 'Smith',
    telephoneNumber: '+15551234567',
    pin: '1234',
    products: {
      hasPersonalBanking: true,
      hasMortgage: false,
      hasCreditCard: true,
    },
  },
  CUST002: {
    customerId: 'CUST002',
    firstName: 'Jane',
    lastName: 'Doe',
    telephoneNumber: '+15559876543',
    pin: '5678',
    products: {
      hasPersonalBanking: true,
      hasMortgage: true,
      hasCreditCard: false,
    },
  },
  CUST003: {
    customerId: 'CUST003',
    firstName: 'Bob',
    lastName: 'Johnson',
    telephoneNumber: '+15555555555',
    pin: '9999',
    products: {
      hasPersonalBanking: true,
      hasMortgage: true,
      hasCreditCard: true,
    },
  },
  CUST004: {
    customerId: 'CUST004',
    firstName: 'Alice',
    lastName: 'Williams',
    telephoneNumber: '+15551111111',
    pin: '0000',
    products: {
      hasPersonalBanking: true,
      hasMortgage: false,
      hasCreditCard: false,
    },
  },
};

/**
 * Telephone number to customer ID mapping
 */
const telephoneToCustomerId: Record<string, string> = {
  '+15551234567': 'CUST001',
  '+15559876543': 'CUST002',
  '+15555555555': 'CUST003',
  '+15551111111': 'CUST004',
};

/**
 * Lookup customer products by customer ID
 */
export function getCustomerProducts(customerId: string): CustomerProducts {
  return (
    customerDatabase[customerId]?.products ?? {
      hasPersonalBanking: false,
      hasMortgage: false,
      hasCreditCard: false,
    }
  );
}

/**
 * Lookup customer profile by customer ID
 */
export function getCustomerProfile(
  customerId: string,
): CustomerProfile | undefined {
  return customerDatabase[customerId];
}

/**
 * Lookup customer profile by telephone number
 */
export function getCustomerProfileByPhone(
  telephoneNumber: string,
): CustomerProfile | undefined {
  const customerId = telephoneToCustomerId[telephoneNumber];
  return customerId ? customerDatabase[customerId] : undefined;
}

/**
 * Verify customer PIN using telephone number
 */
export function verifyCustomerPin(
  telephoneNumber: string,
  pin: string,
): boolean {
  const profile = getCustomerProfileByPhone(telephoneNumber);
  return profile ? profile.pin === pin : false;
}
