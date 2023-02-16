import logging
import sys
import time

from hegpdup.fingerprints import Fingerprints
from hegpdup.doctrees import DocTrees
from intervaltree import IntervalTree


def generateLink(docIntervalTree, threshold):
    link = []
    scoreDup = 0
    for comparison in docIntervalTree.keys():
        alreadyseen = []
        for duplication in sorted(docIntervalTree[comparison]):
            # logger.debug(duplication)
            # from,start,end
            if (duplication.end - duplication.begin) > threshold and (
                duplication.end,
                duplication.begin,
            ) not in alreadyseen:
                # scoreDup=scoreDup+(duplication.end - duplication.begin)
                scoreDup = scoreDup + (
                    duplication.data["end"] - duplication.data["start"]
                )
                alreadyseen.append((duplication.data["end"], duplication.data["start"]))
                fromData = (
                    comparison.split("_")[0]
                    + ","
                    + str(duplication.begin)
                    + ","
                    + str(duplication.end)
                )
                # to,start,end
                toData = (
                    comparison.split("_")[1]
                    + ","
                    + str(duplication.data["start"])
                    + ","
                    + str(duplication.data["end"])
                )
                link.append(fromData + "," + toData)
    return (link, scoreDup)


logger = logging.getLogger(__name__)
logging.basicConfig(
    format="""%(asctime)s -- %(name)s - %(levelname)s :
                    %(messagepathToOutput)s""",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    level=logging.INFO,
)
dataset = [
    line.replace('"', "").rstrip().split("\t")
    for line in open("/tmp/demo.txt", "r").readlines()
]
orf = 3
fingerprintList = [10]
results = []

for candicate in range(0, len(dataset)):
    figerprintsId = Fingerprints(fingerprintList, orf, dataset[candicate][0:2])
    # ~ print(figerprintsId.figprint)
    # logger.info(figerprintsId.figprint)
    # logger.info(figerprintsId.figprintId)
    thisDocTree = DocTrees("akey")
    thisDocTree.buildTree_comparisons(figerprintsId.figprintId)
    thisDocTree.mergeOverlap(
        "myPatientDuplication.patientTexts", "keyRoot", figerprintsId.figprintId
    )
    print(candicate)
    dictData = {"D0": len(dataset[candicate][0]), "D1": len(dataset[candicate][1])}
    thisDocTree.expandOverlap(dictData)
    link, thisScore = generateLink(thisDocTree.resultTree, 15)
    # thisScore*1.0/(dictData["D0"]+dictData["D1"])
    # thisScore*1.0/dictData["D1"]
    results.append([candicate, thisScore, dictData["D0"], dictData["D1"], link])
    print("Data tree")
    print(thisDocTree.resultTree)
    print("finish a sentence")
    print(link)
    for el in link:
        thisexp = el.split(",")
        print(dataset[candicate][0][int(thisexp[1]) : int(thisexp[2])])
        print(dataset[candicate][1][int(thisexp[4]) : int(thisexp[5])])
        print("**********")
