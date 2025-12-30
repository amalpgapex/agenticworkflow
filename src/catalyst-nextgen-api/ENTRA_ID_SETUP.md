# Azure Entra ID Authentication Setup Guide

This guide explains how to set up Azure Entra ID (Azure AD) authentication for the Catalyst NextGen API.

## Overview

The API supports JWT token validation from Azure Entra ID. When enabled, it validates incoming Bearer tokens against your Entra ID tenant.

## Prerequisites

- Azure subscription with Entra ID access
- An app registration in your Entra ID tenant
- Application (client) ID and Tenant ID from your app registration

## Step 1: Register Your Application in Entra ID

1. Sign in to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations** → **New registration**
3. Fill in the application details:
   - **Name**: `Catalyst NextGen API`
   - **Supported account types**: "Accounts in this organizational directory only"
   - **Redirect URI**: Leave empty (not needed for API)
4. Click **Register**

## Step 2: Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission** → **Microsoft Graph** → **Application permissions**
3. Add any necessary permissions (optional for this API)
4. Click **Grant admin consent** (if available)

## Step 3: Get Your Credentials

1. In your app registration, go to **Overview**
2. Copy these values:
   - **Application (client) ID** - Use for `ENTRA_ID_CLIENT_ID`
   - **Directory (tenant) ID** - Use for `ENTRA_ID_TENANT_ID`

## Step 4: Configure Environment Variables

Update your `.env` file with the values from Step 3:

```env
# Enable Entra ID authentication
ENTRA_ID_ENABLED=true

# Your Entra ID tenant ID (directory ID)
ENTRA_ID_TENANT_ID=12345678-1234-1234-1234-123456789012

# Your app registration's client ID
ENTRA_ID_CLIENT_ID=87654321-4321-4321-4321-210987654321

# Audience (typically same as client ID)
ENTRA_ID_AUDIENCE=87654321-4321-4321-4321-210987654321

# For testing without RSA signature verification
ENTRA_ID_SIMPLE_VALIDATION=true

# For production with full RSA verification
# ENTRA_ID_SIMPLE_VALIDATION=false
```

## Step 5: Get an Access Token for Testing

You can get a test token using Azure CLI or Postman.

### Using Azure CLI:

```bash
az account get-access-token \
  --resource "87654321-4321-4321-4321-210987654321" \
  --scope "api://87654321-4321-4321-4321-210987654321/.default"
```

### Using Postman:

1. Create a new POST request to:
   ```
   https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token
   ```

2. In the body (form-data), add:
   - `client_id`: Your app registration's client ID
   - `scope`: `api://{client-id}/.default`
   - `grant_type`: `client_credentials`
   - `client_secret`: Create a client secret in your app registration first

3. Send the request and copy the `access_token` from the response

## Step 6: Test the API

### Using curl:

```bash
# Get an access token first
TOKEN=$(az account get-access-token --resource "your-client-id" --query accessToken -o tsv)

# Call the API with the token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/workflows
```

### Using Postman:

1. Create a new request to `http://localhost:8000/api/v1/workflows`
2. Go to **Authorization** tab
3. Select **Bearer Token** type
4. Paste your access token in the token field
5. Send the request

## Development vs Production

### Development Mode (Simple Validation)

```env
ENTRA_ID_SIMPLE_VALIDATION=true
```

- Validates token format and basic claims
- Does NOT verify cryptographic signature
- Useful for testing without setting up RSA verification
- **Not recommended for production**

### Production Mode (Full RSA Verification)

```env
ENTRA_ID_SIMPLE_VALIDATION=false
```

- Validates token format, claims, AND cryptographic signature
- Fetches public keys from Microsoft's JWKS endpoint
- Caches keys for performance
- **Recommended for production**

## Token Claims Extracted

The API extracts the following information from the token:

```python
{
    "user_id": "oid",           # Azure Entra ID object ID
    "email": "preferred_username",  # User's email
    "name": "name",             # Full name
    "given_name": "given_name",   # First name
    "family_name": "family_name"   # Last name
}
```

## Troubleshooting

### Token validation fails with "Key with kid not found"

- You're likely using `ENTRA_ID_SIMPLE_VALIDATION=false`
- The JWKS endpoint may be unreachable
- Check your internet connection and firewall settings
- Switch to `ENTRA_ID_SIMPLE_VALIDATION=true` for testing

### "Audience mismatch" error

- Ensure `ENTRA_ID_AUDIENCE` matches the resource/scope you requested the token for
- Usually this should be the same as `ENTRA_ID_CLIENT_ID`

### "Token has expired" error

- Your access token has expired
- Get a new token and try again

### "Invalid token" or "Token validation failed"

- Token is malformed or from a different Entra ID tenant
- Check that your token is a valid JWT
- Verify the tenant ID matches

## Fallback to Development Mode

If Entra ID is not fully configured, the API falls back to accepting `X-User-Id` header:

```bash
curl -H "X-User-Id: user@example.com" \
  http://localhost:8000/api/v1/workflows
```

This is useful for development and testing without Entra ID setup.

## Additional Resources

- [Azure Entra ID Documentation](https://learn.microsoft.com/en-us/entra/)
- [App Registration in Entra ID](https://learn.microsoft.com/en-us/entra/identity-platform/app-registration-ref)
- [JWT Bearer Token Authentication](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens)
- [Protected API Sample](https://github.com/Azure-Samples/ms-identity-python-flask-webapp-call-graph)
