# QuoteOfTheDay Cog

The QuoteOfTheDay cog for RedBot posts a random quote to a specified channel at a specified time each day. It ensures no quote is repeated until all quotes have been used. Admins can manage quotes, set the channel and time, and enable or disable the posting feature.

## Features

- **Add Quotes:** Add individual quotes or bulk add multiple quotes.
- **Remove Quotes:** Remove specific quotes.
- **Set Channel:** Define the channel where the quotes will be posted.
- **Set Time:** Set the time (in 24-hour format) for posting quotes.
- **Enable/Disable:** Enable or disable the daily quote posting.

## Installation

```text
[p]cog install reediculous456 quote_otd
[p]load quote_otd
```

## Commands

### Admin Commands

- `[p]quote add <quote>`: Add a quote to the list.
- `[p]quote remove <quote>`: Remove a quote from the list.
- `[p]quote bulkadd <quote1 | quote2 | quote3 | ...>`: Bulk add multiple quotes.
- `[p]quote setchannel <#channel>`: Set the channel where quotes will be posted.
- `[p]quote settime <hour> <minute>`: Set the time for posting quotes.
- `[p]quote enabled <true|false>`: Enable or disable the daily quote posting.

## Usage

### Add a Quote

```text
[p]quote add <quote>
```

Example:

```text
[p]quote add The only limit to our realization of tomorrow is our doubts of today.
```

### Remove a Quote

```text
[p]quote remove <quote>
```

Example:

```text
[p]quote remove The only limit to our realization of tomorrow is our doubts of today.
```

### Bulk Add Quotes

```text
[p]quote bulkadd <quote1 | quote2 | quote3 | ...>
```

Example:

```text
[p]quote bulkadd The best time to plant a tree was 20 years ago. The second best time is now. | It does not matter how slowly you go as long as you do not stop.
```

### Set the Channel

```text
[p]quote setchannel <#channel>
```

Example:

```text
[p]quote setchannel #general
```

### Set the Time

```text
[p]quote settime <hour> <minute>
```

Example:

```text
[p]quote settime 9 0
```

This sets the posting time to 9:00 AM UTC.

### Enable/Disable Posting

```text
[p]quote enabled <true|false>
```

Example:

```text
[p]quote enabled true
```
