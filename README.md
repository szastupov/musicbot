Music Catalog Bot
=================

This Telegram bot maintains a user generated catalog of music.

How does it work? You simply send audio file (from Telegram Desktop, Web or OSX) to the bot and it's added to the public catalog. All tracks are indexed and available for everyone from any Telegram client.

Go ahead and [try it](https://telegram.me/MusicCatalogBot)!


**UPDATE**: The bot is blocked on iOS due to Apple complaints, but you still can build your own from source or a docker image and use it privatly.


![Screenshot](http://i.imgur.com/vRNxnDS.png)
![Screenshot](http://i.imgur.com/qmvht6v.png)

### Technical side

The bot doesn't store any media, instead it only keeps track metadata, while the files are hosted on Telegram servers.

It's written in Python 3, powered by [aiotg](https://github.com/szastupov/aiotg) framework and uses [MongoDB](https://www.mongodb.com) for index.

You can easily run your own instance with [docker-compose](1):
```yml
musicbot:
  image: szastupov/musicbot
  restart: always
  links:
    - mongo
  environment:
    - BOT_NAME=MusicCatalogBot
    - API_TOKEN=Telegram API token
    - BOTAN_TOKEN=Optional botan token
    - MONGO_HOST=mongo
mongo:
  image: mongo
  restart: always
```

Or directly with docker:
```
$ docker pull szastupov/musicbot
$ docker run -e "API_TOKEN=YOUR_TOKEN" \
             -e "BOT_NAME=BotPlaygroundBot" \
             -e "MONGO_HOST=mongo" \
             --link mongo:mongo \
             szastupov/musicbot
```

Or you can run it manually, the requirements are specified in requirements.txt, you know the rest.

[1]: https://docs.docker.com/compose/
