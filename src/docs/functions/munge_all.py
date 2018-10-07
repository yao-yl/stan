#!/usr/bin/python

#  keeps track of chapter, section
#  finds all function definitions (latex tag 'fitem')
#  gets arguments, descriptions
#  writes sections, chapters, Rmd files
#  handles labels, xrefs

import os
import os.path
import re
import sys

rstudioOut = "rstudio_listing.txt"
rmdDir = "pages"
texfile = "preproc_all.tex"
labelsfile = "dict_xref_labels.txt"
labels_dict = {}

def main():
    if (not os.path.exists(rstudioOut)):
        fh1 = open(rstudioOut, 'w+')
        fh1.close()

    read_xrefs(labelsfile)
        
    if not os.path.isfile(texfile):
        print("File {} does not exist. Exiting...".format(texfile))
        sys.exit()
    
    chapterName = ""
    chapterNum = 0
    chapterRmd = ""
    sectionName = ""
    sectionNum = 0
    sectionRmd = ""
    curFn = ""

    with open(texfile) as fp:
        for line in fp:
            line = line.strip()
            if (len(line) == 0):
                continue
            if (line.startswith("\\part")):
                process_part(line)
            elif (line.startswith("\\chapter")):
                chapterName = get_name(line.strip())
                chapterNum += 1
                sectionName = ""
                sectionNum = 0
                sectionRmd = ""
                curFn = ""
                chapterRmd = chapter_rmd_page(chapterName, chapterNum)
            elif (line.startswith("\\section")):
                sectionName = get_name(line.strip())
                sectionNum += 1
                sectionRmd = section_rmd_page(sectionName, sectionNum, chapterName, chapterNum)
                process_section(chapterNum, sectionNum, sectionName, chapterRmd)
                curFn = ""
            elif(line.startswith("\\begin{description}")):
                curFn = process_description(curFn, line, chapterName, sectionName, chapterNum, sectionNum)
            elif (line.startswith("\\sub")):
                process_subsection(line, sectionRmd)
                curFn = ""
            else:
                if (len(sectionRmd) > 0):
                    process_line(line, sectionRmd)
                elif (len(chapterRmd) > 0):
                    process_line(line, chapterRmd)
    fp.close()


def process_description(curFn, line, chapterName, sectionName, chapterNum, sectionNum):
    rmdPath = section_rmd_page(sectionName, sectionNum, chapterName, chapterNum)
    line = remove_tags(line, "farg")
    line = remove_tags(line, "mbox")
    line = munge_code(line)
    items = line.strip().split("\\fitem")
    for item in items:
        if (item.startswith("\\begin")):
            continue
        else:
            numLines = 1
            if (item.startswith("two")):
                numLines = 2
            elif (item.startswith("three")):
                numLines = 3
            elif (item.startswith("four")):
                numLines = 4
            elif (item.startswith("Unary")):
                open1 = item.find("{")
                close = item.find("}")
                open2 = item.find("{",close)
                name = item[open1 : close + 1]
                rest = item[close : len(item)]
                item = "{R}" + name + "{T x}" + rest
            endIdx = item.find("\\end{description}")
            if (endIdx > 0):
                item = item[0 : endIdx]
            item = ' '.join(item.split())
            item_dict = process_item(item, numLines)
            if (item_dict["name"] != curFn):
                curFn = item_dict["name"]
                fh = open(rmdPath, 'a')
                fh.write("\n__%s__\n\n" % item_dict["name"])
                fh.close()
            write_item(item_dict, rmdPath)
    return curFn
    
def process_item(item, numLines):
    curIdx = 0
    openBrace = str.find(item, "{", curIdx)
    if (openBrace < 0):
        print "ERROR parsing return type: ", item
        return
    closeBrace = str.find(item, "}", openBrace+1)
    if (closeBrace < 0):
        print "ERROR parsing return type: ", item
        return
    return_type = item[openBrace+1 : closeBrace]

    # get name
    curIdx = closeBrace
    openBrace = str.find(item, "{", curIdx)
    if (openBrace < 0):
        print "ERROR parsing name: ", item
        return
    closeBrace = str.find(item, "}", openBrace+1)
    if (closeBrace < 0):
        print "ERROR parsing name: ", item
        return
    fn_name = item[openBrace+1 : closeBrace]
    item_name = clean(str.lower(fn_name).replace(" ","_"))

    # get args
    argsAll = ""
    for x in range(0, numLines):
        curIdx = closeBrace
        openBrace = str.find(item, "{", curIdx)
        if (openBrace < 0):
            print "ERROR parsing args: ", item
            return
        closeBrace = match_close(item, openBrace+1)
        if (closeBrace < 0):
            print "ERROR parsing args: ", item
            return
        args = item[openBrace+1 : closeBrace]
        argsAll += args
        if (x < numLines - 1):
            argsAll += ", "
    
    # get decscription
    desc = ""
    curIdx = closeBrace
    openBrace = str.find(item, "{", curIdx)
    if (openBrace > 0):
        closeBrace = match_close(item, openBrace+1)
    if (openBrace > 0 and closeBrace > 0):
        desc = item[openBrace+1 : closeBrace]

    return {"name":item_name,
            "fn_name":fn_name,
            "return_type":return_type,
            "args":argsAll,
            "description":desc}

def process_section(one, two, name, rmdPath):
    display_name = '.'.join([str(one), str(two)])
    display_name = ' '.join([display_name, name])
    page_name = clean(str.lower(name).replace(" ","-"))
    page_name = page_name.replace("(","")
    page_name = page_name.replace(")","")
    page_name += ".html"
    fh = open(rmdPath, 'a')
    fh.write("\n```{asis, echo=is_html_output()}\n")
    fh.write("<a href=\"%s\"><b style=\"font-size: 110%%; color:#990017;\">%s</b></a>\n" % (page_name, display_name))
    fh.write("```\n\n")
    fh.close()

def process_subsection(line, rmdPath):
    start = line.find("{")
    end = line.find("}",start)
    tag = line[0:start]
    ct = tag.count("sub") + 2
    name = line[start+1:end]
    fh = open(rmdPath, 'a')
    fh.write("\n")
    fh.write(line)
    fh.write("\n```{asis, echo=is_html_output()}\n")
    fh.write("<i style=\"font-size: 110%%; color:#800013;\"> %s</i>\n" % name)
    fh.write("```\n\n")
    fh.close()

def process_line(line, curPage):
    if line.startswith("```"): # stan code
        lines = line.split("\\n")
        line = '\n'.join(lines)
    else:
        line = remove_tags(line, "farg")
        line = munge_code(line)
    fh = open(curPage, 'a')
    if line.startswith("|"):  # table
        fh.write("%s\n" % line) 
    else:                     # paragraph
        fh.write("%s\n\n" % line)  
    fh.close()

def process_part(line):
    part = get_name(line)
    rmdFile = ''.join([str.lower(part).replace(" ","_"), ".Rmd"])
    rmdPath = os.path.join(rmdDir, rmdFile)
    if (not os.path.exists(rmdPath)):
        fh = open(rmdPath, 'w+')
        fh.write("# <i style=\"font-size: 110%; padding:1.5em 0 0 0; color:#990017;\">")
        fh.write(part)
        fh.write("</i> {-}\n")
        fh.close()
    print rmdPath
    
def chapter_rmd_page(chapterName, chapterNum):
    rmdFile = ''.join(["chp_", str(chapterNum), ".Rmd"])
    if (not os.path.exists(rmdDir)):
        os.makedirs(rmdDir)
    rmdPath = os.path.join(rmdDir, rmdFile)
    if (not os.path.exists(rmdPath)):
        fh = open(rmdPath, 'w+')
        fh.write("# %s\n\n" % chapterName)
        fh.close()
        print rmdPath
    return rmdPath

def section_rmd_page(sectionName, sectionNum, chapterName, chapterNum):
    section = str.lower(sectionName).replace(" ","_")
    section = section.replace("(","")
    section = section.replace(")","")
    section = section.replace(",","")
    rmdFile = ''.join(["sec_", str(chapterNum), "_", str(sectionNum), "_", section, ".Rmd"])
    if (not os.path.exists(rmdDir)):
        os.makedirs(rmdDir)
    rmdPath = os.path.join(rmdDir, rmdFile)
    if (not os.path.exists(rmdPath)):
        fh = open(rmdPath, 'w+')
        fh.write("## %s\n\n" % sectionName)
        fh.close()
        print rmdPath
    return rmdPath

def write_item(item_dict, rmdPath):
    fh = open(rstudioOut, 'a')
    fh.write("`%s`; `%s`; (`%s`); %s\n" % (item_dict["return_type"], item_dict["fn_name"], item_dict["args"], item_dict["description"]))
    fh.write("\n")
    fh.close()
    fh = open(rmdPath, 'a')
    fh.write("`%s` __`%s`__(`%s`)  \n%s\n" % (item_dict["return_type"], item_dict["fn_name"], item_dict["args"], item_dict["description"]))
    fh.write("\n")
    fh.close()


def munge_code(line):
    p = re.compile("\code{")
    while True:
        if re.search(p, line):
            line = code2backtick(line)
        else:
            break
    return line

def code2backtick(text):
    start = str.find(text, "\code{")
    if (start < 0):
        return text
    end = match_close(text, start+6)
    if (end < 0):
        return text
    if (end == len(text)):
        return text[0 : start] + "`" + text[start + 6 : end] + "`"
    else:
        return text[0 : start] + "`" + text[start + 6 : end] + "`" + text[end+1 : len(text)]        

def remove_tags(text, tag):
    pat = ''.join(["\\\\",tag,"{"])
    while True:
        if re.search(pat, text):
            text = remove_tag(text, tag)
        else:
            break
    return text

def remove_tag(text, tag):
    pat = ''.join(['\\',tag,'{'])
    start = str.find(text, pat)
    if (start < 0):
        return text
    end = match_close(text, start+len(tag)+3)
    if (end < 0):
        return text
    return text[0 : start] + text[start + len(tag) + 2 : end] + text[end+1 : len(text)]


def match_close(item, startIdx):
    level = 0
    for x in range(startIdx, len(item)):
        if item[x] == '{':
            level += 1
        elif item[x] == '}':
            if (level == 0):
                return x
            else:
                level -= 1
    return -1

def get_name(line):
    p = re.compile('\{[^}]*')
    name = p.search(line).group()
    return name[1 : len(name)]

def clean(name):
    if (name.endswith("_cdf")):
        return name[0:(len(name)-4)]
    if (name.endswith("_lccdf")):
        return name[0:(len(name)-6)]
    if (name.endswith("_lcdf")):
        return name[0:(len(name)-5)]
    if (name.endswith("_lpdf")):
        return name[0:(len(name)-5)]
    if (name.endswith("_lpmf")):
        return name[0:(len(name)-5)]
    if (name.endswith("_rng")):
        return name[0:(len(name)-4)]
    if (not name.startswith("operator")):
        return name
    name = name.replace("==","_logial_equal")
    name = name.replace("!=","_logical_not_equal")
    name = name.replace("!","_negation")
    name = name.replace("<=","_logical_less_than_equal")
    name = name.replace("<","_logical_less_than")
    name = name.replace(">=","_logical_greater_than_equal")
    name = name.replace(">","_logical_greater_than")
    name = name.replace("&&","_logical_and")
    name = name.replace("||","_logical_or")
    if (name.endswith("=")):
        name = name.replace("operator","operator_compound")
        name = name[0 : len(name) - 1]
    name = name.replace("^","_pow")
    name = name.replace("%","_mod")
    name = name.replace("'","_transpose")
    name = name.replace(".","_elt")
    name = name.replace("*","_multiply")
    name = name.replace("/","_divide")
    name = name.replace("+","_add")
    name = name.replace("-","_subtract")
    name = name.replace("\\","_left_div")
    return name

def read_xrefs(labelsfile):
    if not os.path.isfile(labelsfile):
        print("File {} does not exist. Exiting...".format(labelsfile))
        sys.exit()
    with open(labelsfile, 'r') as fp:
        for line in fp:
            line = line.strip()
            if (len(line) == 0):
                continue
            items = line.split(":")
            key, values = items[0].strip(), items[1].strip()
            labels_dict[key] = values
    fp.close()

if __name__ == '__main__':  
    main()
