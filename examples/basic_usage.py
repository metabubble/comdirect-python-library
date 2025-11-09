#!/usr/bin/env python3
"""Basic usage example for the Comdirect API client.

This example demonstrates:
1. Client initialization
2. Authentication with TAN challenge
3. Fetching account balances
4. Fetching transactions for an account
5. Automatic token refresh
6. Reauth callback handling
"""

import asyncio
import logging
import os
from datetime import datetime

from comdirect_client.client import ComdirectClient


# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def reauth_callback(reason: str):
    """Callback invoked when reauthentication is required.

    Args:
        reason: Reason why reauth is needed (e.g., "token_refresh_failed")
    """
    logger.warning(f"⚠️  Reauthentication required! Reason: {reason}")
    logger.info("You should restart the authentication flow")
    # In a real application, you might:
    # - Send a notification to the user
    # - Trigger a new authentication flow
    # - Store a flag in the database


async def main():
    """Main example function."""

    # Get credentials from environment variables
    client_id = os.getenv("COMDIRECT_CLIENT_ID")
    client_secret = os.getenv("COMDIRECT_CLIENT_SECRET")
    username = os.getenv("COMDIRECT_USERNAME")
    password = os.getenv("COMDIRECT_PASSWORD")

    if not all([client_id, client_secret, username, password]):
        logger.error("Missing required environment variables:")
        logger.error("  COMDIRECT_CLIENT_ID")
        logger.error("  COMDIRECT_CLIENT_SECRET")
        logger.error("  COMDIRECT_USERNAME")
        logger.error("  COMDIRECT_PASSWORD")
        return

    # Initialize client with async context manager
    async with ComdirectClient(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        base_url="https://api.comdirect.de",  # Production API
        reauth_callback=reauth_callback,  # Optional callback
        token_refresh_threshold_seconds=120,  # Refresh 2 minutes before expiry
    ) as client:
        logger.info("=" * 60)
        logger.info("Step 1: Authentication")
        logger.info("=" * 60)

        try:
            # Perform full authentication (Steps 1-5)
            # This will trigger a TAN challenge on your device
            await client.authenticate()

            logger.info("✅ Authentication successful!")

            # Check token expiry
            expiry = client.get_token_expiry()
            if expiry:
                logger.info(f"Token expires at: {expiry.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(
                    f"Token valid for: {(expiry - datetime.now()).total_seconds():.0f} seconds"
                )

        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return

        # Wait a bit to demonstrate the authentication is complete
        await asyncio.sleep(2)

        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 2: Fetch Account Balances")
        logger.info("=" * 60)

        try:
            balances = await client.get_account_balances()

            logger.info(f"✅ Found {len(balances)} accounts:")
            for balance in balances:
                logger.info(f"\n  Account: {balance.account.accountDisplayId}")
                logger.info(f"    Type: {balance.account.accountType.text}")
                logger.info(f"    Balance: {balance.balance.value} {balance.balance.unit}")
                logger.info(
                    f"    Available: {balance.availableCashAmount.value} {balance.availableCashAmount.unit}"
                )

        except Exception as e:
            logger.error(f"❌ Failed to fetch balances: {e}")
            return

        # Wait a bit
        await asyncio.sleep(2)

        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 3: Fetch Transactions")
        logger.info("=" * 60)

        if balances:
            # Get transactions for the first account
            account = balances[0]
            account_id = account.accountId

            try:
                # Fetch all transactions (default: BOTH booked and pending, CREDIT_AND_DEBIT)
                transactions = await client.get_transactions(
                    account_id=account_id,
                    # transaction_state="BOOKED",  # Optional: filter by booking state
                    # transaction_direction="DEBIT",  # Optional: filter by direction (CREDIT/DEBIT/CREDIT_AND_DEBIT)
                    # paging_first=0,  # Optional: pagination starting index
                )

                logger.info(f"✅ Found {len(transactions)} transactions:")

                # Display first 5 transactions
                for i, tx in enumerate(transactions[:10]):
                    logger.info(f"\n  Transaction {i+1}:")
                    logger.info(f"    Date: {tx.bookingDate or 'N/A'}")
                    if tx.amount:
                        logger.info(f"    Amount: {tx.amount.value} {tx.amount.unit}")
                    else:
                        logger.info("    Amount: N/A")
                    if tx.transactionType:
                        logger.info(f"    Type: {tx.transactionType.text}")
                    else:
                        logger.info("    Type: N/A")
                    logger.info(
                        f"    Text: {tx.remittanceInfo[:50] if tx.remittanceInfo else 'N/A'}..."
                    )

                if len(transactions) > 5:
                    logger.info(f"\n  ... and {len(transactions) - 5} more transactions")

            except Exception as e:
                logger.error(f"❌ Failed to fetch transactions: {e}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 4: Demonstrate Automatic Token Refresh")
        logger.info("=" * 60)

        logger.info("The client automatically refreshes tokens in the background.")
        logger.info("Tokens are refreshed 120 seconds before expiration.")
        logger.info("You can continue making API calls without worrying about token expiry.")

        # Example: Keep the client alive for a while
        logger.info("\nKeeping client alive for 30 seconds...")
        logger.info("(In production, the background task runs continuously)")
        await asyncio.sleep(30)

        logger.info("✅ Done! The client will clean up on exit.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
