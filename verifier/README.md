# Verifier Cog for Redbot

## Overview

The Verifier cog for Redbot provides a way to handle user verification with a series of questions. Users must answer the questions correctly to gain access to the server. This cog also includes commands for server administrators to configure the verification questions and the role to be assigned upon successful verification.

## Features

- Automatically sends a series of questions to new members via DM upon joining the server.
- If the new member answers all questions correctly, they are assigned a specified role.
- Includes a command for users to manually trigger the verification process.
- Administrative commands for setting the role and managing the questions.

## Installation

1. Ensure you have [Redbot](https://github.com/Cog-Creators/Red-DiscordBot) installed and running.
2. Place the `verifier.py` file in your `cogs` directory.

## Usage

### Load the Cog

Load the Verifier cog using the bot's command in your Discord server:

```;
[p]load verifier
```

Replace `[p]` with your bot's command prefix.

### Setting the Verification Role

Set the role that will be granted upon successful verification:

```;
[p]verifyset setonboardrole @RoleName
```

Replace `@RoleName` with the actual role you want to assign.

### Adding Verification Questions

Add questions to the verification process:

```;
[p]verifyset addquestion "What is 2+2?" "4"
```

Replace the question and answer with your desired verification question and correct answer.

### Listing Verification Questions

List all configured verification questions:

```;
[p]verifyset listquestions
```

### Manually Trigger Verification

Users can manually trigger the verification process using the following command:

```;
[p]verify
```

This command will only work if the user is not already verified.

## Commands

### User Command

- `[p]verify`: Manually triggers the verification process if the user is not already verified.

### Admin Commands

- `[p]verifyset`: Parent command for all verification settings.
- `[p]verifyset setonboardrole @RoleName`: Sets the role to be granted upon correct answers.
- `[p]verifyset addquestion "Question" "Answer"`: Adds a question to the verification quiz.
- `[p]verifyset listquestions`: Lists all verification questions.

## Example Configuration

1. **Set the Verification Role**:

   ```;
   [p]verifyset setonboardrole @Verified
   ```

2. **Add Questions**:

   ```;
   [p]verifyset addquestion "What is 2+2?" "4"
   [p]verifyset addquestion "What is the capital of France?" "Paris"
   ```

3. **List Questions**:

   ```;
   [p]verifyset listquestions
   ```

4. **Manual Verification**:

   ```;
   [p]verify
   ```

## Notes

- Ensure the bot has the necessary permissions to send DMs and manage roles in your server.
- If no verification role or questions are set, the bot will notify the user to contact the server administrators for configuration.
