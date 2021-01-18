from bittrex_arbitrage_client import BittrexArbitrageClient
from bithumb_arbitrage_client import BithumbArbitrageClient
from arbitrage_finder import ArbitrageFinder
from utils import Trade, TradeStage
import datetime
import time
from math import *
import sys
import json
import os

def load_keys(path):
    with open(path) as key_file:
        keys = key_file.readlines()

    keys = [key.strip() for key in keys]
    
    return keys

def monitor_arbitrage(key_folder_path):
    #load API keys
    bittrex_keys = load_keys(key_folder_path+'/bittrex_keys.txt')
    bithumb_keys = load_keys(key_folder_path+'/bithumb_keys.txt')

    #contants
    ARBITRAGE_OPPORTUNITY_WAIT_MIN = 60*24 #search for arbitrage oppertunities for a day at most
    PROFIT_THRESHOLD = .012
    PRINT_TOP_TRADES = True
    LOOPS = 20

    print("Setting Up Exchanges")
    #exchange constants
    DEBUG = True


    #instanciate exchanges
    bittrexName = 'bittrex'
    bittrexBaseCurrencies = ['BTC'] #ETH and XMR are also base currencies but we'll experiment with this later
    bittrexTradableCurrencies = ['BTC','ETH','ETC','LTC','DASH'] #XRP has a minimum amt which an address can hold (this may cause issues... avoid for now)
    bittrexMinFunds = 50 # 50 USD
    isStartingExchange = True
    bittrexArbitrageClient = BittrexArbitrageClient(bittrex_keys[0], 
        bittrex_keys[1], 
        bittrexName, 
        bittrexBaseCurrencies, 
        bittrexTradableCurrencies, 
        bittrexMinFunds,
        isStartingExchange, 
        DEBUG)

    bithumbName = 'bithumb'
    bithumbBaseCurrencies = ['KRW']
    bithumbTradableCurrencies = ['BTC','ETH','ETC','LTC','DASH']
    isStartingExchange = False
    bithumbMinFunds = 50000 #approximately 50 USD of KRW
    bithumbArbitrageClient = BithumbArbitrageClient(bithumb_keys[0],
        bithumb_keys[1],
        bithumbName,
        bithumbBaseCurrencies,
        bithumbTradableCurrencies,
        bithumbMinFunds,
        isStartingExchange,
        DEBUG)

    #instanciate an arbitrage finder
    arbFinder = ArbitrageFinder()

    curTrade = Trade([]) 
    for loop in range(LOOPS):
        print("Loop: "+str(loop))
        arbFinder.find_arbitrage_bittrex_bithum(bittrexArbitrageClient, bithumbArbitrageClient, ARBITRAGE_OPPORTUNITY_WAIT_MIN, PROFIT_THRESHOLD, curTrade, PRINT_TOP_TRADES)





if __name__ == '__main__':
    monitor_arbitrage(sys.argv[1])