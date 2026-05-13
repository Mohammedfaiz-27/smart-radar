# Social Accounts API Documentation

This document describes the updated Social Accounts API endpoints that now support both OAuth and manual connection methods for Facebook, Instagram, and WhatsApp.

## Base URL

```
http://localhost:8000/api/v1/social-accounts
```

## Authentication

All endpoints require authentication via JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## Endpoints

### 1. List Connected Accounts

**GET** `/social-accounts`

Returns all connected social media accounts for the authenticated tenant.

**Response:**
```json
{
  "success": true,
  "accounts": [
    {
      "id": "uuid",
      "platform": "facebook",
      "account_name": "My Facebook Page",
      "account_id": "123456789",
      "status": "connected",
      "permissions": ["publish_post", "read_insights"],
      "connected_at": "2024-01-01T12:00:00Z",
      "last_sync": "2024-01-01T12:00:00Z",
      "page_id": "123456789",
      "periskope_id": null
    }
  ]
}
```

### 2. Get Connection Requirements

**GET** `/social-accounts/connection-requirements/{platform}`

Returns platform-specific connection requirements and supported methods.

**Parameters:**
- `platform`: One of `facebook`, `instagram`, `whatsapp`, `twitter`, `linkedin`

**Response:**
```json
{
  "platform": "facebook",
  "oauth_supported": true,
  "manual_supported": true,
  "oauth_fields": ["auth_code"],
  "manual_fields": ["account_name", "page_id", "access_token"],
  "help_text": "For manual connection, you need your Facebook Page Name, Page ID, and Access Token. Page ID can be found in your Facebook Page settings."
}
```

### 3. Validate Manual Credentials

**POST** `/social-accounts/validate-credentials`

Validates manual connection credentials before connecting.

**Request Body:**
```json
{
  "platform": "facebook",
  "connection_method": "manual",
  "account_name": "My Facebook Page",
  "page_id": "123456789",
  "access_token": "your_access_token"
}
```

**Response:**
```json
{
  "is_valid": true,
  "platform": "facebook",
  "account_name": "My Facebook Page",
  "account_id": "123456789",
  "message": "Credentials are valid"
}
```

### 4. Connect Social Account

**POST** `/social-accounts/connect`

Connects a new social media account via OAuth or manual credentials.

#### OAuth Connection

**Request Body:**
```json
{
  "platform": "facebook",
  "connection_method": "oauth",
  "auth_code": "oauth_authorization_code"
}
```

#### Manual Connection

**Facebook:**
```json
{
  "platform": "facebook",
  "connection_method": "manual",
  "account_name": "My Facebook Page",
  "page_id": "123456789",
  "access_token": "your_facebook_access_token"
}
```

**Instagram:**
```json
{
  "platform": "instagram",
  "connection_method": "manual",
  "account_name": "my_instagram_handle",
  "access_token": "your_instagram_access_token"
}
```

**WhatsApp:**
```json
{
  "platform": "whatsapp",
  "connection_method": "manual",
  "account_name": "My WhatsApp Business",
  "periskope_id": "your_periskope_id"
}
```

**Response:**
```json
{
  "success": true,
  "id": "uuid",
  "platform": "facebook",
  "account_name": "My Facebook Page",
  "status": "connected",
  "connected_at": "2024-01-01T12:00:00Z"
}
```

### 5. Disconnect Social Account

**DELETE** `/social-accounts/{account_id}`

Disconnects a social media account.

**Response:**
```json
{
  "success": true,
  "message": "Account disconnected successfully"
}
```

### 6. Refresh Social Token

**POST** `/social-accounts/{account_id}/refresh-token`

Refreshes the access token for a social account.

**Response:**
```json
{
  "message": "Token refreshed successfully"
}
```

### 7. Check Account Status

**GET** `/social-accounts/{account_id}/status`

Checks the status of a social media account connection.

**Response:**
```json
{
  "id": "uuid",
  "platform": "facebook",
  "account_name": "My Facebook Page",
  "status": "connected",
  "permissions": ["publish_post", "read_insights"],
  "is_token_expired": false,
  "last_sync": "2024-01-01T12:00:00Z",
  "needs_refresh": false
}
```

## Platform-Specific Requirements

### Facebook

**Manual Connection Fields:**
- `account_name`: Your Facebook page name
- `page_id`: Facebook page ID (found in page settings)
- `access_token`: Facebook Graph API access token

**OAuth Fields:**
- `auth_code`: OAuth authorization code

### Instagram

**Manual Connection Fields:**
- `account_name`: Instagram account username
- `access_token`: Instagram Graph API access token

**OAuth Fields:**
- `auth_code`: OAuth authorization code

### WhatsApp

**Manual Connection Fields:**
- `account_name`: WhatsApp Business account name
- `periskope_id`: Your WhatsApp Business Periskope ID

**OAuth Fields:**
- `auth_code`: OAuth authorization code

### Twitter

**OAuth Only:**
- `auth_code`: OAuth authorization code

### LinkedIn

**OAuth Only:**
- `auth_code`: OAuth authorization code

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Account name and access token are required for manual connection"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 404 Not Found
```json
{
  "detail": "Social account not found"
}
```

### 409 Conflict
```json
{
  "detail": "Account already connected"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to connect social account"
}
```

## Security Considerations

### Token Encryption
- All access tokens are encrypted before storage
- Tokens are decrypted only when needed for API calls
- Encryption uses Fernet (symmetric encryption)

### Manual Connection Security
- Credentials are validated before storage
- Platform-specific validation rules are enforced
- No plain text logging of sensitive data

### OAuth Security
- State parameter validation (in production)
- Secure token storage
- Automatic token refresh
- Proper error handling

## Usage Examples

### Connect Facebook Page Manually

```bash
curl -X POST "http://localhost:8000/api/v1/social-accounts/connect" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "facebook",
    "connection_method": "manual",
    "account_name": "My Business Page",
    "page_id": "123456789",
    "access_token": "your_facebook_access_token"
  }'
```

### Connect Instagram via OAuth

```bash
curl -X POST "http://localhost:8000/api/v1/social-accounts/connect" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "instagram",
    "connection_method": "oauth",
    "auth_code": "oauth_authorization_code"
  }'
```

### Get Connection Requirements

```bash
curl -X GET "http://localhost:8000/api/v1/social-accounts/connection-requirements/facebook" \
  -H "Authorization: Bearer your_jwt_token"
```

### Validate Manual Credentials

```bash
curl -X POST "http://localhost:8000/api/v1/social-accounts/validate-credentials" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "whatsapp",
    "connection_method": "manual",
    "account_name": "My WhatsApp Business",
    "periskope_id": "your_periskope_id"
  }'
```

## Database Schema

The social accounts table includes the following fields:

```sql
CREATE TABLE social_accounts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  platform VARCHAR(50) NOT NULL,
  account_name VARCHAR(255) NOT NULL,
  account_id VARCHAR(255) NOT NULL,
  status VARCHAR(50) DEFAULT 'connected',
  permissions TEXT[],
  access_token_encrypted TEXT,
  refresh_token_encrypted TEXT,
  token_expires_at TIMESTAMP,
  connected_at TIMESTAMP DEFAULT NOW(),
  last_sync TIMESTAMP,
  page_id VARCHAR(255), -- Facebook specific
  periskope_id VARCHAR(255), -- WhatsApp specific
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

## Testing

Use the provided test script to verify endpoint functionality:

```bash
python test_social_endpoints.py
```

This will test all endpoints and validate the manual connection support.
