# Web Verifier Cog

## Overview

The Web Verifier cog for Redbot provides a JWT-based verification system that integrates with external web services. Users must answer a verification question correctly, then complete verification through an external website. This cog includes a built-in web server and secure token management for seamless integration with your verification infrastructure.

**🌐 Global Verification**: When a user verifies in one server, they are automatically verified across all servers where the bot is present and verification is enabled

## Features

- **Automatic Verification**: Sends verification questions to new members via DM upon joining
- **Secure JWT Integration**: Generates secure JWT tokens for external verification workflows
- **Built-in Web Server**: HTTP server to handle verification callbacks from external services (configurable port)
- **Role Management**: Automatically assigns verified roles upon successful verification
- **Cross-Server Verification**: Global verification system works across all participating servers
- **Flexible Configuration**: Both global and guild-specific settings with priority system
- **Admin Tools**: Comprehensive commands for managing questions, roles, and user verification status
- **Analytics**: Detailed logging and analysis of incorrect verification attempts
- **Security Features**: JWT expiration, secret validation, and secure token handling

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

- `[p]verifyset`: Parent command for all verification settings
- `[p]verifyset verifiedrole @RoleName`: Sets the role to be granted upon verification
- `[p]verifyset clearverifiedrole`: Clears the verified role setting for this guild
- `[p]verifyset question "Question" answer1 answer2`: Sets a guild-specific verification question (overrides global question)
- `[p]verifyset clearquestion`: Clears the guild question to use global fallback (only works if global question exists)
- `[p]verifyset status`: Shows current verification configuration and warnings
- `[p]verifyset showquestion`: Shows the currently active verification question with source indication (deleted after 60 seconds)
- `[p]verifyset setkickonfail true/false`: Enables or disables kicking users on verification failure
- `[p]verifyset verifyonjoin true/false`: Enables or disables automatic verification trigger when users join
- `[p]verifyset enabled true/false`: Enables or disables the verification process
- `[p]verifyset checkuser @User`: Checks global verification status of a specific user

### Owner Commands (Bot-wide)

- `[p]verifyconfig setsecret <secret>`: Sets the JWT secret (minimum 32 characters, global setting)
- `[p]verifyconfig setport <port>`: Sets the port for the verification web server (global setting, requires bot restart)
- `[p]verifyconfig url <URL>`: Sets the base URL for the external verification service (global setting)
- `[p]verifyconfig question "Question" answer1 answer2`: Sets a global verification question (fallback for guilds without custom questions)
- `[p]verifyconfig clearquestion`: Clears the global verification question
- `[p]verifyconfig showquestion`: Shows the global verification question specifically
- `[p]verifyconfig addmember @User <member_id>`: Manually verify a user globally with a specific member ID
- `[p]verifyconfig viewmembers`: Lists all globally verified members and their member IDs
- `[p]verifyconfig removemember @User`: Removes a user's global verification record and roles from all servers
- `[p]verifyconfig checkuser @User`: Checks global verification status of a specific user (owner version with more details)
- `[p]verifyconfig incorrectanswers [limit]`: View logged incorrect answers grouped by normalized form with statistics (default limit: 20)
- `[p]verifyconfig clearincorrectanswers`: Clear all logged incorrect answers (requires confirmation)

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

### Setting Verification Questions

You can set questions at two levels with a priority system:

**Global Question (fallback for all guilds):**

```text
[p]verifyconfig question "What is your member ID?" 12345 67890 98765
```

**Guild-Specific Question (overrides global):**

```text
[p]verifyset question "What is your guild-specific member ID?" 11111 22222 33333
```

**Clear Guild Question (revert to global):**

```text
[p]verifyset clearquestion
```

**Priority System:**

1. If a guild has its own question set → Guild question is used
2. If no guild question is set → Global question is used as fallback
3. If neither is set → Verification will fail with an error message

Replace with your desired questions and valid answers.

### Setting the Verification URL

Set the base URL for your external verification service:

```text
[p]verifyconfig url https://your-verification-site.com/verify
```

### Enabling Verification

Enable the verification process:

```text
[p]verifyset enabled true
```

### Configure Verification on Join (Optional)

Control whether verification automatically starts when users join:

```text
[p]verifyset verifyonjoin true
```

### Manual Verification

Users can manually trigger the verification process:

```text
[p]verify
```

This command will only work if the user is not already verified and verification is enabled.

### User Self-Removal (Unverify)

Users can remove their own verification status:

```text
[p]unverify
```

This will prompt for confirmation, then kick the user from all servers and remove their verification record globally.

### Manual Admin Verification

Bot owners can manually verify a user globally and assign them a member ID:

```text
[p]verifyconfig addmember @Username 12345
```

This will immediately grant the verified role across all servers where the bot is present, verification is enabled, and a verified role is configured. The user will receive a DM notification if possible.

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
6. **Bot validates token, stores member ID globally, and grants role across all applicable servers**

## Example Configuration

1. **Set the Verification Role**:

   ```text
   [p]verifyset verifiedrole @Verified
   ```

2. **Set JWT Secret**:

   ```text
   [p]verifyconfig setsecret my_very_secure_jwt_secret_key_123456789
   ```

3. **Set Global Question (fallback)**:

   ```text
   [p]verifyconfig question "What is the meaning of life?" 42 "forty-two" "forty two"
   ```

   **Optional - Set Guild-Specific Question (overrides global)**:

   ```text
   [p]verifyset question "What is this guild's special code?" SECRET123 secret123
   ```

4. **Set Verification URL**:

   ```text
   [p]verifyconfig url https://your-verification-site.com/verify
   ```

5. **Enable Verification**:

   ```text
   [p]verifyset enabled true
   ```

6. **Check Configuration**:

   ```text
   [p]verifyset status
   ```

7. **Optional Configuration**:

   **Enable Kick on Fail**:

   ```text
   [p]verifyset setkickonfail true
   ```

   **Set Custom Port (requires bot restart)**:

   ```text
   [p]verifyconfig setport 8080
   ```

   **Configure Verification on Join**:

   ```text
   [p]verifyset verifyonjoin true
   ```

## Incorrect Answer Logging

The Web Verifier cog automatically logs all incorrect answers provided during the verification process. This feature helps administrators identify common mistakes, potential confusion points, or suspicious verification attempts.

### Logging Features

- **Normalized Grouping**: Answers are grouped by their normalized form (spaces and special characters removed, case-insensitive) to identify similar responses.
- **Statistics Tracking**: Each incorrect answer group tracks:

  - Total number of attempts
  - Number of unique users who provided this answer
  - Original forms of the answer (preserving exact user input)
  - First and last seen timestamps

- **Admin Commands**: Bot owners can view and manage the incorrect answer logs.

### Viewing Incorrect Answers

Use the `incorrectanswers` command to view logged incorrect responses:

```text
[p]verifyconfig incorrectanswers 10
```

This displays the top 10 most common incorrect answers with statistics including:

- Number of attempts and unique users
- Time since last occurrence
- Original forms of the answer as typed by users
- Normalized form used for grouping

### Managing Logs

Bot owners can clear the incorrect answer logs when needed:

```text
[p]verifyconfig clearincorrectanswers
```

This command requires confirmation and will permanently delete all logged incorrect answers.

## Technical Details

- **Main Class**: `WebVerifier`
- **Module File**: `web_verifier.py`
- **Web Server**: Built-in aiohttp server (configurable port, default: 8080)
- **JWT Algorithm**: HS256
- **Token Expiration**: 30 minutes
- **Security**: Bot-wide JWT secret (minimum 32 characters) for all servers
- **Storage**: Member IDs and configuration stored globally in Red's config system
- **Global Verification**: Users verified in one server are automatically verified in all other participating servers
- **Incorrect Answer Logging**: Stores normalized incorrect answers with grouping, statistics, and timestamps
- **Event System**: Dispatches `member_verified` events for integration with other cogs
- **Answer Normalization**: Removes spaces and special characters, case-insensitive matching

## JWT Integration

### Initial JWT Payload (sent to external service)

```json
{
  "user_id": "123456789",
  "username": "SomeUser",
  "guild_id": "987654321",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Enhanced JWT Payload (sent back by external service)

```json
{
  "user_id": "123456789",
  "username": "SomeUser",
  "guild_id": "987654321",
  "exp": 1234567890,
  "iat": 1234567890,
  "member_id": "user_provided_member_id"
}
```

## Important Notes

- **Permissions**: Ensure the bot has necessary permissions to send DMs, manage roles, and kick members (if using kick on fail)
- **Web Server**: Starts automatically when the cog loads and stops when unloaded
- **Security Requirements**: JWT secrets must be at least 32 characters long for security
- **Token Expiration**: Verification URLs expire after 30 minutes for security
- **Configuration Validation**: The `status` command shows warnings for incomplete configuration
- **External Service**: Your verification service must sign the enhanced JWT with the same secret
- **Global System**: User verification status is shared across all participating servers
- **Answer Matching**: Answers are normalized (spaces/special chars removed, case-insensitive)
- **Fallback System**: Guild questions override global questions; if neither is set, verification fails
- **Event Integration**: Cog dispatches `member_verified` events for other cogs to listen to

## Troubleshooting

- **"Missing JWT secret"**: Use `[p]verifyconfig setsecret` with a 32+ character secret
- **"No question set"**: Set either a global or guild-specific question
- **"Guild not found"**: Ensure the bot is in the originating server
- **"Member not found"**: User may have left the server after starting verification
- **DM Issues**: Users must enable DMs from server members
- **Port conflicts**: Use `[p]verifyconfig setport` to change the web server port
- **Configuration warnings**: Check `[p]verifyset status` for detailed setup guidance
