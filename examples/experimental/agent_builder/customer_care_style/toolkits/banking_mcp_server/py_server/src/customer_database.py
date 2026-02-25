"""
Customer Database Module

Manages customer product information and lookup functionality.
"""

from dataclasses import dataclass


@dataclass
class CustomerProducts:
    """Customer product information."""

    has_personal_banking: bool
    has_mortgage: bool
    has_credit_card: bool


@dataclass
class CustomerProfile:
    """Customer profile with personal information."""

    customer_id: str
    first_name: str
    last_name: str
    telephone_number: str
    pin: str
    products: CustomerProducts


# Mock customer database - maps customer IDs to their profiles
_customer_database: dict[str, CustomerProfile] = {
    "CUST001": CustomerProfile(
        customer_id="CUST001",
        first_name="John",
        last_name="Smith",
        telephone_number="+15551234567",
        pin="1234",
        products=CustomerProducts(
            has_personal_banking=True,
            has_mortgage=False,
            has_credit_card=True,
        ),
    ),
    "CUST002": CustomerProfile(
        customer_id="CUST002",
        first_name="Jane",
        last_name="Doe",
        telephone_number="+15559876543",
        pin="5678",
        products=CustomerProducts(
            has_personal_banking=True,
            has_mortgage=True,
            has_credit_card=False,
        ),
    ),
    "CUST003": CustomerProfile(
        customer_id="CUST003",
        first_name="Bob",
        last_name="Johnson",
        telephone_number="+15555555555",
        pin="9999",
        products=CustomerProducts(
            has_personal_banking=True,
            has_mortgage=True,
            has_credit_card=True,
        ),
    ),
    "CUST004": CustomerProfile(
        customer_id="CUST004",
        first_name="Alice",
        last_name="Williams",
        telephone_number="+15551111111",
        pin="0000",
        products=CustomerProducts(
            has_personal_banking=True,
            has_mortgage=False,
            has_credit_card=False,
        ),
    ),
}

# Telephone number to customer ID mapping
_telephone_to_customer_id: dict[str, str] = {
    "+15551234567": "CUST001",
    "+15559876543": "CUST002",
    "+15555555555": "CUST003",
    "+15551111111": "CUST004",
}


def get_customer_products(customer_id: str) -> CustomerProducts:
    """Lookup customer products by customer ID."""
    profile = _customer_database.get(customer_id)
    if profile:
        return profile.products
    return CustomerProducts(
        has_personal_banking=False,
        has_mortgage=False,
        has_credit_card=False,
    )


def get_customer_profile(customer_id: str) -> CustomerProfile | None:
    """Lookup customer profile by customer ID."""
    return _customer_database.get(customer_id)


def get_customer_profile_by_phone(telephone_number: str) -> CustomerProfile | None:
    """Lookup customer profile by telephone number."""
    customer_id = _telephone_to_customer_id.get(telephone_number)
    return _customer_database.get(customer_id) if customer_id else None


def verify_customer_pin(telephone_number: str, pin: str) -> bool:
    """Verify customer PIN using telephone number."""
    profile = get_customer_profile_by_phone(telephone_number)
    return profile.pin == pin if profile else False
