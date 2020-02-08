import sys
sys.path.insert(0, './helper')
from api_methods import get_tickers
from init_producers import init_producers
from schemas import Features

import pulsar
from pulsar.schema import *

import time
import schedule
from pyhive import presto
import asyncio

from threading import Thread, Lock

producer_dictionary, final_tickers = {}, []

#feature_set = ['ma_1', 'ma_10', 'ma_60', 'ma_120', 'std_1', 'std_10', 'std_60', 'std_120', 'vol_1', 'vol_10', 'vol_60', 'vol_120']
#feature_set = ['ma_1', 'ma_5', 'std_1', 'std_5', 'vol_1', 'vol_5']
feature_set = ['avg_1', 'avg_5', 'stddev_1', 'stddev_5']

def get_all_queries():

    queries = []
    #seconds = time.time()
    miliseconds = 1581094483536

    for feature in feature_set:
        action, num_minutes = feature.split("_")
        num_minutes = int(num_minutes)
        #boundary = (seconds - (60*num_minutes))*1000
        boundary = (miliseconds - (60*num_minutes)*1000)
        query = 'SELECT ' + action + '(price) as ' + feature + ', symbol FROM pulsar."public/default".all_stocks WHERE time > ' + str(boundary) + ' GROUP BY symbol'
        queries.append({"query":query, "feature":feature})

    return queries

class QueryWorker(Thread):
    __lock = Lock()

    def __init__(self, query, feature, result_queue):
        Thread.__init__(self)
        self.query = query
        self.feature = feature
        self.result_queue = result_queue

    def run(self):

        result = None
        print("Connecting to database...")

        try:
            cursor = presto.connect('10.0.0.10', port=8081, username="djh").cursor()
            cursor.execute(self.query)
            result = cursor.fetchall()
        except Exception as e:
            print("Unable to access database %s" % str(e))

        self.result_queue.append({"array":result, "feature":self.feature})

def run_all_queries():

    delay = 1
    result_queue = []

    workers = []
    queries = get_all_queries()

    for query_dict in queries:
        worker = QueryWorker(query_dict['query'], query_dict['feature'], result_queue)
        workers.append(worker)

    for worker in workers:
        worker.start()

    # Wait for the job to be done
    while len(result_queue) < len(feature_set):
        time.sleep(delay)

    job_done = True

    for worker in workers:
        worker.join()

    make_features(result_queue)

def make_features(queue):

    feature_dictionary = {}

    for feature, symbol in queue[0]['array']:
        feature_dictionary[symbol] = {'symbol': symbol}

    #for ticker in final_tickers:
    #    feature_dictionary[ticker] = {}

    for result in queue:

        for feature, symbol in result['array']:
            try:
                feature_dictionary[symbol][result['feature']] = str(feature)
            except:
                print("key error")

    for symbol in feature_dictionary:
        #print(feature_dictionary[symbol])
        feature_object = make_feature_object(feature_dictionary[symbol])
        print(feature_object)
        #producer_dictionary[symbol].send(feature_object)
        #producer_dictionary["all_features"].send(feature_object)

def make_feature_object(dict):

    symbol, avg_1, avg_5, stddev_1, stddev_5 = dict.get('symbol', -1), dict.get('avg_1', 0), dict.get('avg_5', 0), dict.get('stddev_1', 0), dict.get('stddev_5', 0)
    feature_object = Features(symbol = symbol, avg_1 = avg_1, avg_5 = avg_5, stddev_1 = stddev_1, stddev_5 = stddev_5)
    return feature_object

#producer_dictionary, final_tickers = init_producers(get_tickers(), features = True)
run_all_queries()

#schedule.every(30).seconds.do(run_all_queries)

#while True:
#    schedule.run_pending()
