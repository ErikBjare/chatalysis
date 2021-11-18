Chatalysis
==========

Analyse chat conversations to figure out:

 - Who you are writing with, how much, and when.
 - Who contributes the most to the conversation (and who's just creeping).
 - Which messages have the most reacts.
 - Which domains are most frequently linked.


## Usage

 1. Download the information you want to analyze here: https://www.facebook.com/dyi/
    - Note: Make sure to use JSON
    - Currently only supports: Messages
 2. Extract the zip contents into `./data/private`
 3. Install dependencies with `poetry install` or `pip install .`
 3. `chatalysis --help`

```
$ chatalysis --help
Usage: chatalysis [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  convos        List all conversations (groups and 1-1s)
  creeps        List creeping participants (who have minimal or no...
  daily         Your messaging stats, by date
  most-reacted  List the most reacted messages
  people        List all people
  top-writers   List the top writers
  yearly        Your messaging stats, by year
```
