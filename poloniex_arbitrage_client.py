from poloniex_python_client import PoloniexClient
import datetime
import time
from math import *

class PoloniexArbitrageClient(PoloniexClient):
    def round_rate(self, x, sigfigs, roundUp):
        exponent = floor(log10(copysign(x,1)))
        mantissa = x/10**exponent #get full precision mantissa

        if(roundUp):
            mantissa = ceil(mantissa * 10**(sigfigs-1)) / 10**(sigfigs-1) #round mantissa to sigfigs
        else:
            mantissa = floor(mantissa * 10**(sigfigs-1)) / 10**(sigfigs-1) #round mantissa to sigfigs

        return mantissa * 10**exponent

    def reformat_buy_response(self, buyResponse, currencyToBuySym, currencyBuyingWithSym):
        """
        Input:
            Example:
            {"orderNumber":31226040,
            "resultingTrades":[{"amount":"338.8732",
                "date":"2014-10-18 23:03:21",
                "rate":"0.00000173",
                "total":"0.00058625",
                "tradeID":"16164",
                "type":"buy"}]}
        Output:
            Example:
            {'CurrencyBought': 'XRP', 
            'CurrencyBoughtWith' : 'BTC',
            'Trades':[{'amount': 338.8732,
                'date': 1499395078,
                'rate': 0.00000173]}
        """
        trades = buyResponse['resultingTrades']
        tradesReformated = []

        for trade in trades:
            newDate = time.mktime(datetime.datetime.strptime(trade['date'], "%Y-%m-%d %H:%M:%S").timetuple())
            newRate = float(trade['rate'])
            newAmount = float(trade['amount'])
            tradeReformated = {}
            tradeReformated['amount'] = newAmount
            tradeReformated['date'] = newDate
            tradeReformated['rate'] = newRate
            tradesReformated.append(tradeReformated)

        reformatedResponse = {}
        reformatedResponse['CurrencyBought'] = currencyToBuySym
        reformatedResponse['CurrencyBoughtWith'] = currencyBuyingWithSym
        reformatedResponse['Trades'] = tradesReformated
        return reformatedResponse

    def reformat_sell_response(self, sellResponse, currencyToSellSym, currencySellingForSym):
        """
        Input:
            Example:
            {"orderNumber":31226040,
            "resultingTrades":[{"amount":"338.8732",
                "date":"2014-10-18 23:03:21",
                "rate":"0.00000173",
                "total":"0.00058625",
                "tradeID":"16164",
                "type":"buy"}]}
        Output:
            Example:
            {'CurrencySold': 'XRP', 
            'CurrencySoldFor' : 'BTC',
            'Trades':[{'amount': 338.8732,
                'date': 1499395078,
                'rate': 0.00000173]}
        """

        trades = sellResponse['resultingTrades']
        tradesReformated = []

        for trade in trades:
            newDate = time.mktime(datetime.datetime.strptime(trade['date'], "%Y-%m-%d %H:%M:%S").timetuple())
            newRate = float(trade['rate'])
            newAmount = float(trade['amount'])
            tradeReformated = {}
            tradeReformated['amount'] = newAmount
            tradeReformated['date'] = newDate
            tradeReformated['rate'] = newRate
            tradesReformated.append(tradeReformated)

        reformatedResponse = {}
        reformatedResponse['CurrencySold'] = currencyToSellSym
        reformatedResponse['CurrencySoldFor'] = currencySellingForSym
        reformatedResponse['Trades'] = tradesReformated
        return reformatedResponse

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
            Example:
            {'CurrencyBought': 'XRP', 
            'CurrencyBoughtWith' : 'BTC',
            'Trades':[{'amount': 338.8732,
                'date': 1499395078,
                'rate': 0.00000173]}
        """
        #get currency pair
        currencyPair = currencyBuyingWithSym+'_'+currencyToBuySym

        #get last price (round up 4th sigfig)
        poloniexCandlestickData = self.returnTicker()
        lastPrice = float(poloniexCandlestickData[currencyPair]['last'])
        roundUp = True
        lastPrice = self.round_rate(lastPrice, sigFigs, roundUp)

        #get amount
        poloniexBalances = self.returnBalances()
        balance = float(poloniexBalances[currencyBuyingWithSym])
        amount = balance/lastPrice

        #execute buy and reformat response
        buyResponse = self.buy(currencyPair, lastPrice, amount)
        return int(buyResponse['orderNumber'])



    def place_sell_max_order(self, currencyToSellSym, currencySellingForSym, sigfigs=4):
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
            Example:
            {'CurrencyBought': 'XRP', 
            'CurrencyBoughtWith' : 'BTC',
            'Trades':[{'amount': 338.8732,
                'date': 1499395078,
                'rate': 0.00000173]}
        """
				
        #get currency pair
        currencyPair = currencySellingForSym+'_'+currencyToSellSym

        #get last price (chop off everything past 4th sigfig for rate)
        poloniexCandlestickData = self.returnTicker()
        lastPrice = float(poloniexCandlestickData[currencyPair]['last'])
        sigFigs = 4
        roundUp = False
        lastPrice = self.round_rate(lastPrice, sigFigs, roundUp)

        #get amount to sell
        poloniexBalances = self.returnBalances()
        balance = float(poloniexBalances[currencyToSellSym])

        #execute sell and reformat response
        sellResponse = self.sell(currencyPair,lastPrice, balance)
        return int(sellResponse['orderNumber'])
		
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



        poloniexBalances = self.returnBalances()
        balance = float(poloniexBalances[currencySym])
        return self.withdraw(currencySym, balance, addr)

    def wait_for_order_fill(self, currencyPair, waitMin, orderNum):
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
        checkFreq = 5
        numLoops = int((waitMin*60.0)/checkFreq)

        #check orders every 5 seconds
        for i in range(numLoops):
            orders = self.returnOpenOrders(currencyPair)

            #check if order to be filled is no longer open
            orderFilled = True
            for order in orders:
                if(int(order['orderNumber'])==orderNum):
                    orderFilled = False
                    break

            if(not(orderFilled)):
                time.sleep(5)
            else:
                return True

        return False

    def check_for_deposits(self, minAmt, waitMin, symsToTrade):
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

        checkFreq = 5
        numLoops = int((waitMin*60.0)/checkFreq)
        symbolOfCurrencyDeposited = ''

        #check balances every 5sec
        for loop in range(numLoops):
            balances = self.returnBalances()

            #get US dollar tethers
            USDT = self.returnTicker()

            #loop through balances to see if any are large enough
            for currency in symsToTrade:
                #get balances
                amt = float(balances[currency])
                usdPrice = float(USDT['USDT_'+currency]['last'])

                if(amt*usdPrice > minAmt):
                    symbolOfCurrencyDeposited = currency
                    break

            #check if found large balance
            if(symbolOfCurrencyDeposited != ''):
                break

            time.sleep(5)

        if(symbolOfCurrencyDeposited == ''):
            raise NameError('No deposits found in last: '+ str(waitMin)+' min')

        return symbolOfCurrencyDeposited

    def get_most_recent_prices(self, baseCurrencies, tradableCurrencies):
        allPairs = self.returnTicker()
        relevantPairs = {}
        for baseCurrency in baseCurrencies:
            for tradableCurrency in tradableCurrencies:
                pair = baseCurrency+'_'+tradableCurrency

                #handle BTC_BTC pair
                if(baseCurrency == tradableCurrency):
                    relevantPairs[pair] = 1.0
                else:
                    relevantPairs[pair] = float(allPairs[pair]['last'])

        return relevantPairs

    def get_wallets(self, currencies):
        #get all wallets
        all_wallets = self.api_query('returnDepositAddresses')

        #get relevant wallets
        relevant_wallets = {}
        for currency in currencies:
            relevant_wallets[currency] = all_wallets[currency]

        #check wallets loaded from api with wallets visible on exchange
        visible_wallets = {
        'BTC':'1CTdgeE7xYPcV5HYRFrQFpryorz7qZEdN5',
        'ETH':'0x4990dda0d27067f045cf2ea4f98248e1d2355018',
        'ETC':'0x5d039fd1d306000a4bf691d2aeffc395ac1c21c0',
        'LTC':'LLgfY6oWpEub5NiG7CF54PsfqhSMDWExxP',
        'DASH':'Xszwp7FADp3evooTYkT95opNX6vgFidrTV',
        }

        for currency in currencies:
            if(visible_wallets[currency] != relevant_wallets[currency]):
                raise NameError("Api and visible "+currency+" wallets don't match!")

        return relevant_wallets

    def get_effective_price(self, tradeStartingTime, currencyPair, orderNumber):
        tradeHistory = self.returnTradeHistory(currencyPair, tradeStartingTime, floor(time.time()))

        totalBaseCurrency = 0
        totalNonBaseCurrency = 0
        for trade in tradeHistory:
            if(trade['orderNumber'] == orderNumber):
                totalBaseCurrency+=float(trade['total'])
                totalNonBaseCurrency+=float(trade['amount'])

        return totalBaseCurrency/totalNonBaseCurrency

