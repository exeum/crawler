#!/usr/bin/env python3

import argparse
import json
import logging
import ssl
import time
import uuid

import influxdb
import requests
import websocket
from tenacity import retry, stop_after_attempt, TryAgain

TIMEOUT = 30
RETRIES = 5


def process(data, db, kind, exchange, base, quote, scraper_id):
    size = len(data)
    logging.info(data)
    db.write_points([{
        'measurement': 'scraper',
        'tags': {
            'kind': kind,
            'exchange': exchange,
            'base': base,
            'quote': quote,
            'scraper_id': scraper_id
        },
        'time': int(time.time()) * 1000000000,
        'fields': {
            'size': size,
        }
    }])
    line = json.dumps({
        'timestamp': time.time(),
        'data': json.loads(data)
    }, separators=(',', ':'))
    date = time.strftime('%Y%m%d')
    filename = f'/data/{exchange}-{kind}-{base}-{quote}-{date}-{scraper_id}'
    with open(filename, 'at') as f:
        f.write(line + '\n')


@retry(stop=stop_after_attempt(RETRIES))
def http_get(url):
    logging.info(f'getting {url}')
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


@retry(stop=stop_after_attempt(RETRIES))
def websocket_recv(ws):
    data = ws.recv()
    if data:
        return data
    logging.warning('empty response')
    raise TryAgain


@retry(stop=stop_after_attempt(RETRIES))
def websocket_read(url, subscribe, snapshot):
    if snapshot:
        yield http_get(snapshot)
    logging.info(f'connecting to {url}')
    ws = websocket.create_connection(url, timeout=TIMEOUT, sslopt={'cert_reqs': ssl.CERT_NONE})
    if subscribe:
        logging.info(f'sending {subscribe}')
        ws.send(subscribe)
    logging.info('receiving data')
    while True:
        yield websocket_recv(ws)


def scrape(url, subscribe, snapshot, db, kind, exchange, base, quote):
    scraper_id = uuid.uuid4().hex
    logging.info(f'scraping {exchange} {base}/{quote} {kind} ({scraper_id})')
    for data in websocket_read(url, subscribe, snapshot):
        process(data, db, kind, exchange, base, quote, scraper_id)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('exchange')
    parser.add_argument('kind', choices=('book', 'trades'))
    parser.add_argument('base')
    parser.add_argument('quote')
    parser.add_argument('url')
    parser.add_argument('--subscribe')
    parser.add_argument('--snapshot')
    parser.add_argument('--influxdb')
    parser.add_argument('--database', default='antelope')
    return parser.parse_args()


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    db = influxdb.InfluxDBClient(host=args.influxdb, database=args.database, timeout=TIMEOUT)
    scrape(args.url, args.subscribe, args.snapshot, db, args.kind, args.exchange, args.base, args.quote)


if __name__ == '__main__':
    main()
