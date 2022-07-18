Chatalysis
==========

[![Build Status GitHub](https://github.com/ErikBjare/chatalysis/workflows/Build/badge.svg?branch=master)](https://github.com/ErikBjare/chatalysis/actions?query=branch%3Amaster)
[![codecov](https://codecov.io/gh/ErikBjare/chatalysis/branch/master/graph/badge.svg?token=mG3sqsPL6Z)](https://codecov.io/gh/ErikBjare/chatalysis)

Analyse chat conversations to figure out:

 - Who you are writing with, how much, and when.
 - Who contributes the most to the conversation (and who's just creeping).
 - Which messages have the most reacts.
 - Search all past messages by author or content.


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
  messages      List messages, filter by user or content.
  most-reacted  List the most reacted messages
  people        List all people
  top-writers   List the top writers
  yearly        Your messaging stats, by year
```


## TODO 

 - Support more datasources
 - Analyze which domains are most frequently linked.
 - Sentiment analysis
 - Try making metrics to analyze popularity/message/"alpha"/"signal" quality (average positive reacts per message?)
