from utils import Trade, TradeStage


class ArbitrageFinder:
    def find_arbitrage_bittrex_bithum(self, bittrex, bithumb, waitMinutes, profitThreshold, curTrade, printTrades):
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
                                stages.append(TradeStage('BUY', pairs[0], bittrexRecentPricesBid[pairs[0]]))
                                stages.append(TradeStage('SELL', pairs[1], bithumbRecentPricesAsk[pairs[1]]))     
                                stages.append(TradeStage('BUY',pairs[2], bithumbRecentPricesBid[pairs[2]]))
                                stages.append(TradeStage('SELL', pairs[3], bittrexRecentPricesAsk[pairs[3]]))
                                """
                                stages.append(TradeStage('BUY', pairs[0], bittrexRecentPricesBid[pairs[0]]*1.0025))
                                stages.append(TradeStage('SELL', pairs[1], bithumbRecentPricesAsk[pairs[1]]*0.9985))     
                                stages.append(TradeStage('BUY',pairs[2], bithumbRecentPricesBid[pairs[2]]*1.0015))
                                stages.append(TradeStage('SELL', pairs[3], bittrexRecentPricesAsk[pairs[3]]*0.9975))
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