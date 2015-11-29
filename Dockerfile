FROM python

ADD requirements.txt bot.py config.json /bot/

WORKDIR /bot

RUN pip install -r ./requirements.txt

ENV MONGO_HOST mongo
CMD ["python", "./bot.py"]
