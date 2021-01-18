from bittrex_arbitrage_client import BittrexArbitrageClient
from bithumb_arbitrage_client import BithumbArbitrageClient
from utils import Trade, TradeStage
import datetime
import time
from math import *
import sys
import json
import os

def save_trade(sessionName, arbitrageCycle, trade):
    with open(sessionName+'/'+'trade'+str(arbitrageCycle)+'.json', 'w') as fp:
        json.dump(trade.to_dictionary(), fp)


def load_keys(path):
    with open(path) as key_file:
        keys = key_file.readlines()

    keys = [key.strip() for key in keys]
    
    return keys

def reset_trade(bittrex, bithumb):
    try:
        #check funds on bithumb
        currencySym = bithumb.check_for_deposits(1.0/6.0)

        #get bittrex DASH address
        bittrexDASHAddr = bittrex.get_wallets(['DASH'])['DASH']

        #Send funds if already in DASH.
        if(currencySym == 'DASH'):
            response = bithumb.transfer_all('DASH', bittrexDASHAddr)
            print(response)
        #Buy DASH and send funds if funds are in KRW.
        elif(currencySym == 'KRW'):
            buy(bithumb, 'DASH', 'KRW', 10)
            bithumb.transfer_all('DASH', bittrexDASHAddr)
        #Sell whatever coin is in bithumb for KRW, buy DASH with KRW and send funds.
        else:
            sell(bithumb, currencySym, 'KRW', 10)
            buy(bithumb, 'DASH', 'KRW', 10)
            bithumb.transfer_all('DASH', bittrexDASHAddr)

        #wait for DASH to arrive at bittrex
        print('Wait for funds to arrive at Bittrex.')
        originalBalance = bittrex.get_current_balance('DASH')
        waitMinutes = 60
        checkFreq = 5

        waitSeconds = waitMinutes*60
        waitLoops = int(waitSeconds/checkFreq)
        for i in range(waitLoops):
            curBalance = bittrex.get_current_balance('DASH')
            if(curBalance != originalBalance):
                break
            print('.')
            time.sleep(checkFreq)


        #sell DASH for BTC once it arrives
        sell(bittrex, 'DASH', 'BTC', 1)

    except NameError, e:
        print(e)

        #check funds on bittrex
        currencySym = bittrex.check_for_deposits(1.0/6.0)
        if(currencySym != 'BTC'):
            sell(bittrex, currencySym, 'BTC', 1)

def send_funds(exchangeA, exchangeB, curTrade , A2B):
    if(A2B):
        startExchange = exchangeA
        endExchange = exchangeB
    else:
        startExchange = exchangeB
        endExchange = exchangeA

    #get currency to trade
    currency = curTrade.get_most_recent_stage().get_non_base_coin()
    walletAddr = endExchange.get_wallets([currency])
    startExchange.transfer_all(currency, walletAddr[currency])

#hardcode the cases for bittrex and bithumb for now...
def find_arbitrage_bittrex_bithum(bittrex, bithumb, waitMinutes, profitThreshold, curTrade, printTrades):
    print("Searching for arbitrage oppertunities.")
    checkFreq = 5
    numLoops = int((waitMinutes*60.0)/checkFreq)

    for loopNum in range(numLoops):
        print('.')
        #get most recent prices
        bittrexRecentPricesAsk = bittrex.get_most_recent_prices('ask')
        bittrexRecentPricesBid = bittrex.get_most_recent_prices('bid')
        bithumbRecentPricesAsk = bithumb.get_most_recent_prices('close')
        bithumbRecentPricesBid = bithumb.get_most_recent_prices('close')

        #find all trades
        allValidTrades = []
        #buy coins on bittrex using 'bittrex_BC_START'
        for bittrex_BC_START in bittrex.baseCurrencies:
            #buy 'bittrex_TC' with 'bittrex_BC_START'
            for bittrex_TC in bittrex.tradableCurrencies:
                #sell 'bittrex_TC' on bithumb for 'bithumb_BC'
                for bithumb_BC in bithumb.baseCurrencies:
                    #buy 'bithumb_TC' with 'bithumb_BC'
                    for bithumb_TC in bithumb.tradableCurrencies:
                        #sell 'bithumb_TC' on bittrex for 'bittrex_BC_END'
                        for bittrex_BC_END in bittrex.baseCurrencies:

                            pairs = []
                            pairs.append(bittrex_BC_START+'_'+bittrex_TC)
                            pairs.append(bithumb_BC+'_'+bittrex_TC)
                            pairs.append(bithumb_BC+'_'+bithumb_TC)
                            pairs.append(bittrex_BC_END+'_'+bithumb_TC)

                            stages = []
                            stages.append(TradeStage('BUY', pairs[0], bittrexRecentPricesBid[pairs[0]]*1.0025))
                            stages.append(TradeStage('SELL', pairs[1], bithumbRecentPricesAsk[pairs[1]]*0.9985))     
                            stages.append(TradeStage('BUY',pairs[2], bithumbRecentPricesBid[pairs[2]]*1.0015))
                            stages.append(TradeStage('SELL', pairs[3], bittrexRecentPricesAsk[pairs[3]]*0.9975))
                            """
                            stages.append(TradeStage('BUY', pairs[0], bittrexRecentPricesBid[pairs[0]]))
                            stages.append(TradeStage('SELL', pairs[1], bithumbRecentPricesAsk[pairs[1]]))     
                            stages.append(TradeStage('BUY',pairs[2], bithumbRecentPricesBid[pairs[2]]))
                            stages.append(TradeStage('SELL', pairs[3], bittrexRecentPricesAsk[pairs[3]]))
                            """

                            #determin if trade is valid with respect to trade already in progress
                            validTrade = True
                            for stageNum in range(len(curTrade.stages)):
                                #check if trading pair names match
                                if(curTrade.stages[stageNum].tradingPair == pairs[stageNum]):
                                    #change price of trading stage to the locked price of the stage 
                                    stages[stageNum].price = curTrade.stages[stageNum].price
                                #invalidate trade if trading pair names  
                                else:
                                    validTrade = False
                                    break

                            if(validTrade):
                                allValidTrades.append(Trade(stages))

        #get profits of valid trades
        for trade in allValidTrades:
            trade.profit = (1.0/trade.stages[0].price)*trade.stages[1].price*(1.0/trade.stages[2].price)*trade.stages[3].price-1.0

        #sort valid least to most profitable
        sortedValidTrades = sorted(allValidTrades, key=lambda trade: trade.profit)

        #print trades
        if(printTrades):
            print('BEST TRADES')
            #for i in range(len(sortedValidTrades)):
            for i in range(8):
                print(str(sortedValidTrades[len(sortedValidTrades)-i-1]))
            print('\n')



        mostProfitableTrade = sortedValidTrades[len(sortedValidTrades)-1]

        if(mostProfitableTrade.profit > profitThreshold):
            print("Trade Found: "+str(mostProfitableTrade))
            indexOfNextStage = len(curTrade.stages)
            return mostProfitableTrade.stages[indexOfNextStage]

        
        time.sleep(checkFreq)

    #rais error if no arb oppertunities found
    raise NameError('No arbitrage oppertunities found in last: '+ str(waitMinutes)+' min')

def buy(exchange, currrencySymToBuy, currrencySymBuyingWith, ORDER_FILL_WAIT_MIN):
    #This branch is taken when an "arbitrage finder" suggests a new currency actually needs to be bought.
    if(currrencySymBuyingWith != currrencySymToBuy):
        #get original balances
        originalBaseCurrencyBalance = exchange.get_current_balance(currrencySymBuyingWith)
        originalNonBaseCurrencyBalance = exchange.get_current_balance(currrencySymToBuy)

        #get timestamp to track order
        timestamp = time.time()

        #place buy order
        orderNum = exchange.place_buy_max_order(currrencySymToBuy, currrencySymBuyingWith)

        #wait for order to sync with other api calls
        time.sleep(2)

        #wait for order to fill (code gets more complex if order doesn't fill)
        #Options: 
        #1) don't raise error if % of order is filled...
        #2) place market order
        #3) cancell open orders + look for arbitrage oppertunities again (results in several trades floating around)
        pair = currrencySymBuyingWith+'_'+currrencySymToBuy
        if(not(exchange.wait_for_order_fill(orderNum, 'bid', timestamp, pair, ORDER_FILL_WAIT_MIN))):
            raise NameError("Order didn't completely fill.")

        #correct price of nextTradeStage to accont for different rates order filled at
        finalBaseCurrencyBalance = exchange.get_current_balance(currrencySymBuyingWith)
        finalNonBaseCurrencyBalance = exchange.get_current_balance(currrencySymToBuy)
        effectivePrice = (originalBaseCurrencyBalance-finalBaseCurrencyBalance)/(finalNonBaseCurrencyBalance-originalNonBaseCurrencyBalance)
        print('Effective Price: '+str(effectivePrice))
        return effectivePrice
    
    #This branch is taken when an "arbitrage finder" suggests current funds are already in the right currency.
    else:
        return 1.0


def sell(exchange, currrencySymToSell, currencySymSellingFor, ORDER_FILL_WAIT_MIN):
    #This branch is taken when an "arbitrage finder" suggests current funds need to be converted to a new currency.
    if(currrencySymToSell != currencySymSellingFor):
        #get original balances
        originalBaseCurrencyBalance = exchange.get_current_balance(currencySymSellingFor)
        originalNonBaseCurrencyBalance = exchange.get_current_balance(currrencySymToSell)

        timestamp = time.time()

        orderNum = exchange.place_sell_max_order(currrencySymToSell, currencySymSellingFor)

        #wait for order to sync with other api calls
        time.sleep(2)

        pair = currencySymSellingFor+'_'+currrencySymToSell
        if(not(exchange.wait_for_order_fill(orderNum, 'ask', timestamp, pair, ORDER_FILL_WAIT_MIN))):
            raise NameError("Order didn't completely fill.")

        #correct price of nextTradeStage to accont for different rates order filled at
        finalBaseCurrencyBalance = exchange.get_current_balance(currencySymSellingFor)
        finalNonBaseCurrencyBalance = exchange.get_current_balance(currrencySymToSell)
        effectivePrice = (finalBaseCurrencyBalance-originalBaseCurrencyBalance)/(originalNonBaseCurrencyBalance-finalBaseCurrencyBalance)
        print('Effective Price: '+str(effectivePrice))
        return effectivePrice

    #This branch is taken when an "arbitrage finder" suggests current funds are already in the right currency.
    else:
        return 1.0


def run_bot(key_folder_path):
    #load API keys
    bittrex_keys = load_keys(key_folder_path+'/bittrex_keys.txt')
    bithumb_keys = load_keys(key_folder_path+'/bithumb_keys.txt')

    #contants
    MAX_TRADE_CYCLES = 1
    DEPOSIT_WAIT_MIN = 60*5 #search for incomming deposits for 5hrs at most
    ARBITRAGE_OPPORTUNITY_WAIT_MIN = 60*24 #search for arbitrage oppertunities for a day at most
    ORDER_FILL_WAIT_MIN = 5 #wait 5 min for order to fill
    PROFIT_THRESHOLD = .01
    DEBUG = True
    PRINT_TOP_TRADES = True
    RESET_TRADE = True
    SESSION_NAME = 'Test_100'

    #make folder to store trades
    if(not(os.path.exists(SESSION_NAME))):
        os.mkdir(SESSION_NAME)
        os.mkdir(SESSION_NAME+'_Predicted')

    print("Setting Up Exchanges")
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

    exchangeA = bittrexArbitrageClient
    exchangeB = bithumbArbitrageClient

    if(RESET_TRADE):
        print('Resetting Trade')
        reset_trade(exchangeA, exchangeB)
        print('Trade Reset')
        input()

    print("Start Trading")
    #start trading
    for arbitrageCycle in range(MAX_TRADE_CYCLES):

        #WAIT for incomming/existing funds for arbitrage
        curCurrencySym = exchangeA.check_for_deposits(DEPOSIT_WAIT_MIN)

        #SEARCH for arbitrage oppertunities
        curTrade = Trade([]) #will store ACTUAL rates for various stages of the trade
        predictedTrade = Trade([]) #will store PREDICTED rates for various stages of the trade
        nextTradeStage = find_arbitrage_bittrex_bithum(exchangeA, exchangeB, ARBITRAGE_OPPORTUNITY_WAIT_MIN, PROFIT_THRESHOLD, curTrade, PRINT_TOP_TRADES)
        predictedTrade.stages.append(nextTradeStage)

        #BUY "coin1" @ bittrex if funds aren't already in this currency
        currrencySymToBuy = nextTradeStage.get_non_base_coin()
        nextTradeStage.price = buy(exchangeA, currrencySymToBuy, curCurrencySym, ORDER_FILL_WAIT_MIN)
        #update curTrade with most recently completed 'stage'
        curTrade.stages.append(nextTradeStage)

        #SEND funds to bithumb
        A2B = True
        send_funds(exchangeA, exchangeB, curTrade , A2B)
        
        #WAIT for funds to arrive at bithumb
        exchangeB.check_for_deposits(DEPOSIT_WAIT_MIN)

        #SEARCH for arbitrage oppertunities so coins are sold at right time
        nextTradeStage = find_arbitrage_bittrex_bithum(exchangeA, exchangeB, ARBITRAGE_OPPORTUNITY_WAIT_MIN, PROFIT_THRESHOLD, curTrade, PRINT_TOP_TRADES)
        predictedTrade.stages.append(nextTradeStage)

        #SELL "coin1" @ bithumb 
        currrencySymToSell = nextTradeStage.get_non_base_coin() #some coin sent over
        currencySymSellingFor = nextTradeStage.get_base_coin()  #KRW
        nextTradeStage.price = sell(exchangeB, currrencySymToSell, currencySymSellingFor, ORDER_FILL_WAIT_MIN)
        #update curTrade with most recently completed 'stage'
        curTrade.stages.append(nextTradeStage)

        #SEARCH for arbitrage oppertunities so coins are bought at right time
        nextTradeStage = find_arbitrage_bittrex_bithum(exchangeA, exchangeB, ARBITRAGE_OPPORTUNITY_WAIT_MIN, PROFIT_THRESHOLD, curTrade, PRINT_TOP_TRADES)
        predictedTrade.stages.append(nextTradeStage)

        #BUY "coin2" @ bithumb
        currrencySymToBuy = nextTradeStage.get_non_base_coin() #coin to send back
        currrencySymBuyingWith = nextTradeStage.get_base_coin()  #KRW
        nextTradeStage.price = buy(exchangeA, currrencySymToBuy, currrencySymBuyingWith, ORDER_FILL_WAIT_MIN)
        #update curTrade with most recently completed 'stage'
        curTrade.stages.append(nextTradeStage)

        #SEND funds to bittrex
        A2B = False
        send_funds(exchangeA, exchangeB, curTrade , A2B)

        #WAIT for funds to arrive at bittrex
        exchangeA.check_for_deposits(DEPOSIT_WAIT_MIN)

        #SEARCH for arbitrage oppertunities so coins are sold at right time
        nextTradeStage = find_arbitrage_bittrex_bithum(exchangeA, exchangeB, ARBITRAGE_OPPORTUNITY_WAIT_MIN, PROFIT_THRESHOLD, curTrade, PRINT_TOP_TRADES)
        predictedTrade.stages.append(nextTradeStage)

        #SELL "coin2" @ bittrex 
        currrencySymToSell = nextTradeStage.get_non_base_coin() #some coin sent over
        currencySymSellingFor = nextTradeStage.get_base_coin()  #KRW
        nextTradeStage.price = sell(exchangeA, currrencySymToSell, currencySymSellingFor, ORDER_FILL_WAIT_MIN)
        #update curTrade with most recently completed 'stage'
        curTrade.stages.append(nextTradeStage)

        save_trade(SESSION_NAME,arbitrageCycle,curTrade)
        save_trade(SESSION_NAME+'_Predicted',arbitrageCycle,curTrade)


    print("Done Trading")

if __name__ == '__main__':
    run_bot(sys.argv[1])


