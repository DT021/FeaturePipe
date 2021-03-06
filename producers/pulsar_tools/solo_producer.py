import sys
sys.path.insert(0, './api_methods')
from api_methods import get_tickers

import json
import requests
import pulsar
from websocket import create_connection
from pulsar.schema import *

API_KEY = "6deAryjhAoa53eNJ5hMZSQb8BOKp64kpuHmYfa"

class Stock(Record):
    symbol = String()
    exchange_id = Integer()
    trade_id = Integer()
    price = Float()
    size = Integer()
    tape = Integer()
    time = Long()
    #conditions = List()

client = pulsar.Client('pulsar://10.0.0.7:6650,10.0.0.8:6650,10.0.0.9:6650')
producer = client.create_producer('msft_test', schema=AvroSchema(Stock))

def produce():

    ws = create_connection("wss://socket.polygon.io/stocks")
    response = ws.recv()

    auth = {"action":"auth","params":API_KEY}
    auth_json = json.dumps(auth)
    ws.send(auth_json)
    response = ws.recv()

    subscribe = {"action":"subscribe","params":"T.*"}
    subscribe_json = json.dumps(subscribe)
    ws.send(subscribe_json)
    response = ws.recv()

    while True:
        result = ws.recv()
        send_message(result)

def make_stock(result_json):

    symbol, exchange_id, trade_id, price, tape, size, time = result_json.get('sym', -1), result_json.get('x', -1), result_json.get('i', -1), result_json.get('p', -1), result_json.get('x', -1), result_json.get('s', -1), result_json.get('t', -1)
    vars = [symbol, exchange_id, trade_id, price, tape, size, time]

    if -1 in vars:
        return Stock(symbol = "bad_data", exchange_id = 1, trade_id = 1, price = 1.0, tape = 1, size = 1, time = 1000000000)

    return Stock(symbol = symbol, exchange_id = exchange_id, trade_id = trade_id, price = price, tape = tape, size = size, time = time)

def send_message(result):

    json_result = json.loads(result)

    if len(result) > 1:

        final = json_result[0]

        if final.get('ev', 0) == 'T':

            stock = make_stock(final)
            producer.send(stock)

produce()
