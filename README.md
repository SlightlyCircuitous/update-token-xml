# update-token-xml

## About

Command line tool to compare a new set of tokens from Scryfall with an existing Cockatrice token XML. 

Pulls down a token set from Scryfall, appends reprinted tokens to a copy of the current XML file, and creates entries for new tokens in a separate XML file. Pulls the current large Scryfall hard link for picURLs.

## Use and Caveats

Run using `python filename setcode /path/to/current/XML/file` or make the file executable with chmod and use `./filename setcode /path/to/current/XML/file`, while in the same folder as this script file.

Does not handle:
- Filling out related or reverse-related fields
- Adding spaces to non-uniquely named tokens
- Adding "(Token)" to token copies of cards

Treats tokens with new reminder text as new tokens.
