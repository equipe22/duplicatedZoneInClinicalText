from hegpdup.fingerprint_builder import FingerprintBuilder
from hegpdup.duplicate_finder import DuplicateFinder


def generateLink(docIntervalTree, threshold):
    link = []
    scoreDup = 0
    for comparison in docIntervalTree.keys():
        alreadyseen = []
        for interval in sorted(docIntervalTree[comparison]):
            duplication = interval.data
            targetSpan = duplication.targetSpan
            if targetSpan.length <= threshold or targetSpan in alreadyseen:
                continue
            scoreDup = scoreDup + targetSpan.length
            alreadyseen.append(targetSpan)
            sourceSpan = duplication.sourceSpan
            fromData = (
                comparison[0] + "," + str(sourceSpan.start) + "," + str(sourceSpan.end)
            )
            # to,start,end
            toData = (
                comparison[1] + "," + str(targetSpan.start) + "," + str(targetSpan.end)
            )
            link.append(fromData + "," + toData)
    return (link, scoreDup)


dataset = [
    line.replace('"', "").rstrip().split("\t")
    for line in open("/tmp/demo.txt", "r").readlines()
]
orf = 3
fingerprintList = [10]

for texts in dataset:
    print(texts)

    fingerprintBuilder = FingerprintBuilder(fingerprintList, orf)
    duplicateFinder = DuplicateFinder(fingerprintBuilder)

    for i, text in enumerate(texts):
        name = f"D{i}"
        comparisonTrees = duplicateFinder.buildComparisonTrees(name, text)
        if i == 0:
            continue
        print("Data tree")
        print(comparisonTrees)
        link, thisScore = generateLink(comparisonTrees, 15)

        print("finish a sentence")
        print(link)
        for el in link:
            thisexp = el.split(",")
            print(texts[0][int(thisexp[1]) : int(thisexp[2])])
            print(texts[1][int(thisexp[4]) : int(thisexp[5])])
            print("**********")
