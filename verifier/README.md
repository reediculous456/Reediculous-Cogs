# Verifier Cog for Redbot

## Overview

The Verifier cog for Redbot provides a way to handle user verification with a series of questions. Users must answer the questions correctly to gain access to the server. This cog also includes commands for server administrators to configure the verification questions and the role to be assigned upon successful verification.

## Features

- Automatically sends a series of questions to new members via DM upon joining the server.
- If the new member answers all questions correctly, they are assigned a specified role.
- Includes a command for users to manually trigger the verification process.
- Administrative commands for setting the role and managing the questions.

## Caveats

- This cog does not stop users from interacting with your server. The intent is that you lock all desired functionality behind the assigned verification role.
- This cog does not offer a way for a user to contact a mod if they fail verification. My recommendation is to have a channel where users can ask for help if they fail verification.
- To help prevent issues with users failing verification, answers are not case sensitive. This means that "Paris" and "paris" are considered the same answer. Also, special characters are removed from answers before comparison. This means that "Paris!" and "Paris" are considered the same answer.

## Installation

```;
[p]cog install reediculous456 verifier
[p]load verifier
```

## Commands

### User Command

- `[p]verify`: Manually triggers the verification process if the user is not already verified.

### Admin Commands

- `[p]verifyset`: Parent command for all verification settings.
- `[p]verifyset setverifiedrole @RoleName`: Sets the role to be granted upon correct answers.
- `[p]verifyset addquestion "Question" "Answer"`: Adds a question to the verification quiz.
- `[p]verifyset removequestion <index>`: Removes a question from the verification quiz by its index.
- `[p]verifyset listquestions`: Lists all verification questions. List is deleted after 60 seconds.
- `[p]verifyset enabled true/false`: Enables or disables the verification process.
- `[p]verifyset setkickonfail true/false`: Enables or disables kicking users on verification failure.

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
[p]verifyset setverifiedrole @RoleName
```

Replace `@RoleName` with the actual role you want to assign.

### Adding Verification Questions

Add questions to the verification process:

```;
[p]verifyset addquestion "What is 2+2?" "4"
```

Replace the question and answer with your desired verification question and correct answer.

### Removing Verification Questions

Remove a question from the verification process by its index:

```;
[p]verifyset removequestion 1
```

Replace `1` with the index of the question you want to remove.

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

## Example Configuration

1. **Set the Verification Role**:

   ```;
   [p]verifyset setverifiedrole @Verified
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

5. **Enable/Disable Verification**:

   ```;
   [p]verifyset enabled true
   ```

6. **Optional: Kick on Fail**:

   ```;
    [p]verifyset setkickonfail true
    ```

## Notes

- Ensure the bot has the necessary permissions to send DMs and manage roles in your server.
- If no verification role or questions are set, the bot will notify the user to contact the server administrators for configuration.
