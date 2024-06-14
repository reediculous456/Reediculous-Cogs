# QuoteOfTheDay Cog

The QuoteOfTheDay cog for RedBot posts a random quote to a specified channel at a specified time each day. It ensures no quote is repeated until all quotes have been used. Admins can manage quotes, set the channel and time, and enable or disable the posting feature.

## Features

- **Add Quotes:** Add individual quotes or bulk add multiple quotes.
- **Remove Quotes:** Remove specific quotes.
- **Set Channel:** Define the channel where the quotes will be posted.
- **Set Time:** Set the time (in 24-hour format) for posting quotes.
- **Enable/Disable:** Enable or disable the daily quote posting.
- - **List Quotes:** List quotes in paginated format in groups of 15.

## Installation

```text
[p]cog install reediculous456 quote_otd
[p]load quote_otd
```

## Commands

### Admin Commands

- `[p]quoteotd list [page]`: List quotes in pages of 15 quotes.
- `[p]quoteotd add <quote>`: Add a quote to the list.
- `[p]quoteotd remove <quote>`: Remove a quote from the list.
- `[p]quoteotd bulkadd <quote1 | quote2 | quote3 | ...>`: Bulk add multiple quotes.
- `[p]quoteotd setchannel <#channel>`: Set the channel where quotes will be posted.
- `[p]quoteotd settime <hour> <minute>`: Set the time for posting quotes.
- `[p]quoteotd enabled <true|false>`: Enable or disable the daily quote posting.

## Usage

### List Quotes

```text
[p]quote list [page]
```

Example:

```text
[p]quote list 1
```

Lists the first 15 quotes. Use the page parameter to view subsequent pages.

### Add a Quote

```text
[p]quoteotd add <quote>
```

Example:

```text
[p]quoteotd add The only limit to our realization of tomorrow is our doubts of today.
```

### Remove a Quote

```text
[p]quoteotd remove <quote>
```

Example:

```text
[p]quoteotd remove The only limit to our realization of tomorrow is our doubts of today.
```

### Bulk Add Quotes

```text
[p]quoteotd bulkadd <quote1 | quote2 | quote3 | ...>
```

Example:

```text
[p]quoteotd bulkadd The best time to plant a tree was 20 years ago. The second best time is now. | It does not matter how slowly you go as long as you do not stop.
```

### Set the Channel

```text
[p]quoteotd setchannel <#channel>
```

Example:

```text
[p]quoteotd setchannel #general
```

### Set the Time

```text
[p]quoteotd settime <hour> <minute>
```

Example:

```text
[p]quoteotd settime 9 0
```

This sets the posting time to 9:00 AM UTC.

### Enable/Disable Posting

```text
[p]quoteotd enabled <true|false>
```

Example:

```text
[p]quoteotd enabled true
```
