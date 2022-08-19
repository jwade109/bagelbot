## August 19th, 2022

- Added bb simpsons, the latest in a growing family of sound effect
  libraries. Not too many sound effects available, yet.

  ```
  bb simpsons snrub
  bb sim money
  bb sim ?
  ```

## August 13th, 2022

- Added bb bedtime, which tells you to go to bed, and then kicks everyone
  from the voice channel. Requires Bagelbot to be granted the
  "Move Members" permission
- Limited deployment of [Sentence Enhancers](https://www.youtube.com/watch?v=-tyk3CiBL2g)
  for reducing the staleness of BagelBot's vernacular

## August 9th, 2022

- Rebalanced audio levels to make playing music/sound effects less loud
- Fixed a bug where BagelBot wouldn't join a voice channel to play an
  enqueued song if not already in a voice channel

## August 7th, 2022

- Added documentation for the Reminders module
- Added a feature where you can use ? to ask a sound effect command
  what effects exist. Such commands are:

  ```
  bb starwars ?
  bb wii ?
  bb rocket-league ?
  bb mulaney ?
  bb mechanicus ?
  bb undertale ?
  ```

## August 6th, 2022

- Added Warhammer 40k Mechanicus OST (bb mechanicus)
- Released the Othello module, which allows users to challenge each other
  (or BagelBot!) to a game of Othello

## August 5th, 2022

- Fixed issue where the audio worker loop was polling for user IDs
  unnecessarily, causing Discord to throttle the bot. This caused
  the worker to pause for around 15 seconds at a time. Playing audio
  should be much quicker now.

## July 22nd, 2022

- Restricted bb error to only be invokable by Wade Foster, so Chandler
  can't spam me with error alerts. (Yes, I get a text message every time
  BagelBot says "oof, ouch, my bones".)

## July 17th, 2022

- Extended features for the Define module. Users can now look up words
  and phrases using Wikipedia, Wiktionary, and Urban Dictionary via
  the following commands:

  ```
  bb define "thing to define" (uses all three sources)
  bb wikipedia ...
  bb wiktionary ...
  bb urbandict ...
  ```

## October 6th, 2021

- BagelBot will now, on rare occasion, parrot a single word from a user's
  (publicly available -- not in DMs!) message back to them with a capital B
  either appended to or written over the first letter of the word.

  For example:

  User: Dang, I'm really depressed that my cat died.

  BagelBot: Bepressed.

## April 24th, 2021

- First bird sighting

## April 6th, 2021

- BagelBot was born