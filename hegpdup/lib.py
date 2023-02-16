from collections import Counter


def flat2gen(alist):
    for item in alist:
        if isinstance(item, list):
            for subitem in item:
                yield subitem
        else:
            yield item


def returnUniq(thisList):
    return list(set(thisList))


# Python program to illustrate the intersection
# of two lists using set() method
# https://www.geeksforgeeks.org/python-intersection-two-lists/


def intersection(lst1, lst2):
    return list(set(lst1) & set(lst2))


# https://stackoverflow.com/questions/7828867/how-to-efficiently-compare-two-unordered-lists-not-sets-in-python
# O(n): The Counter() method is best (if your objects are hashable):
def compareCounter(s, t):
    return Counter(s) == Counter(t)
