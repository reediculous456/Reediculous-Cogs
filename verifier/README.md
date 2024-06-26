# Verifier Cog

## Overview

The Verifier cog for Redbot provides a way to handle user verification with a series of questions. Users must answer the questions correctly to gain access to the server. This cog also includes commands for server administrators to configure the verification questions and the role to be assigned upon successful verification.

## Features

- Automatically sends a series of questions to new members via DM upon joining the server.
- If the new member answers all questions correctly, they are assigned a specified role.
- Includes a command for users to manually trigger the verification process.
- Administrative commands for setting the role and managing the questions.
- Support for "sticky" questions that are always asked first.

## Caveats

- This cog does not stop users from interacting with your server. The intent is that you lock all desired functionality behind the assigned verification role.
- This cog does not offer a way for a user to contact a mod if they fail verification. My recommendation is to have a channel where users can ask for help if they fail verification.
- To help prevent issues with users failing verification, answers are not case sensitive. This means that "Paris" and "paris" are considered the same answer. Also, special characters are removed from answers before comparison. This means that "Paris!" and "Paris" are considered the same answer.

## Installation

```text
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
- `[p]verifyset editquestion <index> "Question" "Answer"`: Edits a question in the verification quiz by its index.
- `[p]verifyset listquestions`: Lists all verification questions. List is deleted after 60 seconds.
- `[p]verifyset enabled true/false`: Enables or disables the verification process.
- `[p]verifyset setkickonfail true/false`: Enables or disables kicking users on verification failure.
- `[p]verifyset setnumquestions <number>`: Sets the number of questions to ask during verification.
- `[p]verifyset setstickyquestion <index> true/false`: Sets whether a question is sticky or not by its index. Sticky questions are always asked first, regardless of number of questions set.

## Usage

### Load the Cog

Load the Verifier cog using the bot's command in your Discord server:

```text
[p]load verifier
```

Replace `[p]` with your bot's command prefix.

### Setting the Verification Role

Set the role that will be granted upon successful verification:

```text
[p]verifyset setverifiedrole @RoleName
```

Replace `@RoleName` with the actual role you want to assign.

### Adding Verification Questions

Add questions to the verification process:

```text
[p]verifyset addquestion "What is 2+2?" "4"
```

Replace the question and answer with your desired verification question and correct answer.

### Removing Verification Questions

Remove a question from the verification process by its index:

```text
[p]verifyset removequestion 1
```

Replace `1` with the index of the question you want to remove.

### Editing Verification Questions

Edit a question in the verification process by its index:

```text
[p]verifyset editquestion 1 "What is 3+3?" "6" "six"
```

Replace `1` with the index of the question you want to edit, and update the question and answers as needed.

### Listing Verification Questions

List all configured verification questions:

```text
[p]verifyset listquestions
```

### Setting Sticky Questions

Set a question as sticky or not by its index:

```text
[p]verifyset setstickyquestion 1 true
```

Replace 1 with the index of the question you want to set as sticky, and true with false to unset it as sticky.

### Manually Trigger Verification

Users can manually trigger the verification process using the following command:

```text
[p]verify
```

This command will only work if the user is not already verified and verification is enabled.

### Setting Number of Questions to Ask

Set the number of questions to ask during the verification process:

```text
[p]verifyset setnumquestions 3
```

You also can use `True` to ask all questions in the list.

### Enabling/Disabling Kick on Fail

Enable or disable kicking users who fail the verification:

```text
[p]verifyset setkickonfail true
[p]verifyset setkickonfail false
```

### Enabling/Disabling Verification

Enable or disable the verification process:

```text
[p]verifyset enabled true
[p]verifyset enabled false
```

## Example Configuration

1. **Set the Verification Role**:

   ```text
   [p]verifyset setverifiedrole @Verified
   ```

2. **Add Questions**:

   ```text
   [p]verifyset addquestion "What is 2+2?" "4"
   [p]verifyset addquestion "What is the capital of France?" "Paris"
   ```

3. **List Questions**:

   ```text
   [p]verifyset listquestions
   ```

4. **Set a Question as Sticky**:

   ```text
   [p]verifyset setstickyquestion 1 true
   ```

5. **Manual Verification**:

   ```text
   [p]verify
   ```

6. **Enable/Disable Verification**:

   ```text
   [p]verifyset enabled true
   ```

7. **Optional: Kick on Fail**:

   ```text
    [p]verifyset setkickonfail true
    ```

## Notes

- Ensure the bot has the necessary permissions to send DMs and manage roles in your server.
- If no verification role or questions are set, the bot will notify the user to contact the server administrators for configuration.
