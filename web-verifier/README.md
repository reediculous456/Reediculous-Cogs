# Web Verifier Cog - JWT-Based Verification System

A Discord bot cog that handles user verification using JWT tokens and web requests.

## Features

- **Static Question**: Asks users a single configurable question (default: "What is your member ID?")
- **JWT Token Generation**: Generates secure JWT tokens containing user information
- **Web-based Verification**: Users receive a URL with a JWT token to complete verification
- **Member ID Storage**: Stores member IDs for verified users
- **Web Server**: Built-in HTTP server to handle verification requests

## How It Works

1. When a user joins the server (or runs `!verify`), they receive a DM with:
   - The verification question
   - A unique URL containing a JWT token

2. The JWT token contains:
   - User's Discord ID
   - Username
   - Guild ID
   - Expiration time (30 minutes)

3. When your verification site calls the webhook with a JWT token and member_id, the bot:
   - Validates the JWT token
   - Stores the member ID for the user
   - Grants the verified role
   - Sends a confirmation message

## Setup Commands

### Basic Setup

- `!verifyset verifiedrole @RoleName` - Set the role granted upon verification
- `!verifyset question <question>` - Set the verification question
- `!verifyset url <base_url>` - Set the verification URL base
- `!verifyset enabled true` - Enable verification

### Management Commands

- `!verifyset status` - View current settings
- `!verifyset viewquestion` - View the current question
- `!verifyset viewmembers` - List all verified members and their member IDs
- `!verifyset removemember @User` - Remove a user's verification record
- `!verifyset regeneratesecret` - Generate new JWT secret (invalidates existing tokens)

### User Commands

- `!verify` - Manually trigger verification process

## Verification Flow

1. User joins server
2. Bot sends DM:

   ```text
   Welcome! To complete verification, please answer this question:

   **What is your member ID?**

   Once you have your answer, visit this link to complete verification:
   https://your-verification-site.com/verify?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

   This link will expire in 30 minutes.
   ```

3. User completes verification on your site
4. Your site calls webhook: `http://localhost:8080/verify?jwt=<token>&member_id=<id>`
5. Bot verifies the token, stores the member ID, and grants the role

## Technical Details

- **Main Class**: `WebVerifier` (renamed from `Verifier`)
- **Module File**: `web_verifier.py`
- **Web Server**: Runs on localhost:8080 by default
- **JWT Algorithm**: HS256
- **Token Expiration**: 30 minutes
- **Security**: Each guild has its own JWT secret
- **Storage**: Member IDs are stored in the bot's config system

## Requirements

- PyJWT==2.8.0
- aiohttp==3.8.6
- discord==2.3.2
- Red-DiscordBot==3.5.17

## Notes

- The web server starts automatically when the cog loads
- JWT secrets are generated automatically per guild
- Verification URLs expire after 30 minutes for security
- Your verification site should call the webhook endpoint with the JWT token and member_id parameter
