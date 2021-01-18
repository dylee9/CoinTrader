class ExchangeClient(object):
    def __init__(self):
        #exceptions
        self.WRONG_PRICE_EXCEPTION = '1000'
        self.ORDER_DIDNT_FILL_EXCEPTION = '1001'

        #all exchanges are initially not resetting trades
        self.resettingTrade = False
