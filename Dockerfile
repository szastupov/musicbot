FROM python

ADD requirements.txt /bot/
WORKDIR /bot
RUN pip install -r ./requirements.txt

ADD bot.py /bot/

CMD ["python", "./bot.py"]
