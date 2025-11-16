Feature: Comdirect API Client Library
  As a developer
  I want to use a Python library to interact with the Comdirect API
  So that I can authenticate, manage tokens, and retrieve banking data with proper error handling

  Background:
    Given the Comdirect API base URL is configured
    And client credentials are provided
    And user credentials are provided
    And logging is configured with appropriate log levels

  # ============================================================================
  # Authentication Flow
  # ============================================================================

  Scenario: User triggers initial authentication successfully
    Given the user has valid Comdirect credentials
    When the user triggers authentication
    Then the library should generate a session UUID
    And the library should obtain an OAuth2 password credentials token
    And the library should log "INFO: Starting authentication flow"
    And the library should retrieve the session status
    And the library should log "INFO: Session UUID retrieved"
    And the library should create a TAN challenge
    And the library should log "INFO: TAN challenge created" with TAN type
    And the library should poll for TAN approval every 1 second
    And the library should log "DEBUG: Polling TAN status" for each poll attempt
    And the library should activate the session after TAN approval
    And the library should log "INFO: TAN approved, activating session"
    And the library should exchange for secondary token
    And the library should log "INFO: Authentication successful"
    And the library should store the access token
    And the library should store the refresh token
    And the library should store the token expiry timestamp
    And the authentication should be marked as complete

  Scenario: OAuth2 password credentials grant fails with invalid credentials
    Given the user has invalid Comdirect credentials
    When the user triggers authentication
    Then the library should attempt OAuth2 password credentials grant
    And the library should receive a 401 Unauthorized response
    And the library should log "ERROR: Authentication failed - Invalid credentials"
    And the library should raise an AuthenticationError exception
    And no tokens should be stored

  Scenario: TAN challenge times out after 60 seconds
    Given the user has valid Comdirect credentials
    And the authentication flow has reached the TAN polling stage
    When 60 seconds elapse without TAN approval
    Then the library should log "WARNING: TAN approval timeout"
    And the library should stop polling
    And the library should raise a TANTimeoutError exception
    And the authentication should be marked as failed

  Scenario: TAN challenge is approved via Push-TAN
    Given the authentication flow has reached the TAN polling stage
    And the TAN type is "P_TAN_PUSH"
    When the user approves the TAN in their smartphone app
    Then the library should detect status "AUTHENTICATED" in polling response
    And the library should log "INFO: TAN approved via P_TAN_PUSH"
    And the library should proceed to session activation

  Scenario: Session activation fails with wrong header format
    Given the authentication flow has reached the session activation stage
    When the library sends a PATCH request with incorrect x-once-authentication-info header
    Then the library should receive a 422 Unprocessable Entity response
    And the library should log "ERROR: Session activation failed - Incorrect header format"
    And the library should raise a SessionActivationError exception

  # ============================================================================
  # Automatic Token Refresh with AsyncIO
  # ============================================================================

  Scenario: Automatic token refresh triggered before expiration
    Given the library has valid banking tokens
    And the token expires in 120 seconds
    And the asyncio token refresh task is running
    When the current time reaches 120 seconds before expiration
    Then the library should automatically attempt token refresh
    And the library should log "INFO: Auto-refreshing token (120s before expiry)"
    And the library should send a refresh token request
    And the library should receive new access and refresh tokens
    And the library should update stored tokens
    And the library should update token expiry timestamp
    And the library should log "INFO: Token refresh successful"
    And the asyncio task should schedule next refresh

  Scenario: Token refresh succeeds with new tokens
    Given the library has valid banking tokens with refresh token
    When the library attempts to refresh tokens
    Then the library should POST to /oauth/token with grant_type=refresh_token
    And the library should log "DEBUG: Refreshing token"
    And the library should receive a 200 OK response
    And the library should extract new access_token from response
    And the library should extract new refresh_token from response
    And the library should extract expires_in from response
    And the library should calculate new expiry timestamp
    And the library should log "INFO: Token refreshed, expires in {expires_in}s"

  Scenario: Token refresh fails and triggers reauth callback
    Given the library has expired or invalid refresh token
    And a reauth callback function is registered
    When the library attempts to refresh tokens
    Then the library should receive a 401 Unauthorized response
    And the library should log "WARNING: Token refresh failed - token expired"
    And the library should invoke the reauth callback
    And the library should log "INFO: Reauth callback invoked"
    And the library should wait for user to trigger authentication
    And all tokens should be cleared

  Scenario: AsyncIO refresh task handles concurrent API requests
    Given the library has valid banking tokens
    And multiple async API requests are in progress
    When the token refresh is triggered automatically
    Then the library should acquire a token refresh lock
    And the library should log "DEBUG: Acquiring token refresh lock"
    And the library should complete the token refresh
    And the library should release the lock
    And the library should log "DEBUG: Token refresh lock released"
    And waiting API requests should retry with new token

  Scenario: Token refresh task restarts after authentication
    Given the user has just completed authentication
    And new tokens with expiry time are stored
    When the authentication completes successfully
    Then the library should start an asyncio token refresh task
    And the library should log "INFO: Token refresh task started"
    And the task should calculate next refresh time
    And the task should schedule refresh for 2 minutes before expiry

  # ============================================================================
  # Account Data Retrieval
  # ============================================================================

  Scenario: Retrieve account balances successfully
    Given the library is authenticated with valid tokens
    When the user requests account balances
    Then the library should check token expiry before request
    And the library should log "DEBUG: Fetching account balances"
    And the library should GET /api/banking/clients/user/v2/accounts/balances
    And the library should include Authorization header with bearer token
    And the library should include x-http-request-info header
    And the library should receive a 200 OK response
    And the library should parse the response into AccountBalance typed objects
    And the library should log "INFO: Retrieved {count} account balances"
    And the library should return a list of AccountBalance objects

  Scenario: Account balances request fails with expired token
    Given the library has an expired access token
    And a reauth callback is registered
    When the user requests account balances
    Then the library should GET /api/banking/clients/user/v2/accounts/balances
    And the library should receive a 401 Unauthorized response
    And the library should log "WARNING: API request failed - token expired"
    And the library should attempt automatic token refresh
    And if refresh fails, the library should invoke the reauth callback
    And the library should raise a TokenExpiredError exception

  Scenario: Parse account balance response into typed structures
    Given the library receives a valid account balances response
    When the library parses the response
    Then each account balance should be converted to an AccountBalance object
    And each AccountBalance should have an accountId property of type str
    And each AccountBalance should have an account property of type Account
    And each AccountBalance should have a balance property of type AmountValue
    And each AccountBalance should have a balanceEUR property of type AmountValue
    And each AccountBalance should have an availableCashAmount property of type AmountValue
    And the Account object should have properly typed fields
    And the AmountValue objects should have value as Decimal and unit as str
    And the library should log "DEBUG: Parsed {count} account balance objects"

  # ============================================================================
  # Transaction Retrieval
  # ============================================================================

  Scenario: Retrieve transactions for a specific account
    Given the library is authenticated with valid tokens
    And an account with accountId exists
    When the user requests transactions for the accountId
    Then the library should check token expiry before request
    And the library should log "DEBUG: Fetching ALL transactions for account {accountId}"
    And the library should GET /api/banking/v1/accounts/{accountId}/transactions
    And the library should include Authorization header with bearer token
    And the library should include x-http-request-info header
    And the library should receive a 200 OK response
    And the library should parse the response into Transaction typed objects
    And the library should log "INFO: Retrieved {count} transactions"
    And the library should return a list of Transaction objects

  Scenario: Retrieve transactions with transaction direction filter
    Given the library is authenticated with valid tokens
    And an account with accountId exists
    When the user requests transactions with transactionDirection="DEBIT"
    Then the library should add query parameter "transactionDirection=DEBIT"
    And the library should log "DEBUG: Fetching ALL transactions for account {accountId} (direction: DEBIT)"
    And the library should return only debit transactions

  Scenario: Retrieve transactions with booking status filter
    Given the library is authenticated with valid tokens
    And an account with accountId exists
    When the user requests transactions with transactionState="BOOKED"
    Then the library should add query parameter "transactionState=BOOKED"
    And the library should log "DEBUG: Fetching ALL transactions for account {accountId} (state: BOOKED)"
    And the library should return only booked transactions

   Scenario: Parse transaction response into typed structures
     Given the library receives a valid transactions response
     When the library parses the response
     Then each transaction should be converted to a Transaction object
     And each Transaction should have a bookingStatus property of type str
     And each Transaction should have a bookingDate property of type Optional[date]
     And each Transaction should have an amount property of type Optional[AmountValue]
     And each Transaction should have optional remitter property of type Optional[AccountInformation]
     And each Transaction should have optional creditor property of type Optional[AccountInformation]
     And each Transaction should have a reference property of type str
     And each Transaction should have a transactionType property of type Optional[EnumText]
     And each Transaction should have a remittanceLines field of type list[str]
     And each Transaction should expose a remittance_lines property returning the same list
     And negative amounts should indicate outgoing transactions
     And positive amounts should indicate incoming transactions
     And the library should log "DEBUG: Parsed {count} transaction objects"


   Scenario: Handle transactions with null optional fields gracefully
     Given the library receives a transactions response with null fields
     And some transactions have null amount
     And some transactions have null transactionType
     And some transactions have null bookingDate
     And some AccountInformation objects have null iban
     When the library parses the response
     Then the library should not raise an exception
     And Transaction objects should be created with None values for null fields
     And Transaction objects should have an empty remittanceLines list when remittanceInfo is missing or empty
     And the library should safely handle from_dict() calls on null nested objects
     And the library should log "DEBUG: Parsed {count} transaction objects"


  # ============================================================================
  # Error Handling and Logging
  # ============================================================================

  Scenario: Handle network timeout gracefully
    Given the library is authenticated with valid tokens
    When a network timeout occurs during an API request
    Then the library should log "ERROR: Network timeout during API request"
    And the library should raise a NetworkTimeoutError exception
    And the library should not clear stored tokens

  Scenario: Handle account not found (404)
    Given the library is authenticated with valid tokens
    When the user requests transactions for a non-existent accountId
    Then the library should receive a 404 Not Found response
    And the library should log "ERROR: Account {accountId} not found"
    And the library should raise an AccountNotFoundError exception

  Scenario: Logging levels are appropriate for different events
    Given the library is initialized with logging configured
    Then DEBUG level should be used for detailed flow information
    And INFO level should be used for significant events
    And WARNING level should be used for recoverable errors
    And ERROR level should be used for failures requiring attention
    And sensitive data like tokens and passwords should never be logged
    And token prefixes (first 8 chars) may be logged for debugging

  Scenario: Sanitize sensitive data in logs
    Given the library is performing authentication
    When logging authentication events
    Then passwords should never appear in logs
    And access tokens should never appear in full
    And refresh tokens should never appear in full
    And only non-sensitive identifiers should be logged
    And the library should log "DEBUG: Token received: {token_prefix}..."

  # ============================================================================
  # Reauth Callback Mechanism
  # ============================================================================

  Scenario: Register reauth callback function
    Given the library is initialized
    When the user registers a reauth callback function
    Then the callback should be stored internally
    And the library should log "INFO: Reauth callback registered"
    And the callback should be invoked when reauth is needed

  Scenario: Reauth callback is invoked when refresh fails
    Given a reauth callback is registered
    And the library attempts token refresh
    When the refresh fails with 401 error
    Then the library should invoke the reauth callback
    And the library should log "INFO: Invoking reauth callback"
    And the callback should receive an error reason parameter
    And the library should clear all stored tokens
    And the library should pause the asyncio refresh task

  Scenario: Reauth callback is invoked on persistent 401 errors
    Given a reauth callback is registered
    And the access token is expired and refresh will also fail
    And a reauth callback is registered to capture persistent failure
    When the user requests account balances and receives repeated 401 responses
    Then the library should attempt token refresh and fail
    And the reauth callback should be invoked with reason api_request_unauthorized
    And tokens should be cleared after persistent authentication failure
    And a TokenExpiredError should be raised to the caller

  Scenario: User triggers authentication after reauth callback
    Given the reauth callback was invoked
    And all tokens were cleared
    When the user triggers authentication again
    Then the library should restart the full authentication flow
    And the library should log "INFO: Re-authentication started"
    And after successful auth, the asyncio refresh task should restart

  # ============================================================================
  # Type Safety and Data Structures
  # ============================================================================

  Scenario: AccountBalance type structure is correctly defined
    Given the library defines an AccountBalance dataclass or Pydantic model
    Then it should have field account of type Account
    And it should have field accountId of type str
    And it should have field balance of type AmountValue
    And it should have field balanceEUR of type AmountValue
    And it should have field availableCashAmount of type AmountValue
    And it should have field availableCashAmountEUR of type AmountValue
    And all fields should have proper type hints

  Scenario: Account type structure is correctly defined
    Given the library defines an Account dataclass or Pydantic model
    Then it should have field accountId of type str
    And it should have field accountDisplayId of type str
    And it should have field currency of type str
    And it should have field clientId of type str
    And it should have field accountType of type EnumText
    And it should have field iban of type Optional[str]
    And it should have field bic of type Optional[str]
    And it should have field creditLimit of type Optional[AmountValue]

  Scenario: Transaction type structure is correctly defined
    Given the library defines a Transaction dataclass or Pydantic model
    Then it should have field bookingStatus of type str
    And it should have field bookingDate of type Optional[date]
    And it should have field amount of type Optional[AmountValue]
    And it should have field remitter of type Optional[AccountInformation]
    And it should have field debtor of type Optional[AccountInformation]
    And it should have field creditor of type Optional[AccountInformation]
    And it should have field reference of type str
    And it should have field valutaDate of type str
    And it should have field transactionType of type Optional[EnumText]
    And it should have field remittanceInfo of type Optional[str]
    And it should have field newTransaction of type bool

  Scenario: AmountValue type structure is correctly defined
    Given the library defines an AmountValue dataclass or Pydantic model
    Then it should have field value of type Decimal
    And it should have field unit of type str
    And the value should be parsed from string to Decimal
    And the structure should support arithmetic operations safely

  Scenario: EnumText type structure is correctly defined
    Given the library defines an EnumText dataclass or Pydantic model
    Then it should have field key of type str
    And it should have field text of type str

  Scenario: AccountInformation type structure is correctly defined
    Given the library defines an AccountInformation dataclass or Pydantic model
    Then it should have field holderName of type str
    And it should have field iban of type Optional[str]
    And it should have field bic of type Optional[str]

  # ============================================================================
  # Session Management
  # ============================================================================

  Scenario: Session UUID is generated and reused throughout authentication
    Given the user triggers authentication
    When the library starts the authentication flow
    Then a random UUID v4 should be generated for sessionId
    And the sessionId should be stored for the session
    And the library should log "DEBUG: Generated session ID: {session_id_prefix}..."
    And the same sessionId should be used in all x-http-request-info headers
    And the sessionId should persist across all API calls until logout

  Scenario: Request ID is generated for each API call
    Given the library needs to make an API call
    When generating the x-http-request-info header
    Then the library should get current timestamp in milliseconds
    And the library should extract last 9 digits
    And the requestId should be exactly 9 digits
    And each API call should have a unique requestId
    And the library should log "DEBUG: Request ID: {request_id}"

  # ============================================================================
  # Library Configuration
  # ============================================================================

  Scenario: Initialize library with configuration
    Given the user wants to use the library
    When the user initializes the ComdirectClient
    Then the user should provide client_id
    And the user should provide client_secret
    And the user should provide username
    And the user should provide password
    And the user may optionally provide base_url (default: https://api.comdirect.de)
    And the user may optionally provide reauth_callback function
    And the user may optionally provide token_refresh_threshold_seconds (default: 120)
    And the library should validate all required parameters
    And the library should log "INFO: ComdirectClient initialized"

  Scenario: Library exposes async interface for API calls
    Given the library is initialized
    Then the library should provide async method authenticate()
    And the library should provide async method get_account_balances()
    And the library should provide async method get_transactions(account_id, ...)
    And the library should provide async method refresh_token()
    And the library should provide method is_authenticated() returning bool
    And the library should provide method get_token_expiry() returning Optional[datetime]
    And all async methods should be properly typed with return types

  # ============================================================================
  # Integration Scenarios
  # ============================================================================

  Scenario: Complete workflow from authentication to transaction retrieval
    Given the user initializes the library with credentials
    When the user calls authenticate() and completes TAN
    Then authentication should succeed
    And tokens should be stored
    And asyncio refresh task should start
    When the user calls get_account_balances()
    Then a list of AccountBalance objects should be returned
    When the user extracts an accountId from the balances
    And the user calls get_transactions(accountId)
    Then a list of Transaction objects should be returned
    And all operations should be logged appropriately

  Scenario: Workflow with automatic token refresh
    Given the user is authenticated
    And the library has been running for 8 minutes
    When the asyncio task detects token will expire in 2 minutes
    Then the library should automatically refresh the token
    And subsequent API calls should use the new token
    And the user should not need to re-authenticate
    And the workflow should continue seamlessly

  Scenario: Workflow with reauth required
    Given the user is authenticated
    And the library has been running for 15 minutes
    When the token expires and refresh also fails
    Then the reauth callback should be invoked
    And the user should be notified
    When the user calls authenticate() again
    Then a new authentication flow should complete
    And normal operations should resume

  # ============================================================================
  # New: HTTP Error Handling (422, 500)
  # ============================================================================

  Scenario: Handle validation error (422) in account balances request
    Given the user is authenticated
    When the user requests account balances with invalid query parameters
    Then the library should receive a 422 Unprocessable Entity response
    And the library should log "ERROR: Account balances request failed - validation error"
    And the library should raise a ValidationError exception
    And the exception message should contain "Invalid request parameters"

  Scenario: Handle server error (500) in account balances request
    Given the user is authenticated
    When the API server returns a 500 Internal Server Error for account balances
    Then the library should log "ERROR: API server error during account balances request"
    And the library should raise a ServerError exception
    And the exception message should contain "500 Internal Server Error"

  Scenario: Handle validation error (422) in transactions request
    Given the user is authenticated
    And the user has a valid account ID
    When the user requests transactions with invalid query parameters
    Then the library should receive a 422 Unprocessable Entity response
    And the library should log "ERROR: Transactions request failed - validation error"
    And the library should raise a ValidationError exception

  Scenario: Handle server error (500) in transactions request
    Given the user is authenticated
    And the user has a valid account ID
    When the API server returns a 500 Internal Server Error for transactions
    Then the library should log "ERROR: API server error during transactions request"
    And the library should raise a ServerError exception

  # ============================================================================
  # New: Query Parameters for Account Attributes
  # ============================================================================

  Scenario: Request account balances without account master data
    Given the user is authenticated
    When the user calls get_account_balances with with_attributes=False
    Then the library should include "without-attr=account" in the query parameters
    And the library should send GET /api/banking/clients/user/v2/accounts/balances?without-attr=account
    And the response should not include account master data
    And the library should parse the response correctly

  Scenario: Request account balances excluding specific attributes
    Given the user is authenticated
    When the user calls get_account_balances with without_attributes="account,balance"
    Then the library should include "without-attr=account,balance" in the query parameters
    And the library should send the request with these parameters
    And the response should exclude the specified attributes

  Scenario: Request transactions without account details
    Given the user is authenticated
    And the user has a valid account ID
    When the user calls get_transactions with with_attributes=False
    Then the library should include "without-attr=account" in the query parameters
    And the library should send GET /api/banking/v1/accounts/{id}/transactions?without-attr=account
    And the response should not include account details
    And the library should parse the response correctly

  Scenario: Request transactions excluding specific attributes
    Given the user is authenticated
    And the user has a valid account ID
    When the user calls get_transactions with without_attributes="account,booking"
    Then the library should include "without-attr=account,booking" in the query parameters
    And the library should send the request with these parameters
    And the response should exclude the specified attributes

  # ============================================================================
  # New: "deptor" Field Name Handling
  # ============================================================================

  Scenario: Parse transaction with correct "debtor" field name
    Given the library receives a transaction response with "debtor" field
    When the library parses the transaction
    Then the transaction.debtor attribute should be populated correctly
    And the AccountInformation should contain holderName, iban, and bic

  Scenario: Parse transaction with Swagger spec typo "deptor" field name
    Given the library receives a transaction response with "deptor" field (Swagger typo)
    When the library parses the transaction
    Then the transaction.debtor attribute should be populated from "deptor"
    And the library should handle the typo gracefully with fallback logic
    And the AccountInformation should be correctly parsed

  Scenario: Prefer "debtor" over "deptor" when both present
    Given the library receives a transaction response with both "debtor" and "deptor" fields
    When the library parses the transaction
    Then the library should prefer the correct "debtor" field
    And transaction.debtor should be populated from "debtor"
    And "deptor" should be ignored

   # ============================================================================
   # New: remittance line marker handling
   # ============================================================================

   Scenario: Parse remittanceInfo with numbered line prefixes into remittanceLines
     Given the library receives a valid transactions response
     And some transactions have remittanceInfo values with numbered line prefixes
     When the library parses the response
     Then each Transaction should have a remittanceLines field of type list[str]
     And each Transaction should expose a remittance_lines property returning the same list
     And the library should detect numbered line markers (01, 02, 03, ... up to 99)
     And the library should support both short test-format remittanceInfo strings
     And the library should support long fixed-width remittanceInfo strings from the real API
     And for long-format strings, the library should detect markers using approximate spacing between markers
     And the library should extract the content after each marker as a logical line
     And the library should populate remittanceLines with one entry per logical line, in order
     And example "01AA02 N84G BFT2 Y5KY                02End-to-End-Ref.:                   03nicht angegeben                    " should produce remittanceLines:
       | AA02 N84G BFT2 Y5KY
       | End-to-End-Ref.:
       | nicht angegeben
     And example "01Storno Echtzeitüberweisung         02AA02 N84G BFT2 Y5KY                03Rückgabegrund:                     04Auf Veranlassung der Bank          " should produce remittanceLines:
       | Storno Echtzeitüberweisung
       | AA02 N84G BFT2 Y5KY
       | Rückgabegrund:
       | Auf Veranlassung der Bank
     And the library should strip trailing whitespace from each line
     And the library should skip empty lines after stripping


