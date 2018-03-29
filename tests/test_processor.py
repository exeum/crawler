from decimal import Decimal
import time
from datetime import datetime
from processor.processor import normalize
from processor.processor import process_gdax_book
from processor.processor import process_bitfinex_book


def test_normalize():
    assert normalize(42) == normalize(42.0)
    assert normalize(1992) == normalize('1992.00000000')
    assert normalize(1.3) == normalize('  0001.3000 ')


def e2s(epoch):
    return datetime.fromtimestamp(epoch).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def prepare_sample_gdax_book(snap_sz, mid_price, limit):
    assert(snap_sz <= mid_price)

    snapshot = {}
    base_ts = int(time.time())

    # snapshot
    snapshot['timestamp'] = float(base_ts) + float(0)
    snapshot['data'] = {}
    snapshot['data']['product'] = 'BTC-USD'
    snapshot['data']['type'] = 'snapshot'
    bids = []
    asks = []
    # snap_sz bids & snap_sz asks in snapshot
    for i in range(1, snap_sz + 1):
        bid_price = Decimal(mid_price - i)
        bid_amount = 1
        ask_price = Decimal(mid_price + i)
        ask_amount = 1
        bids.append([str(bid_price), str(bid_amount)])
        asks.append([str(ask_price), str(ask_amount)])
    snapshot['data']['bids'] = bids
    snapshot['data']['asks'] = asks

    # subscription
    subscription = {}
    subscription['timestamp'] = float(base_ts) + float(0)
    subscription['data'] = {}
    subscription['data']['type'] = 'subscriptions'
    channels = []
    channels.append({'name': 'level2', 'product_ids': ['BTC-USD']})
    subscription['data']['channels'] = channels

    # update
    updates = []

    # ts = base_ts + 1 => clear first `limit buys and `limit` sells from mid_price
    ts = base_ts + 1
    msec = 1
    buys_cnt = 0
    sells_cnt = 0
    for i in range(0, 2 * limit):
        update = {}
        update['timestamp'] = float(ts) + float(msec) / float(1000)
        update['data'] = {}
        update['data']['type'] = 'l2update'
        update['data']['product_id'] = 'BTC-USD'
        update['data']['time'] = e2s(update['timestamp'])
        if i % 2 == 0:
            buys = []
            buys_cnt += 1
            buys.append(['buy', str(Decimal(mid_price - buys_cnt)), '0'])
            update['data']['changes'] = buys
        else:
            sells = []
            sells_cnt += 1
            sells.append(['sell', str(Decimal(mid_price + sells_cnt)), '0'])
            update['data']['changes'] = sells
        msec += 1
        updates.append(update)

    # ts = base_ts + 2 => take the removed `limit` buys & `limit` sells back
    ts = base_ts + 2
    msec = 1
    buys_cnt = 0
    sells_cnt = 0
    for i in range(0, 2 * limit):
        update = {}
        update['timestamp'] = float(ts) + float(msec) / float(1000)
        update['data'] = {}
        update['data']['type'] = 'l2update'
        update['data']['product_id'] = 'BTC-USD'
        update['data']['time'] = e2s(update['timestamp'])
        if i % 2 == 0:
            buys = []
            buys.append(['buy', str(Decimal(mid_price - limit + buys_cnt)), '1'])
            update['data']['changes'] = buys
            buys_cnt += 1
        else:
            sells = []
            sells.append(['sell', str(Decimal(mid_price + limit - sells_cnt)), '1'])
            update['data']['changes'] = sells
            sells_cnt += 1
        msec += 1
        updates.append(update)

    # ts = base_ts + 3 => update amount of
    # `limit`-highest-price buys & `limit`-lowest-price sells
    ts = base_ts + 3
    msec = 1
    buys_cnt = 0
    sells_cnt = 0
    for i in range(0, 2 * limit):
        update = {}
        update['timestamp'] = float(ts) + float(msec) / float(1000)
        update['data'] = {}
        update['data']['type'] = 'l2update'
        update['data']['product_id'] = 'BTC-USD'
        update['data']['time'] = e2s(update['timestamp'])
        if i % 2 == 0:
            buys = []
            buys_cnt += 1
            buys.append(['buy', str(Decimal(mid_price - buys_cnt)), '2'])
            update['data']['changes'] = buys
        else:
            sells = []
            sells_cnt += 1
            sells.append(['sell', str(Decimal(mid_price + sells_cnt)), '2'])
            update['data']['changes'] = sells
        msec += 1
        updates.append(update)

    # ts = base_ts + 4 => update out-of-targeted range
    ts = base_ts + 4
    msec = 1
    buys_cnt = 0
    sells_cnt = 0
    for i in range(0, 2 * limit):
        update = {}
        update['timestamp'] = float(ts) + float(msec) / float(1000)
        update['data'] = {}
        update['data']['type'] = 'l2update'
        update['data']['product_id'] = 'BTC-USD'
        update['data']['time'] = e2s(update['timestamp'])
        if i % 2 == 0:
            buys = []
            buys_cnt += 1
            buys.append(['buy', str(Decimal(mid_price - limit - buys_cnt)), '3'])
            update['data']['changes'] = buys
        else:
            sells = []
            sells_cnt += 1
            sells.append(['sell', str(Decimal(mid_price + limit + sells_cnt)), '3'])
            update['data']['changes'] = sells
        msec += 1
        updates.append(update)

    return base_ts, [snapshot, subscription, *updates]


def test_process_gdax_book():
    # prepare sample data
    snap_sz = 5000
    mid_price = 10000
    limit = 10
    base_ts, lentries = prepare_sample_gdax_book(snap_sz, mid_price, limit)

    # run unit-tests
    entries = iter(lentries)
    for (ts, dbids, dasks) in process_gdax_book(entries):
        sbids = sorted(dbids.items(), key=lambda key_value: key_value[0], reverse=True)
        sasks = sorted(dasks.items(), key=lambda key_value: key_value[0], reverse=False)
        bids = sorted(sbids, reverse=True)[:limit]
        asks = sorted(sasks, reverse=False)[:limit]
        assert(len(bids) == limit)
        assert(len(asks) == limit)

        if (ts == base_ts + 1):
            for i in range(0, limit):
                assert(bids[i][0] == mid_price - (i + 1))
                assert(bids[i][1] == '1')
                assert(asks[i][0] == mid_price + (1 + i))
                assert(asks[i][1] == '1')
        elif (ts == base_ts + 2):
            for i in range(0, limit):
                assert(bids[i][0] == (mid_price - limit) - (i + 1))
                assert(bids[i][1] == '1')
                assert(asks[i][0] == (mid_price + limit) + (i + 1))
                assert(asks[i][1] == '1')
        elif (ts == base_ts + 3):
            for i in range(0, limit):
                assert(bids[i][0] == mid_price - (i + 1))
                assert(bids[i][1] == '1')
                assert(asks[i][0] == mid_price + (1 + i))
                assert(asks[i][1] == '1')
        elif (ts == base_ts + 4):
            for i in range(0, limit):
                assert(bids[i][0] == mid_price - (i + 1))
                assert(bids[i][1] == '2')
                assert(asks[i][0] == mid_price + (1 + i))
                assert(asks[i][1] == '2')


def prepare_sample_bitfinex_book(snap_sz, mid_price, limit):
    assert(snap_sz <= mid_price)

    base_ts = int(time.time())

    # event info
    evt_info = {}
    evt_info['timestamp'] = float(base_ts) + float(0)
    evt_info['data'] = {}
    evt_info['data']['event'] = 'info'
    evt_info['data']['version'] = 1.1
    evt_info['data']['platform'] = {'status': 1}

    # event subscribed
    evt_subscribed = {}
    evt_subscribed['timestamp'] = float(base_ts) + float(0)
    evt_subscribed['data'] = {}
    evt_subscribed['data']['event'] = 'subscribed'
    evt_subscribed['data']['channel'] = 'book'
    evt_subscribed['data']['channelId'] = 24907
    evt_subscribed['data']['prec'] = 'P0'
    evt_subscribed['data']['freq'] = 'F0'
    evt_subscribed['data']['len'] = '25'
    evt_subscribed['data']['pair'] = 'BTCUSD'

    # snapshot
    snapshot = {}
    snapshot['timestamp'] = float(base_ts) + float(0)
    snapshot['data'] = []
    snapshot['data'].append(24907)
    orders = []
    bids = []
    asks = []
    # snap_sz bids & snap_sz asks in snapshot
    for i in range(1, snap_sz + 1):
        count = 1
        bid_price = mid_price - i
        bid_amount = 1
        ask_price = mid_price + i
        ask_amount = -1
        bids.append([bid_price, count, bid_amount])
        asks.append([ask_price, count, ask_amount])
    orders = bids
    orders.extend(asks)
    snapshot['data'].append(orders)

    # update
    updates = []

    # ts = base_ts + 1 => clear first `limit buys and `limit` sells from mid_price
    ts = base_ts + 1
    msec = 1
    buys_cnt = 0
    sells_cnt = 0
    for i in range(0, 2 * limit):
        update = {}
        update['timestamp'] = float(ts) + float(msec) / float(1000)
        if i % 2 == 0:
            buys_cnt += 1
            update['data'] = [24907, mid_price - buys_cnt, 0, 1]
        else:
            sells_cnt += 1
            update['data'] = [24907, mid_price + sells_cnt, 0, -1]
        msec += 1
        updates.append(update)

    # ts = base_ts + 2 => take the removed `limit` buys & `limit` sells back
    ts = base_ts + 2
    msec = 1
    buys_cnt = 0
    sells_cnt = 0
    for i in range(0, 2 * limit):
        update = {}
        update['timestamp'] = float(ts) + float(msec) / float(1000)
        if i % 2 == 0:
            update['data'] = [24907, mid_price - limit + buys_cnt, 1, 1]
            buys_cnt += 1
        else:
            update['data'] = [24907, mid_price + limit - sells_cnt, 1, -1]
            sells_cnt += 1
        msec += 1
        updates.append(update)

    # ts = base_ts + 3 => update amount of
    # `limit`-highest-price buys & `limit`-lowest-price sells
    ts = base_ts + 3
    msec = 1
    buys_cnt = 0
    sells_cnt = 0
    for i in range(0, 2 * limit):
        update = {}
        update['timestamp'] = float(ts) + float(msec) / float(1000)
        if i % 2 == 0:
            buys_cnt += 1
            update['data'] = [24907, mid_price - buys_cnt, 1, 2]
        else:
            sells_cnt += 1
            update['data'] = [24907, mid_price + sells_cnt, 1, -2]
        msec += 1
        updates.append(update)

    # ts = base_ts + 4 => update out-of-targeted range
    ts = base_ts + 4
    msec = 1
    buys_cnt = 0
    sells_cnt = 0
    for i in range(0, 2 * limit):
        update = {}
        update['timestamp'] = float(ts) + float(msec) / float(1000)
        if i % 2 == 0:
            buys_cnt += 1
            update['data'] = [24907, mid_price - limit - buys_cnt, 1, 3]
        else:
            sells_cnt += 1
            update['data'] = [24907, mid_price + limit + sells_cnt, 1, -3]
        msec += 1
        updates.append(update)

    return base_ts, [evt_info, evt_subscribed, snapshot, *updates]


def test_process_bitfinex_book():
    # prepare sample data
    snap_sz = 5000
    mid_price = 10000
    limit = 10
    base_ts, lentries = prepare_sample_bitfinex_book(snap_sz, mid_price, limit)

    # run unit-tests
    entries = iter(lentries)
    for (ts, dbids, dasks) in process_bitfinex_book(entries):
        sbids = sorted(dbids.items(), key=lambda key_value: key_value[0], reverse=True)
        sasks = sorted(dasks.items(), key=lambda key_value: key_value[0], reverse=False)
        bids = sorted(sbids, reverse=True)[:limit]
        asks = sorted(sasks, reverse=False)[:limit]
        assert(len(bids) == limit)
        assert(len(asks) == limit)

        if (ts == base_ts + 1):
            for i in range(0, limit):
                assert(bids[i][0] == mid_price - (i + 1))
                assert(bids[i][1] == '1')
                assert(asks[i][0] == mid_price + (1 + i))
                assert(asks[i][1] == '-1')
        elif (ts == base_ts + 2):
            for i in range(0, limit):
                assert(bids[i][0] == (mid_price - limit) - (i + 1))
                assert(bids[i][1] == '1')
                assert(asks[i][0] == (mid_price + limit) + (i + 1))
                assert(asks[i][1] == '-1')
        elif (ts == base_ts + 3):
            for i in range(0, limit):
                assert(bids[i][0] == mid_price - (i + 1))
                assert(bids[i][1] == '1')
                assert(asks[i][0] == mid_price + (1 + i))
                assert(asks[i][1] == '-1')
        elif (ts == base_ts + 4):
            for i in range(0, limit):
                assert(bids[i][0] == mid_price - (i + 1))
                assert(bids[i][1] == '2')
                assert(asks[i][0] == mid_price + (1 + i))
                assert(asks[i][1] == '-2')
