Chatalysis
==========

Analyse chat conversations to figure out:

 - Who you are writing with, how much, and when.
 - Who contributes the most to the conversation.
 - Which domains are most frequently linked.


Intended to support:

 - Export conversations
   - Compute how many messages and the total number of how many days one has been *in contact* with **each contact**.
 - Export location data
   - Convert to bucket/event format supported by ActivityWatch/Zenobase.

## Usage

 1. Download the information you want to analyze here: https://www.facebook.com/your_information/
    - Currently only supports: Messages
 2. Extract the zip contents into `./data/private`
 3. `python3 main.py`
