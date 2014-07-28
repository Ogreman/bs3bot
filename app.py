from __future__ import print_function

from datetime import datetime, timedelta
from twittcher import SearchWatcher
from celery import Celery
from celery.task import periodic_task

import tweepy
import os
import operator
import re

CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
ACCESS_KEY  = os.environ['ACCESS_KEY']
ACCESS_SECRET = os.environ['ACCESS_SECRET']


auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth)


REDIS_URL = os.environ.get('REDISTOGO_URL', 'redis://localhost')
celery = Celery(__name__, broker=REDIS_URL)

REMOVE_LIST = ["-", "a", "an", "as", "at", "before", "but", "by", "for","from","is", "in", "into", "like", "of", "off", "on", "onto","per","since", "than", "the", "this", "that", "to", "up", "via","with"]


class TopTweetWatcher(SearchWatcher):

    def __init__(self, search_term, action=print, database=None):
        SearchWatcher.__init__(self, search_term, action, database)
        self.lex = {}

    def calculate_most_used(self):
        for tweet in self.seen_tweets:
            for word in tweet.text.split():
                word = word.lower()
                if word.startswith('#'):
                    word = word[1:]
                elif word.startswith('@'):
                    continue
                elif re.match('^[\w-]+$', word) is None:
                    continue
                elif word in REMOVE_LIST:
                    continue
                if word in self.lex:
                    self.lex[word] += 1
                else:
                    self.lex[word] = 1

    def get_most_popular(self, num=1):
        if not self.lex:
            self.calculate_most_used()
        return list(
            item for item, _ in sorted(
                self.lex.iteritems(),
                key=operator.itemgetter(1),
                reverse=True
            )
        )[:num]


bot = TopTweetWatcher("bristol")


@periodic_task(run_every=timedelta(minutes=1))
def check_tweets():
    bot.watch()


@periodic_task(run_every=timedelta(minutes=2))
def check_top():
    bot.calculate_most_used()


@periodic_task(run_every=timedelta(minutes=3))
def tweet_top():
    for words in range(14, 3, -1):
        status_text = ' '.join(bot.get_most_popular(words))
        if (
            status_text
        ) and (
            len(status_text) <= 140
        ) and (
            status_text not in bot.seen_tweets
        ):
            api.update_status(status=status_text)
            bot.seen_tweets += [status_text]
            break

