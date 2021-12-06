from mempool import Mempool
from abstract_builder import Blockbuilder
from collections import OrderedDict
from ancestor_set import AncestorSet
import logging

import heapq

class BlockbuilderByAnces(Blockbuilder):
    def __init__(self, mempool, weightLimit=3992820):
        self.mempool = mempool
        self.refMempool = Mempool()
        self.refMempool.fromDict(mempool.txs)
        self.selectedTxs = []
        self.availableWeight = weightLimit
        self.ancestorSets = []
        self.txAncestorSetMap = {}

    def initialize_stubs(self):
        for txid, tx in self.mempool.txs.items():
            # Initialize all AncestorSets just with tx itself
            ancestorSet = AncestorSet(tx)
            print("AncestorSet created: " + str(ancestorSet))
            heapq.heappush(self.ancestorSets, ancestorSet)
            self.txAncestorSetMap[txid] = ancestorSet

    def buildBlockTemplate(self):
        # TODO: Heapify transactions by transaction feerate, only calculate ancestorfeerate when transaction bubbles to the top.
        # TODO: If transaction with ancestor feerate bubbles up, include in block
        logging.info("Building blocktemplate...")
        initialize_stubs()

        while(len(self.ancestorSets) > 0):
            bestAncestorSet = heapq.heappop(self.ancestorSets)
            if bestAncestorSet.isObsolete:
                # execute lazy delete
                continue
            elif not bestAncestorSet.isComplete:
                print("backfilling: " + str(bestAncestorSet))
                # Update incomplete AncestorSets lazily when relevant
                missing_ancestors = []
                for txid in bestAncestorSet.getAncestorTxids():
                    missing_ancestors.append(self.mempool.txs[txid])
                print("Missing ancestors: " + str(missing_ancestors))
                bestAncestorSet.update(missing_ancestors)
                heapq.heappush(self.ancestorSets, bestAncestorSet)
            elif bestAncestorSet.isComplete:
                # Complete AncestorSet has highest feerate
                if bestAncestorSet.getWeight() > self.availableWeight:
                    # Doesn't fit in the block, discard
                    continue
                else:
                    # Add to block
                    txsIdsToAdd = list(bestAncestorSet.txs.keys())
                    print("txsIdsToAdd: " + str(txsIdsToAdd))
                    while len(txsIdsToAdd) > 0:
                        for txid in txsIdsToAdd:
                            print("Try adding txid: " + str(txid))
                            if set(self.refMempool.txs[txid].parents).issubset(set(self.selectedTxs)):
                                self.selectedTxs.append(txid)
                                txsIdsToAdd.remove(txid)
                    self.availableWeight -= bestAncestorSet.getWeight()

                    remainingDescendants = bestAncestorSet.getAllDescendants()

                    for d in remainingDescendants:
                        print("Stubbing remaining descendant: " + str(d))
                        descendantAncestorSet = self.txAncestorSetMap[d]
                        if descendantAncestorSet.isComplete:
                            # lazy delete and add stub as replacement
                            descendantAncestorSet.isObsolete = True
                            replacement = AncestorSet(self.mempool.txs[d])
                            self.txAncestorSetMap[d] = replacement
                            heapq.heappush(self.ancestorSets, replacement)

                    for txid in bestAncestorSet.txs.keys():
                        # lazy delete ancestor sets corresponding to included set
                        if txid in self.txAncestorSetMap.keys():
                            self.txAncestorSetMap[txid].isObsolete = True
                        self.mempool.removeConfirmedTx(txid)

        return self.selectedTxs


    def outputBlockTemplate(self, blockId=""):
        raise Exception("not implemented")

if __name__ == '__main__':
    mempool = bb.Mempool()
    mempool.fromTXT("monthTest/100124-000123.mempool")
    builder = BlockbuilderByAnces(mempool)
    print("block is "+str(builder.buildBlockTemplate(100000)))
