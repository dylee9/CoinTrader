class TradeStage:
	def __init__(self, buyOrSell, tradingPair, price):
		self.buyOrSell = buyOrSell
		self.tradingPair = tradingPair
		self.price = price

	def get_non_base_coin(self):
		#find pair divider index
		dividerIdx = 0
		for i in range(len(self.tradingPair)):
			if(self.tradingPair[i] == '_'):
				dividerIdx = i
				break

		return self.tradingPair[dividerIdx+1:len(self.tradingPair)]

	def get_base_coin(self):
		#find pair divider index
		dividerIdx = 0
		for i in range(len(self.tradingPair)):
			if(self.tradingPair[i] == '_'):
				dividerIdx = i
				break

		return self.tradingPair[0:dividerIdx]

	def toString(self):
		baseCoin = self.get_base_coin()
		nonBaseCoin = self.get_non_base_coin()

		if(self.buyOrSell == 'BUY'):
			return [baseCoin, nonBaseCoin]
		else:
			return [nonBaseCoin, baseCoin]

	def to_dictionary(self):
		return {'buyOrSell':self.buyOrSell,'tradingPair':self.tradingPair,'price':self.price}

class Trade:
	def __init__(self, stages):
		self.stages = stages
		self.profit = 0

	def get_most_recent_stage(self):
		return self.stages[len(self.stages)-1]

	def __str__(self):
		string = ''
		for i in range(len(self.stages)):
			pairs = self.stages[i].toString()
			if(i == 0):
				string = pairs[0]+'-->'+pairs[1]
			else:
				string+='-->'+pairs[1]



		string += ' Profit: '+str(self.profit)

		return string

	def to_dictionary(self):
		tradeDict = {'stages':[]}
		for stage in self.stages:
			tradeDict['stages'].append(stage.to_dictionary())
		return tradeDict
