# antelope

[![Build Status](https://travis-ci.org/exeum/antelope.svg?branch=master)](https://travis-ci.org/exeum/antelope)

Antelope is a fast, scaleable and fault-tolerant system for collecting, processing and storing market data from multiple cryptocurrency exchanges. It aims to be as simple as possible.

## Data storage

Order book archives are stored in S3 as `orderbook-<exchange>-<symbol>-<yyyymmdd>-<uuid>.gz`.
