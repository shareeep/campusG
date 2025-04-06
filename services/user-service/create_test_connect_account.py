import os
import stripe
import json
from datetime import datetime

# Set Stripe API key from environment
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
if not STRIPE_SECRET_KEY:
    print("ERROR: STRIPE_SECRET_KEY environment variable not set")
    print("Please set the STRIPE_SECRET_KEY environment variable before running this script.")
    exit(1)

stripe.api_key = STRIPE_SECRET_KEY

def create_test_connect_account():
    """Create a Stripe Connect account for testing
    
    This script helps create a Stripe Connect Express account 
    in test mode that can be used for testing payment transfers.
    """
    print("Stripe Connect Test Account Generator")
    print("====================================")
    print("This tool will create a test Connect account in Stripe.")
    print("Note: You're using the API key:", "sk_test_..." + STRIPE_SECRET_KEY[-4:])
    
    if not STRIPE_SECRET_KEY.startswith('sk_test_'):
        print("\nWARNING: You appear to be using a production API key!")
        confirm = input("Are you sure you want to continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation canceled.")
            return
    
    # Get runner information
    email = input("\nEnter runner email: ")
    first_name = input("Enter runner first name: ")
    last_name = input("Enter runner last name: ")
    full_name = f"{first_name} {last_name}"
    
    # Create Connect Express account
    try:
        print("\nCreating Stripe Connect Express account...")
        account = stripe.Account.create(
            type="express",
            country="SG",
            email=email,
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            metadata={
                "created_at": datetime.now().isoformat(),
                "created_by": "test_script",
                "environment": "test" if STRIPE_SECRET_KEY.startswith('sk_test_') else "production",
                "name": full_name
            },
            business_type="individual",
            business_profile={
                "name": full_name,
                "product_description": "Food delivery services"
            }
        )
        
        print(f"\nSuccess! Connect account created with ID: {account.id}")
        print("\nAccount Details:")
        print(f"  - ID: {account.id}")
        print(f"  - Email: {email}")
        print(f"  - Type: {account.type}")
        print(f"  - Capabilities: {account.capabilities}")
        
        # Instructions for usage
        print("\nTo use this account in your application:")
        print("1. Store this Connect account ID with the runner's profile")
        print("2. Update the user record in your database with:")
        print(f"   user.stripe_connect_account_id = '{account.id}'")
        
        # Output JSON for easy copying
        account_data = {
            "stripe_connect_account_id": account.id,
            "email": email,
            "name": full_name,
            "created_at": datetime.now().isoformat()
        }
        
        print("\nJSON output for reference:")
        print(json.dumps(account_data, indent=2))
        
        return account.id
        
    except stripe.error.StripeError as e:
        print(f"\nError creating Connect account: {str(e)}")
        return None
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        return None

if __name__ == "__main__":
    create_test_connect_account()
