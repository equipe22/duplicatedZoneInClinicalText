import pickle
import os
import hashlib

from collections import Counter

def setOnDict(thisDict):
    return([dict(a) for a in set([tuple(b.items()) for b in thisDict])])


def flat2gen(alist):
    for item in alist:
        if isinstance(item, list):
            for subitem in item: yield subitem
        else:
            yield item

def createHash(toHash):
    hash_object = hashlib.md5(toHash.replace("|"," ").encode())
    return(hash_object.hexdigest())


def returnUniq(thisList):
    return(list(set(thisList)))


def deleteInList(thisList, toDelete):
    if toDelete in thisList:
        indice = thisList.index(toDelete)
        del thisList[indice]
    return(thisList)


def sortBy(thisList, sortByPosition):
    thisList.sort(key=lambda tup: tup[sortByPosition])
    return(thisList)


def saveObject(thisObject, fileName):
    outfile = open(fileName, 'wb')
    pickle.dump(thisObject, outfile)
    outfile.close()


def loadObject(fileName):
    inputfile = open(fileName, 'rb')
    thisObject = pickle.load(inputfile)
    inputfile.close()
    return(thisObject)
# Python program to illustrate the intersection
# of two lists using set() method
# https://www.geeksforgeeks.org/python-intersection-two-lists/


def intersection(lst1, lst2):
    return list(set(lst1) & set(lst2))

# https://stackoverflow.com/questions/7828867/how-to-efficiently-compare-two-unordered-lists-not-sets-in-python
# O(n): The Counter() method is best (if your objects are hashable):
def compareCounter(s, t):
    return Counter(s) == Counter(t)


# O(n log n): The sorted() method is next best (if your objects are orderable):
def compareSorted(s, t):
    return sorted(s) == sorted(t)


def returnPattern(filePath, start, end):
        thispattern = "".join(open(os.path.normpath(filePath), 'r').readlines()
                              )[start:end]
        return(thispattern)


def mean(numbers):
    """
    mean(numbers)
    returns (mean)

    **Descriptions**:

    This function aims to return a mean of a list

    **Parameters**:

    :param numbers: a list of number
    :type numbers: list
    :returns: mean
    :rtype: float
    """
    return(float(sum(numbers)) / max(len(numbers), 1))
