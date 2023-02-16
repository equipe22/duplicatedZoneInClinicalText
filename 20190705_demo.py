from hegpdup.fingerprint_builder import FingerprintBuilder
from hegpdup.duplicate_finder import DuplicateFinder


def generateLink(duplicates, docNameTo):
    link = []
    scoreDup = 0
    alreadyseen = []
    for duplication in duplicates:
        targetSpan = duplication.targetSpan
        if targetSpan in alreadyseen:
            continue
        scoreDup = scoreDup + targetSpan.length
        alreadyseen.append(targetSpan)
        sourceSpan = duplication.sourceSpan
        fromData = (
            duplication.sourceDocId
            + ","
            + str(sourceSpan.start)
            + ","
            + str(sourceSpan.end)
        )
        # to,start,end
        toData = docNameTo + "," + str(targetSpan.start) + "," + str(targetSpan.end)
        link.append(fromData + "," + toData)
    return (link, scoreDup)


dataset = [
    line.replace('"', "").rstrip().split("\t")
    for line in open("/tmp/demo.txt", "r").readlines()
]
orf = 3
fingerprintList = [10]
minDuplicateLength = 16

for texts in dataset:
    print(texts)

    fingerprintBuilder = FingerprintBuilder(fingerprintList, orf)
    duplicateFinder = DuplicateFinder(
        fingerprintBuilder, minDuplicateLength=minDuplicateLength
    )

    for i, text in enumerate(texts):
        name = f"D{i}"
        duplicates = duplicateFinder.findDuplicates(name, text)
        if i == 0:
            continue
        print("Duplicates")
        print(duplicates)
        link, thisScore = generateLink(duplicates, name)

        print("finish a sentence")
        print(link)
        for el in link:
            thisexp = el.split(",")
            print(texts[0][int(thisexp[1]) : int(thisexp[2])])
            print(texts[1][int(thisexp[4]) : int(thisexp[5])])
            print("**********")
