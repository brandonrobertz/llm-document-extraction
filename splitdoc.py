#!/usr/bin/env python
import json
import sys
import re


new_page_identifiers = {
    "FOIL G000569-102422",
}


new_record_identifiers = {
    "OFFICE OF THE ATTORNEY GENERAL LETITIA JAMES": {
        "pages": 2,
    },
    "NEW YORK STATE SECURITY BREACH REPORTING FORM": {
        "pages": 2,
    },
    "RE: NOTICE OF DATA BREACH": {},
    "NOTICE OF DATA BREACH": {},
    "Notification of Data Breach": {},
    "Notice of Data Security Incident": {},
    # least specific
    "inform you of an incident": {},
    "information may have been compromised": {}
}


def line_matches(line, identifiers):
    for str_match in identifiers:
        escape_spaces = re.sub(r'\s+', r"\\s+", str_match)
        re_match = re.compile(f".*{escape_spaces}.*", re.I)
        if re.match(re_match, line):
            return str_match


def text_to_pages(infile):
    pages = []
    with open(infile, "r") as f:
        for i, line in enumerate(f.readlines()):
            if not i % 1000:
                print("Parsing line:", i, end="\r")
            if not pages:
                pages.append(line)
                continue
            pages[-1] += f"{line}\n"
            if line_matches(line, new_page_identifiers):
                pages.append("")
    print()
    final_pages = [p.strip() for p in pages if p.strip()]
    print(f"Built {len(final_pages)} pages")
    return final_pages


def group_pages_to_records(pages):
    print(f"Building records from {len(pages)} pages")
    page_groups = []
    record_ids = new_record_identifiers.keys()
    grab_pages = 0
    for pg_i, page in enumerate(pages):
        if pg_i % 100:
            print(pg_i, end="\r")
        if not page_groups:
            page_groups.append({
                "text": page,
                "pg": pg_i + 1,
            })
            continue
        record_match = line_matches(page, record_ids)
        if grab_pages > 0:
            grab_pages -= 1
        if record_match:
            record_data = new_record_identifiers[record_match]
            page_groups.append({
                "text": "",
                "pg": pg_i + 1,
            })
        page_groups[-1]["text"] += f"{page}\n"
        if grab_pages == 1:
            page_groups.append({
                "text": "",
                "pg": pg_i + 1,
            })
    print(f"Built {len(page_groups)} records")
    return page_groups


if __name__ =="__main__":
    try:
        infile = sys.argv[1]
        outfile = sys.argv[2]
    except IndexError:
        sys.exit("USAGE: splitdoc.py infile.txt outfile.json")

    pages = text_to_pages(infile)
    # print("==================================================")
    # print("Page 1")
    # print("--------------------------------------------------")
    # print(pages[0])
    # print()
    # print("==================================================")
    # print("Page 2")
    # print("--------------------------------------------------")
    # print(pages[1])
    # print()
    # print("==================================================")
    # print("Last Page")
    # print("--------------------------------------------------")
    # print(pages[-1])
    # print()

    page_groups = group_pages_to_records(pages)
    # print("==================================================")
    # print("Record 1")
    # print("--------------------------------------------------")
    # print(page_groups[0])
    # print()
    # print("==================================================")
    # print("Last Record")
    # print("--------------------------------------------------")
    # print(page_groups[-1])
    # print()

    with open(outfile, "w") as f:
        f.write(json.dumps(page_groups))
