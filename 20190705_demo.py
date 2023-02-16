from hegpdup.fingerprints import Fingerprints
from hegpdup.doctrees import DocTrees


def generateLink(docIntervalTree, threshold):
    link = []
    scoreDup = 0
    for comparison in docIntervalTree.keys():
        alreadyseen = []
        for duplication in sorted(docIntervalTree[comparison]):
            # from,start,end
            if (duplication.end - duplication.begin) > threshold and (
                duplication.end,
                duplication.begin,
            ) not in alreadyseen:
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



dataset = [
    line.replace('"', "").rstrip().split("\t")
    for line in open("/tmp/demo.txt", "r").readlines()
]
orf = 3
fingerprintList = [10]

for candicate in range(0, len(dataset)):
    figerprintsId = Fingerprints(fingerprintList, orf, dataset[candicate][0:2])
    thisDocTree = DocTrees()
    thisDocTree.buildTree_comparisons(figerprintsId.figprintId)
    thisDocTree.mergeOverlap(figerprintsId.figprintId)
    print(candicate)
    dictData = {"D0": len(dataset[candicate][0]), "D1": len(dataset[candicate][1])}
    thisDocTree.expandOverlap(dictData)
    link, thisScore = generateLink(thisDocTree.resultTree, 15)
    print("Data tree")
    print(thisDocTree.resultTree)
    print("finish a sentence")
    print(link)
    for el in link:
        thisexp = el.split(",")
        print(dataset[candicate][0][int(thisexp[1]) : int(thisexp[2])])
        print(dataset[candicate][1][int(thisexp[4]) : int(thisexp[5])])
        print("**********")
