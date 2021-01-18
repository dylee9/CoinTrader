import sys
from bithumb_python_client import BithumbClient
import pprint
import time
from math import *

class BithumbArbitrageClient(BithumbClient):
    def __init__(self, 
        apiKey, 
        apiSecret,
        name,
        baseCurrencies,
        tradableCurrencies,
        minFunds,
        isStartingExchange, 
        debug):

        super(BithumbArbitrageClient, self).__init__(apiKey, apiSecret)

        self.name = name
        self.baseCurrencies = baseCurrencies
        self.tradableCurrencies = tradableCurrencies
        self.minFunds = minFunds
        self.isStartingExchange = isStartingExchange
        self.debug = debug
        self.transferFees = {'BTC':0.00050000,
            'ETH':0.01010000,
            'ETC':0.01010000,
            'LTC':0.01010000,
            'DASH':0.01010000}

    def round_down(self, x, digits=4.0):
        return floor(float(x) * pow(10.0, digits))/pow(10.0, digits)

    def round_rate(self, x, sigfigs, roundUp):
        exponent = floor(log10(copysign(x,1)))
        mantissa = x/10**exponent #get full precision mantissa

        if(roundUp):
            mantissa = ceil(mantissa * 10**(sigfigs-1)) / 10**(sigfigs-1) #round mantissa to sigfigs
        else:
            mantissa = floor(mantissa * 10**(sigfigs-1)) / 10**(sigfigs-1) #round mantissa to sigfigs

        return mantissa * 10**exponent

    def get_non_base_coin(self, pair):
        #find pair divider index
        dividerIdx = 0
        for i in range(len(pair)):
            if(pair[i] == '_'):
                dividerIdx = i
                break

        return pair[dividerIdx+1:len(pair)]

    def get_most_recent_prices(self, priceType):
        """
        Input:
            priceType: string
                ('ask', 'bid', 'close')
        Output:
            priceDict: dictionary
                {'KRW_BTC' : 2585616, 'KRW_ETH': ... }
        """
        #convert priceType to string that can be used with bithum api
        if(priceType == 'ask'):
            priceType = 'sell_price'
        elif(priceType == 'bid'):
            priceType = 'buy_price'
        elif(priceType == 'close'):
            priceType = 'closing_price'
        else:
            raise NameError('Invalid priceType.')

        priceDict = {}
        for baseCurrency in self.baseCurrencies:
            for tradableCurrency in self.tradableCurrencies:
                priceInfo = self.xcoinApiCall("/public/ticker/"+tradableCurrency, {})
                price = priceInfo['data'][priceType]
                priceDict[baseCurrency+'_'+tradableCurrency] = float(price)

        #returns dictionary of closing prices
        return priceDict

    def get_wallets(self, currencies):
        #get relevant wallets
        relevant_wallets = {}
        for currency in currencies:
            rgParams = {'currency':currency}
            walletData = self.xcoinApiCall("/info/wallet_address", rgParams);
            relevant_wallets[currency] = walletData['data']['wallet_address']

        #check wallets loaded from api with wallets visible on exchange
        visible_wallets = {
        'BTC':'1JKs75F5xNwzHNPmaDpAtiM99fYTogx4XH',
        'ETH':'0x8954fd987a27546f3e30707407c0e8ef33ba53ad',
        'ETC':'0x8ea05b29a0b276b9a476ea36ad69bb2742206e80',
        'LTC':'LcaXAVnChARLPMXbuuFp5P5ZHJ98qkJzuQ',
        'DASH':'XguJb682BiLkEJZqH6PULq1oeZqFzuBdzQ',
        }

        for currency in currencies:
            if(visible_wallets[currency] != relevant_wallets[currency]):
                raise NameError("Api and visible "+currency+" wallets don't match!")

        return relevant_wallets

    def place_buy_max_order(self, currencytoBuySym, currencyBuyingWithSym, sigFigs=4):
        #get current closing price (4sigfigs)
        unRoundedlastPrice = self.get_most_recent_prices('close')[currencyBuyingWithSym+'_'+currencytoBuySym]
        roundUp = True
        lastPrice = self.round_rate(unRoundedlastPrice, sigFigs, roundUp)

        #get amount
        balanceInfo = self.xcoinApiCall("/info/balance", {"currency": 'BTC'})
        krwBalance = balanceInfo['data']['available_krw']
        amount = self.round_down(float(krwBalance)/lastPrice)

        #purchase coins & reformat response
        rgParams = {
        'order_currency': currencytoBuySym,
        'payment_currency': 'KRW',
        'units': amount,
        'price': int(lastPrice),
        'type': 'bid',
        'misu': 'N'
        }

        print(rgParams)

        buyResponse = self.xcoinApiCall("/trade/place", rgParams)

        if(self.debug):
            print("Exchange: Bithumb")
            print("Ticker Price: "+str(unRoundedlastPrice))
            print("Bought At: "+str(lastPrice))
            print('Amount: '+str(amount))
            print("Buy Response")
            print(buyResponse)

        return buyResponse['order_id']

    def place_sell_max_order(self, currencyToSellSym, currencySellingForSym, sigFigs=4):

        #get amount to sell
        balance = self.round_down(self.get_current_balance(currencyToSellSym))
        price = self.get_most_recent_prices('close')[currencySellingForSym+'_'+currencyToSellSym]

        #purchase coins & reformat response
        rgParams = {
        'order_currency': currencyToSellSym,
        'payment_currency': currencySellingForSym,
        'units': balance,
        'price': int(price),
        'type': 'ask',
        'misu': 'N'
        }

        sellResponse = self.xcoinApiCall("/trade/place", rgParams)

        if(self.debug):
            print("Exchange: Bithumb")
            print("Ticker Price: "+str(price))
            print("Sold At: "+str(price))
            print('Amount: '+str(balance))
            print("Sell Response")
            print(sellResponse)

        return sellResponse['order_id']


    def transfer_all(self, currencySym, addr):

        #check if address is valid
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

        #get amount to transfer
        balance = self.get_current_balance(currencySym)
        balance -= self.transferFees[currencySym]

        #withdraw coins to given address (need destination parameter for ripple)
        rgParams = {
        'units': balance,
        'address': addr,
        'currency': currencySym,
        }

        withdrawResponse = self.xcoinApiCall("/trade/btc_withdrawal", rgParams)

        if(self.debug):
            print("Exchange: Bithumb")
            print("Transfering "+str(balance)+" of "+currencySym+" to "+str(addr))
            print("Withdrawal Response")
            print(withdrawResponse)

        return withdrawResponse

    #wait for withdraw order to complete (only has tracking for withdrawals)
    def wait_for_withdraw_order_fill(self, currencySym, waitMin):

        checkFreq = 5
        numLoops = int((waitMin*60.0)/checkFreq)
        rgParams = {
        'searchGb': '3',
        'currency': currencySym,
        }

        #check orders every 5 seconds
        for i in range(numLoops):
            ordersResponse = self.xcoinApiCall("/info/user_transactions", rgParams)
            orders = ordersResponse['data']

            if(len(orders)>0):
                time.sleep(checkFreq)
            else:
                return True

        return False

    def wait_for_order_fill(self, order_id, order_type, timestamp, currencyPair, waitMin):
        if(self.debug):
            print("Exchange: Bithumb")
            print("Waiting For Order To Fill")

        #get number of checks
        checkFreq = 5
        numLoops = int((waitMin*60.0)/checkFreq)

        #instanciate api params
        currencySym = self.get_non_base_coin(currencyPair)

        rgParams = {
        'order_id': order_id,
        'type': order_type,
        'count': 1,
        'after': int(timestamp),
        'currency': currencySym
        }

        #check orders every 5 seconds
        for i in range(numLoops):
            if(self.debug):
                print(".")

            orderResponse = self.xcoinApiCall("/info/orders", rgParams)

            #no open orders
            if(orderResponse['status'] == '5600'):
                return True
            else:
                print("Sleeping")
                time.sleep(checkFreq)

        return False

    def check_for_deposits(self, waitMin):
        if(self.debug):
            print("Exchange: Bithumb")
            print("Checking For Deposits")
            all_balances = {}

        checkFreq = 5
        numLoops = int((waitMin*60.0)/checkFreq)
        symbolOfCurrencyDeposited = ''

        #get currencies to loop through
        allCurrencies = set(self.baseCurrencies+self.tradableCurrencies)

        #check balances every 5sec
        for loop in range(numLoops):
            krwPrices = self.get_most_recent_prices('close')

            #loop through balances to see if any are large enough
            for currency in allCurrencies:
                #get balance of currency
                amt = float(self.get_current_balance(currency))

                #get value of currency in KRW
                if(currency != 'KRW'):
                    krwPrice = float(krwPrices['KRW_'+currency])
                else:
                    krwPrice = 1.0

                #store debugging info
                if(self.debug):
                    all_balances[currency] = amt

                #check if there are enough funds for an arbitrage trade
                if(amt*krwPrice > self.minFunds):
                    if(symbolOfCurrencyDeposited != ''):
                        raise NameError('Large amount of funds in more than one currency.')

                    symbolOfCurrencyDeposited = currency

            #display debugging info
            if(self.debug):
                print(all_balances)

            #check if found large balance
            if(symbolOfCurrencyDeposited != ''):
                break

            time.sleep(checkFreq)

        if(symbolOfCurrencyDeposited == ''):
            raise NameError('No deposits found in last: '+ str(waitMin)+' min')

        return symbolOfCurrencyDeposited

    def get_current_balance(self, currencySym):
        #KRW balance has to be handeled differently from other balances
        if(currencySym != 'KRW'):
            rgParams = {'currency': currencySym}
        else:
            rgParams = {'currency': 'BTC'}

        currency_wallet_info = self.xcoinApiCall("/info/balance", rgParams)
        loweredCurrencySym = currencySym.lower()
        balance = currency_wallet_info['data']['available_%s'%loweredCurrencySym]

        return float(balance)


# # Test Reformating
# buySellOutput = {
#     "status"    : "0000",
#     "order_id"  : "1429500241523",
#     "data": [
#         {
#             "cont_id"   : "15364",
#             "units"     : "0.16789964",
#             "price"     : "270000",
#             "total"     : 45333,
#             "fee"       : "0.00016790"
#         },
#         {
#             "cont_id"   : "15365",
#             "units"     : "0.08210036",
#             "price"     : "289000",
#             "total"     : 23727,
#             "fee"       : "0.00008210"
#         }
#     ]
# }
# print(bithumbArbitrageClient.reformat_sell_response(buySellOutput,'ETH'))

# Test Rounding
# print(bithumbArbitrageClient.round_rate(0.10173050, 4, True))
# print(bithumbArbitrageClient.round_down(1.2229,3))
# print(bithumbArbitrageClient.round_down(1.2229,4))

#Test Sell
#print(bithumbArbitrageClient.place_sell_max_order('ETC'))

#Test Buy
# print(bithumbArbitrageClient.place_buy_max_order('ETC'))

# test check for deposit
# print(bithumbArbitrageClient.check_for_deposits(1.0,['BTC','ETC','ETH']))

#test transfer all
# print(bithumbArbitrageClient.transfer_all('BTC', '3NjjYZ5DedWKekJECC27w8VBWd3uXZXYQD'))

#test get balance
# print(bithumbArbitrageClient.get_balance('BTC'))