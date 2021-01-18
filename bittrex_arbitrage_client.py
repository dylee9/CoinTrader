from bittrex_python_client import BittrexClient
import datetime
import time
from math import *

class BittrexArbitrageClient(BittrexClient):
    def __init__(self,
     apiKey, 
     apiSecret,
     name,
     baseCurrencies,
     tradableCurrencies,
     minFunds,
     isStartingExchange,
     debug):

        super(BittrexArbitrageClient, self).__init__(apiKey, apiSecret)

        self.TRADING_FEE = .0025
        self.baseCurrencies = baseCurrencies
        self.tradableCurrencies = tradableCurrencies
        self.minFunds = minFunds
        self.isStartingExchange = isStartingExchange
        self.debug = debug

    def round_rate(self, x, sigfigs, roundUp):
        exponent = floor(log10(copysign(x,1)))
        mantissa = x/10**exponent #get full precision mantissa

        if(roundUp):
            mantissa = ceil(mantissa * 10**(sigfigs-1)) / 10**(sigfigs-1) #round mantissa to sigfigs
        else:
            mantissa = floor(mantissa * 10**(sigfigs-1)) / 10**(sigfigs-1) #round mantissa to sigfigs

        return mantissa * 10**exponent

    def reformat_pair(self, pair):
        for i in range(len(pair)):
            if(pair[i] == '_'):
                pair = pair[0:i]+'-'+pair[i+1:len(pair)]
                return pair

        raise NameError("Badly formated pair. (No '_' char)")

    def place_buy_max_order(self, currencyToBuySym, currencyBuyingWithSym, sigFigs=4):
        """
        Input:
            currencyToBuySym: string
                symbol of coin to buy ('ETH', 'BTC' ect.)
            currencyBuyingWithSym: string
                symbol of coin you're buying with ('ETH', 'BTC' ect.)
            sigFigs: int
                the sigfig which will be rounded up to approximate the current rate 
                (4 seems to work decently)
        Output:
            ordernum: float
                unique identifier of the buy order            
        """
        #get currency pair
        currencyPair = currencyBuyingWithSym+'-'+currencyToBuySym

        #get last price (round up 4th sigfig)
        bittrexTickerResponse = self.get_ticker(currencyPair)
        lastAsk = float(bittrexTickerResponse['result']['Ask'])
        roundUp = True
        lastAsk = self.round_rate(lastAsk, sigFigs, roundUp)

        #get amount
        bittrexBalanceResponse = self.get_balance(currencyBuyingWithSym)
        balance = float(bittrexBalanceResponse['result']['Available'])
        amount = balance/lastAsk
        amount = amount/(1.0+self.TRADING_FEE)

        #execute buy
        buyResponse = self.buy_limit(currencyPair, amount, lastAsk)

        if(self.debug):
            print("Exchange: Bittrex")
            print("Ticker Price: "+str(float(bittrexTickerResponse['result']['Ask'])))
            print("Bought At: "+str(lastAsk))
            print('Amount: '+str(amount))
            print("Buy Response")
            print(buyResponse)

        #check response
        if(not(buyResponse['success'])):
            raise NameError('Bittrex buy of '+currencyPair+' failed.')
            
        return buyResponse['result']['uuid']



    def place_sell_max_order(self, currencyToSellSym, currencySellingForSym, sigFigs=4):
        """
        Input:
            currencyToSellSym: string
                symbol of coin to sell ('ETH', 'BTC' ect.)
            currencySellingForSym: string
                symbol of coin you're selling for ('ETH', 'BTC' ect.)
            sigFigs: int
                the sigfig which will be rounded up to approximate the current rate 
                (4 seems to work decently)
        Output:
            ordernum: float
                unique identifier of the buy order 
        """
				
        #get currency pair
        currencyPair = currencySellingForSym+'-'+currencyToSellSym

        #get last price (chop off everything past 4th sigfig for rate)
        bittrexTickerResponse = self.get_ticker(currencyPair)
        lastBid = float(bittrexTickerResponse['result']['Bid'])
        roundUp = False
        lastBid = self.round_rate(lastBid, sigFigs, roundUp)

        #get amount to sell
        bittrexBalanceResponse = self.get_balance(currencyToSellSym)
        balance = float(bittrexBalanceResponse['result']['Available'])
        balance = balance/(1.0+self.TRADING_FEE)

        #execute sell response
        sellResponse = self.sell_limit(currencyPair, balance, lastBid)

        if(self.debug):
            print("Exchange: Bittrex")
            print("Ticker Price: "+str(float(bittrexTickerResponse['result']['Bid'])))
            print("Sold At: "+str(lastBid))
            print('Amount: '+str(balance))
            print("Sell Response")
            print(sellResponse)

        #check response
        if(not(sellResponse['success'])):
            raise NameError('Bittrex sell of '+currencyPair+' failed.')

        return sellResponse['result']['uuid']
		
    def transfer_all(self, currencySym, addr):
        """
        Input:
            currencySym: string
                symbol of currency to transfer
            addr: string
                address of wallet to transfer to
        Output:
            Example:
                {"response":"Withdrew 2398 NXT."}
        """

        #chekc if address make sense
        if(currencySym=='ETH' and (addr[0:2]!='0x' or len(addr)!=42)):
            raise NameError('BAD ETH ADDRESS!!!!!')
        elif(currencySym=='BTC' and len(addr)!=34):
            raise NameError('BAD BTC ADDRESS!!!!!')
        elif(currencySym=='ETC' and (addr[0:2]!='0x' or len(addr)!=42)):
            raise NameError('BAD ETC ADDRESS!!!!!')
        elif(currencySym=='DASH' and len(addr)!=34):
            raise NameError('BAD DASH ADDRESS!!!!!')
        elif(currencySym=='XRP'):
            raise NameError('Need to study min XRP balance before using this currency.')

        bittrexBalanceResponse = self.get_balance(currencySym)
        balance = float(bittrexBalanceResponse['result']['Available'])

        if(self.debug):
            print("Exchange: Bittrex")
            print("Transfering "+str(balance)+" of "+currencySym+" to "+str(addr))

        return self.withdraw(currencySym, balance, addr)

    def wait_for_order_fill(self, orderNum, orderType, timestamp, currencyPair, waitMin):
        """
        Input:
            currencyPair: string
                currency pair of the orders being tracked
            waitMin: int
                amount of minits to wait for order to go through
            orderNum: int
                unique identifier of the order which needs to be filled
        Output:
            True if order went through False otherwise
        """
        if(self.debug):
            print("Exchange: Bittrex")
            print("Waiting For Order To Fill")

        checkFreq = 5
        numLoops = int((waitMin*60.0)/checkFreq)

        #reformat currency pair
        currencyPair = self.reformat_pair(currencyPair)

        #check orders every 5 seconds
        for i in range(numLoops):
            if(self.debug):
                print(".")

            orders = self.get_open_orders(currencyPair)

            #check if order to be filled is no longer open
            orderFilled = True
            for order in orders['result']:
                if(order['OrderUuid']==orderNum):
                    orderFilled = False
                    break

            if(not(orderFilled)):
                time.sleep(checkFreq)
            else:
                return True

        return False

    def check_for_deposits(self, waitMin):
        """
        Input:
            minAmt: float
                Minimum funds to be worthwile to do arbitrage with.
            waitMin: int
                Number of minutes to check if minAmt has been deposited.
            symsToTrade: list of strings
                Symbols of currencies to look out for.

        Output:
            Symbol of currency deposited.
        """
        if(self.debug):
            print("Exchange: Bittrex")
            print("Checking For Deposits")

        checkFreq = 10
        numLoops = int((waitMin*60.0)/checkFreq)
        symbolOfCurrencyDeposited = ''

        all_balances = {}

        #check balances every checkFreq sec
        for loop in range(numLoops):
            #loop through balances to see if any are large enough
            for currency in self.tradableCurrencies:
                #get balance
                
                bittrexBalanceResponse = self.get_balance(currency)
                balance = float(bittrexBalanceResponse['result']['Available'])

                #get USD price
                if(currency != 'DASH'):
                    bittrexTickerResponse = self.get_ticker('USDT-'+currency)
                    USDP = float(bittrexTickerResponse['result']['Last'])
                else:
                    bittrexTickerResponse = self.get_ticker('USDT-BTC')
                    USD_BTC = float(bittrexTickerResponse['result']['Last'])
                    bittrexTickerResponse = self.get_ticker('BTC-DASH')
                    BTC_DASH = float(bittrexTickerResponse['result']['Last'])
                    USDP = USD_BTC*BTC_DASH

                if(self.debug):
                    all_balances[currency] = balance

                if(balance*USDP > self.minFunds):
                    if(symbolOfCurrencyDeposited != ''):
                        raise NameError('Large amount of funds in more than one currency.')

                    symbolOfCurrencyDeposited = currency

            if(self.debug):
                print(all_balances)

            #check if found large balance
            if(symbolOfCurrencyDeposited != ''):
                break

            time.sleep(checkFreq)

        if(symbolOfCurrencyDeposited == ''):
            raise NameError('No deposits found in last: '+ str(waitMin)+' min')

        return symbolOfCurrencyDeposited

    def get_most_recent_prices(self, priceType):
        #convert priceType to string that can be used with bittrex api
        if(priceType == 'ask'):
            priceType = 'Ask'
        elif(priceType == 'bid'):
            priceType = 'Bid'
        elif(priceType == 'close'):
            priceType = 'Last'
        else:
            raise NameError('Invalid priceType.')

        relevantPairs = {}
        for baseCurrency in self.baseCurrencies:
            for tradableCurrency in self.tradableCurrencies:
                pair = baseCurrency+'-'+tradableCurrency

                #handle BTC_BTC pair
                if(baseCurrency == tradableCurrency):
                    relevantPairs[baseCurrency+'_'+tradableCurrency] = 1.0
                else:
                    bittrexTickerResponse = self.get_ticker(pair)
                    relevantPairs[baseCurrency+'_'+tradableCurrency] = float(bittrexTickerResponse['result']['Last'])

                time.sleep(2)

        return relevantPairs

    def get_wallets(self, currencies):
        #check wallets loaded from api with wallets visible on exchange
        visible_wallets = {
        'BTC':'1Md1bDLyQXqQJeHDXuB3XqyDrQ6AbCim4N',
        'ETH':'0x7343042f53727f9af8e87d0c2eb3a5cad97ad593',
        'ETC':'0x5d28263c72f013d1ca9f48a4ce1eadde067c0325',
        'LTC':'LWKuWrXSe1FHQZwzXMyDBYJWWLgN231CMJ',
        'DASH':'XfYGfcrpiJVGCoouhYh2ypX3YfKv6GhLy4',
        }

        relevant_wallets = {}
        for currency in currencies:
            #get wallet address according to api
            wallet_address = self.get_deposit_address(currency)
            wallet_address = wallet_address['result']['Address']

            #compare api wallet addr with visible wallet address
            if(visible_wallets[currency] != wallet_address):
                raise NameError("Api and visible "+currency+" wallets don't match!")
            else:
                relevant_wallets[currency] = wallet_address

        return relevant_wallets

    def get_current_balance(self, currency):
        bittrexBalanceResponse = self.get_balance(currency)
        return float(bittrexBalanceResponse['result']['Available'])

