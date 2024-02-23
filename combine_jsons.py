#!/usr/bin/env python
import json
import os
import sys

import sqlite_utils
import tablib


if __name__ == "__main__":
    try:
        infolder = sys.argv[1]
        outfile = sys.argv[2]
    except IndexError:
        print("USAGE: combine_jsons.py path/to/jsons/ [ path/to/output.db | path/to/output.csv ]")
        sys.exit(1)

    print("Parsing JSONs in folder", infolder)
    all_records = []
    all_keys = set()
    for basedir, subdirs, files in os.walk(infolder):
        for file in files:
            if not file.endswith(".json"):
                continue
            json_file = os.path.join(basedir, file)
            print("Parsing", json_file)
            with open(json_file, "r") as f:
                file_records = json.load(f)
                for i, record in enumerate(file_records):
                    print("Parsing", json_file, "record no", i, end="\r")
                    if "response" not in record:
                        continue
                    response = record["response"].strip()
                    if not response.startswith("{"):
                        response = "{" + response
                    try:
                        response_dict = json.loads(response)
                    except json.JSONDecodeError:
                        continue
                    all_records.append(response_dict)
                    all_keys.update(response_dict.keys())

    if outfile.endswith(".db"):
        print("Building DB", outfile)
        db = sqlite_utils.Database(outfile)
        for rec in all_records:
            db["records"].upsert(rec, pk="pk", alter=True)
    elif outfile.endswith(".csv"):
        print("Building CSV", outfile)
        csv = tablib.Dataset(headers=list(all_keys))
        for rec in all_records:
            row = []
            for key in all_keys:
                row.append(rec.get(key))
            csv.append(row)
        with open(outfile, "w") as f:
            f.write(csv.csv)
