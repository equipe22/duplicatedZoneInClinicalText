from hegpdup.fingerprint_builder import FingerprintBuilder
from hegpdup.duplicate_finder import DuplicateFinder


def generateLink(docIntervalTree, threshold):
    link = []
    scoreDup = 0
    for comparison in docIntervalTree.keys():
        alreadyseen = []
        for duplication in sorted(docIntervalTree[comparison]):
            # from,start,end
            if (duplication.end - duplication.begin) <= threshold or (
                duplication.end,
                duplication.begin,
            ) in alreadyseen:
                continue
            scoreDup = scoreDup + (duplication.data.end - duplication.data.start)
            alreadyseen.append((duplication.data.end, duplication.data.start))
            fromData = (
                comparison[0]
                + ","
                + str(duplication.begin)
                + ","
                + str(duplication.end)
            )
            # to,start,end
            toData = (
                comparison[1]
                + ","
                + str(duplication.data.start)
                + ","
                + str(duplication.data.end)
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
    fingerprintBuilder = FingerprintBuilder(
        fingerprintList, orf, dataset[candicate][0:2]
    )
    duplicateFinder = DuplicateFinder()
    duplicateFinder.buildTree_comparisons(fingerprintBuilder.figprintId)
    duplicateFinder.mergeOverlap(fingerprintBuilder.figprintId)
    print(candicate)
    duplicateFinder.expandOverlap()
    link, thisScore = generateLink(duplicateFinder.resultTree, 15)
    print("Data tree")
    print(duplicateFinder.resultTree)
    print("finish a sentence")
    print(link)
    for el in link:
        thisexp = el.split(",")
        print(dataset[candicate][0][int(thisexp[1]) : int(thisexp[2])])
        print(dataset[candicate][1][int(thisexp[4]) : int(thisexp[5])])
        print("**********")
