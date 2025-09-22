# Web Verifier Cog

## Overview

The Web Verifier cog for Redbot provides a JWT-based verification system that integrates with external web services. Users must answer a verification question correctly, then complete verification through an external website. This cog includes a built-in web server and secure token management for seamless integration with your verification infrastructure.

## Features

- Automatically sends a verification question to new members via DM upon joining the server.
- Generates secure JWT tokens for external verification workflows.
- Built-in HTTP server to handle verification callbacks from external services.
- If the member provides correct answers and completes external verification, they are assigned a specified role.
- Administrative commands for configuring questions, roles, and JWT secrets.
- Secure member ID storage and management.

## Caveats

- This cog does not stop users from interacting with your server. The intent is that you lock all desired functionality behind the assigned verification role.
- Requires an external web service to handle the verification interface and submit verification results.
- JWT secrets must be at least 32 characters long for security.
- Verification tokens expire after 30 minutes.

## Installation

```text
[p]cog install reediculous456 web_verifier
[p]load web_verifier
```

## Commands

### User Commands

- `[p]verify`: Manually triggers the verification process if the user is not already verified.
- `[p]unverify`: Removes verification status and role from the user.

### Admin Commands (Guild-level)

- `[p]verifyset`: Parent command for all verification settings.
- `[p]verifyset addmember @User <member_id>`: Manually verify a user with a specific member ID.
- `[p]verifyset verifiedrole @RoleName`: Sets the role to be granted upon verification.
- `[p]verifyset question "Question" answer1 answer2`: Sets the verification question and accepted answers.
- `[p]verifyset url <URL>`: Sets the base URL for the external verification service.
- `[p]verifyset status`: Shows current verification configuration and warnings.
- `[p]verifyset showquestion`: Shows the current verification question (deleted after 60 seconds).
- `[p]verifyset setkickonfail true/false`: Enables or disables kicking users on verification failure.
- `[p]verifyset enabled true/false`: Enables or disables the verification process.
- `[p]verifyset viewmembers`: Lists all verified members and their member IDs.
- `[p]verifyset checkuser @User`: Checks verification status of a specific user.
- `[p]verifyset removemember @User`: Removes a user's verification record.

### Owner Commands (Bot-wide)

- `[p]verifyconfig setsecret <secret>`: Sets the JWT secret (minimum 32 characters, global setting).

## Usage

### Load the Cog

Load the Web Verifier cog using the bot's command in your Discord server:

```text
[p]load web_verifier
```

Replace `[p]` with your bot's command prefix.

### Setting the Verification Role

Set the role that will be granted upon successful verification:

```text
[p]verifyset verifiedrole @Verified
```

Replace `@Verified` with the actual role you want to assign.

### Setting the JWT Secret

Set a secure JWT secret (minimum 32 characters):

```text
[p]verifyconfig setsecret your_super_secure_secret_key_here_123456789
```

This secret will be used to sign and verify JWT tokens. Note that this is a bot-wide setting that requires bot owner permissions.

### Setting the Verification Question

Set the question and accepted answers:

```text
[p]verifyset question "What is your member ID?" 12345 67890 98765
```

Replace with your desired question and valid answers.

### Setting the Verification URL

Set the base URL for your external verification service:

```text
[p]verifyset url https://your-verification-site.com/verify
```

### Enabling Verification

Enable the verification process:

```text
[p]verifyset enabled true
```

### Manual Verification

Users can manually trigger the verification process:

```text
[p]verify
```

This command will only work if the user is not already verified and verification is enabled.

### Manual Admin Verification

Administrators can manually verify a user and assign them a member ID:

```text
[p]verifyset addmember @Username 12345
```

This will immediately grant the verified role and store the member ID for the user. The user will receive a DM notification if possible.

### Checking Configuration Status

View current verification settings and any configuration warnings:

```text
[p]verifyset status
```

## Verification Flow

1. **User joins server** or runs `[p]verify`
2. **Bot sends DM with question**:

   ```text
   Welcome! Please answer the following question correctly to gain access to the server. You have 90 seconds to answer.

   **What is your member ID?**
   ```

3. **User provides correct answer**
4. **Bot generates JWT token and sends verification URL**:

   ```text
   Correct! Now visit this link to complete verification:
   https://your-verification-site.com/verify?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

   This link will expire in 30 minutes.
   ```

5. **External service processes verification** and sends enhanced JWT back to bot
6. **Bot validates token, stores member ID, and grants role**

## Example Configuration

1. **Set the Verification Role**:

   ```text
   [p]verifyset verifiedrole @Verified
   ```

2. **Set JWT Secret**:

   ```text
   [p]verifyconfig setsecret my_very_secure_jwt_secret_key_123456789
   ```

3. **Set Question and Answers**:

   ```text
   [p]verifyset question "What is your member ID?" 12345 67890 98765
   ```

4. **Set Verification URL**:

   ```text
   [p]verifyset url https://your-verification-site.com/verify
   ```

5. **Enable Verification**:

   ```text
   [p]verifyset enabled true
   ```

6. **Check Configuration**:

   ```text
   [p]verifyset status
   ```

7. **Optional: Enable Kick on Fail**:

   ```text
   [p]verifyset setkickonfail true
   ```

## Technical Details

- **Main Class**: `WebVerifier`
- **Module File**: `web_verifier.py`
- **Web Server**: Runs on localhost:8080 by default
- **JWT Algorithm**: HS256
- **Token Expiration**: 30 minutes
- **Security**: Each guild has its own JWT secret
- **Storage**: Member IDs are stored in the bot's config system

## JWT Integration

### Initial JWT Payload (sent to external service)

```json
{
  "user_id": 123456789,
  "username": "User#1234",
  "guild_id": 987654321,
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Enhanced JWT Payload (sent back by external service)

```json
{
  "user_id": 123456789,
  "username": "User#1234",
  "guild_id": 987654321,
  "exp": 1234567890,
  "iat": 1234567890,
  "member_id": "user_provided_member_id"
}
```

## Requirements

- PyJWT==2.8.0
- aiohttp==3.8.6
- discord==2.3.2
- Red-DiscordBot==3.5.17

## Notes

- Ensure the bot has the necessary permissions to send DMs and manage roles in your server.
- The web server starts automatically when the cog loads.
- JWT secrets must be at least 32 characters long for security.
- Verification URLs expire after 30 minutes for security.
- If no verification role, question, or JWT secret is set, the bot will notify users to contact administrators.
- Your external verification service must sign the enhanced JWT with the same secret.
