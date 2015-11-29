Music Catalog Bot
=================

This Telegram bot maintains a user generated catalog of music.

How does it work? You simply send an audio file (from Telegram Desktop, Web or OSX) to the bot and it's added to the public catalog. All tracks are indexed and available for everyone from any Telegram client.

Go ahead and [try it](https://telegram.me/MusicCatalogBot)!

### Technical side

The bot doesn't store any media, instead it only stores track metadata, while files are hosted on Telegram servers.

The bot is written in Python 3, powered by [aiotg](https://github.com/szastupov/aiotg) framework and uses [MongoDB](https://www.mongodb.com) for index.

You can easily run your own instance with docker:
```
$ cp config.json.example config.json
$ vi config.json # set your API token in config.json
$ docker-compose build
$ docker-compose up -d # We are up and running!
```

You can also do it without Docker, the requirements are specified in requirements.txt, you know the rest.
