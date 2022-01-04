import sys
from collections import defaultdict as d
import re
from optparse import OptionParser, OptionGroup
import math
import gzip

# Author: Martin Kapun

# version 1.0 # 27/06/18

#########################################################   HELP   #########################################################################
usage = "python %prog --mpileup data.mpileup --base-quality-threshold 25 > output.sync"
parser = OptionParser(usage=usage)
helptext = """

H E L P :
_________
"""
group = OptionGroup(parser, helptext)
#########################################################   parameters   #########################################################################

parser.add_option("--mpileup", dest="m", help="A mpileup file")
parser.add_option(
    "--base-quality-threshold", dest="b", help="The Base-quality threshold ", default=15
)
parser.add_option(
    "--coding", dest="c", help="the Illumina FASTQ quality coding", default=1.8
)


parser.add_option_group(group)
(options, args) = parser.parse_args()


################################### functions ######################################


def load_data(x):
    """ import data either from a gzipped or or uncrompessed file or from STDIN"""
    import gzip

    if x == "-":
        y = sys.stdin
    elif x.endswith(".gz"):
        y = gzip.open(x, "rt", encoding="latin-1")
    else:
        y = open(x, "r", encoding="latin-1")
    return y


def keywithmaxvalue(d):
    """ This function resturns the key for the maximum value in a dictionary"""
    newhash = d(list)
    for k, v in d.items():
        newhash[v].append(k)
    return newhash[max(newhash.keys())]


def splitter(l, n):
    """ This generator function returns equally sized cunks of an list"""
    # credit: Meric Lieberman, 2012
    i = 0
    chunk = l[:n]
    while chunk:
        yield chunk
        i += n
        chunk = l[i: i + n]


def extract_indel(l, sign):
    """ This function returns an Indel from a sequence string in a pileup"""
    position = l.index(sign)
    numb = ""
    i = 0
    while True:
        if l[position + 1 + i].isdigit():
            numb += l[position + 1 + i]
            i += 1
        else:
            break

    seqlength = int(numb)
    sequence = l[position: position + i + 1 + seqlength]
    indel = sequence.replace(numb, "")

    return sequence, indel


def counth2sync(x):
    """ convert countHash to sync """
    counts = []
    for y in ["A", "T", "C", "G", "N", "D"]:
        if y in x:
            counts.append(x[y])
        else:
            counts.append(0)
    return ":".join([str(x) for x in counts])


################################## parameters ########################################


data = options.m
baseqthreshold = int(options.b)
phred = float(options.c)

############################ calculate PHRED cutoff  #############################

# calculate correct PHRED score cutoff: ASCII-pc

if phred >= 1.0 and phred < 1.8:
    pc = 64
else:
    pc = 33

############################ parse MPILEUP ###########################################

# parse mpileup and store alternative alleles:

for line in load_data(data):
    if len(line.split("\t")) < 2:
        continue

    k = line[:-1].split("\t")
    CHR, POS, REF = k[:3]

    div = list(splitter(k, 3))
    libraries = div[1:]
    # loop through libraries

    alleles = d(lambda: d(int))

    for j in range(len(libraries)):
        alleles[j]
        nuc = libraries[j][1]
        qualities = libraries[j][2]

        # test if seq-string is empty
        if nuc == "*":
            continue

        # find and remove read indices and mapping quality string
        nuc = re.sub(r"\^.", r"", nuc)
        nuc = nuc.replace("$", "")
        cov = 0

        # find and remove InDels
        while "+" in nuc or "-" in nuc:
            if "+" in nuc:
                insertion, ins = extract_indel(nuc, "+")
                nuc = nuc.replace(insertion, "")
            else:
                deletion, dele = extract_indel(nuc, "-")
                nuc = nuc.replace(deletion, "")

        # test for base quality threshold (if below: ignore nucleotide)
        # print len(nuc),len(qualities)
        nuc = "".join(
            [
                nuc[x]
                for x in range(len(nuc))
                if ord(qualities[x]) - pc >= baseqthreshold
            ]
        )
        nuc = "".join([nuc[x] for x in range(len(nuc)) if nuc[x] != "*"])

        # read all alleles
        for i in range(len(nuc)):

            # ignore single nucleotide deletions
            if nuc[i] == "*":
                continue
            # count nucleotides similar to reference base
            if nuc[i] == "," or nuc[i] == ".":
                alleles[j][REF] += 1
                continue
            # count alternative nucleotides
            alleles[j][nuc[i].upper()] += 1
    syncL = []
    for k, v in sorted(alleles.items()):
        syncL.append(counth2sync(v))

    # write output
    print(CHR + "\t" + POS + "\t" + REF + "\t" + "\t".join(syncL))
