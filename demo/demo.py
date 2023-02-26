from pathlib import Path
import json

from hegpdup import FingerprintBuilder, DuplicateFinder


orf = 3
fingerprintLength = 15
minDuplicateLength = 15

with open(Path(__file__).parent / "data.json") as fp:
    examples = json.load(fp)

for texts in examples:
    print("************")

    # init FingerprintBuilder and DuplicateFinder that will process a batch of documents
    fingerprintBuilder = FingerprintBuilder(fingerprintLength, orf)
    duplicateFinder = DuplicateFinder(fingerprintBuilder, minDuplicateLength)

    for i, text in enumerate(texts):
        id = f"D{i}"
        print("\nDOCUMENT: " + id)
        print(text)

        # call findDuplicates() on each document from older to newer
        duplicates = duplicateFinder.findDuplicates(id, text)

        if i == 0:
            continue

        print("\nDUPLICATES:")
        for duplicate in duplicates:
            print(
                f"\tsourceDoc={duplicate.sourceDocId}, sourceStart={duplicate.sourceSpan.start}, sourceEnd={duplicate.sourceSpan.end}, "
                f"targetStart={duplicate.targetSpan.start}, targetEnd={duplicate.targetSpan.end}"
            )
            duplicate_text = text[duplicate.targetSpan.start : duplicate.targetSpan.end]
            print(f"\ttext=" + repr(duplicate_text), end="\n\n")
