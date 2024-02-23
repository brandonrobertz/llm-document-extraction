#!/usr/bin/env python
"""
Extract JSON records from text documents using LLMs.
"""
import argparse
from datetime import datetime
import json
import os
import re
import sys
import time

from llama_cpp import Llama


# max chars to use in prompt
N_GPU_LAYERS=-1
CONTEXT_SIZE=4096
RESPONSE_TOKENS=1024


parser = argparse.ArgumentParser(
    description='Extract structured data from text using an LLM.'
)
parser.add_argument(
    '--model', 
    help='Path to the LLM model to use, should be compatible with llama.cpp'
)
parser.add_argument(
    '--n_gpu', 
    default=N_GPU_LAYERS,
    help='How many GPU layers to use (see llama.cpp for information about this setting)'
)
parser.add_argument(
    '--n_ctx', 
    default=CONTEXT_SIZE,
    help='Model context size'
)
parser.add_argument(
    '--n_tokens', 
    default=RESPONSE_TOKENS,
    help='Max number of output tokens the model can output (eats into context size)'
)
parser.add_argument(
    '--keydoc', 
    default="text",
    help='If using JSON input type, this is the key of the document text'
)
parser.add_argument(
    '--keyid', 
    default="pg",
    help='If using JSON input type, this is the key of the id/page no'
)
parser.add_argument(
    '--continue-from-outfile', 
    action="store_true",
    help='If set, parse the output file (if it exists) and continue where it left off'
)
parser.add_argument(
    'infile',
    help='Input JSON file'
)
parser.add_argument(
    'schema_file',
    help='Path to JSON Schema file'
)
parser.add_argument(
    'outfile',
    help='Path to output results JSON file'
)


def clean_document(llm, page_text):
    max_doc_size = CONTEXT_SIZE - RESPONSE_TOKENS
    cleaned = re.sub(
        r"[\t ]+", " ", re.sub(
            r"[\n]+", "\n", page_text, re.M
        ), re.M
    ).strip()
    # blank line removal, also remove any excessively long tokens
    cleaned = "\n".join([l for l in cleaned.split('\n') if l.strip() and len(l) < 100])
    print("cleaned doc length:", len(cleaned))
    trim_attempts = 0
    while len(llm.tokenize(bytes(cleaned, encoding="utf-8"))) > max_doc_size and trim_attempts < 200:
        trim_attempts += 1
        tokens = re.split(r"[\t ]+", cleaned)
        # remove tokens 200 chars from the end of the doc, upward. so that we
        # can capture a signature and any final statements but trim before that
        keep_end_tokens = 50
        front = tokens[:-keep_end_tokens - 5]
        end = tokens[-keep_end_tokens:]
        cleaned = " ".join(front + end)
        print("cleaned doc length tokens:", len(tokens), "chars:", len(cleaned))
    return cleaned


def load_model(model_path):
    # for LLaMA2 70B models add kwarg: n_gqa=8 (NOTE: not required for GGUF models)
    return Llama(
        model_path=model_path,
        n_ctx=CONTEXT_SIZE,
        n_gpu_layers=N_GPU_LAYERS,
        n_threads=os.cpu_count() - 1,
        verbose=False
    )


def execute(llm, prompt):
    print("=" * 72)
    print(f"Prompt ({len(prompt)} bytes)")
    print("-" * 72)
    peek_chrs = 1500
    print(prompt[:peek_chrs] + "..." if len(prompt) > peek_chrs else prompt)
    stream = llm(
        prompt,
        max_tokens=RESPONSE_TOKENS,
        stop=["```"],
        temperature=0,
        stream=True,
        echo=True
    )

    response = ""
    for token in stream:
        choice = token['choices'][0]
        response += choice["text"]
        if choice['finish_reason']:
            break

    print("-" * 72)
    print(f"Response ({len(response)}")
    print("-" * 72)
    print(response)
    print()
    return response


def scrape_via_prompt(llm, page_text, schema, examples=None):
    prompt = f"Document:\n```{clean_document(llm, page_text)}```\nJSON schema:\n```\n{schema}\n```\nA JSON representation of the text document above that follows the JSON schema is:\n```\n{{"
    response = execute(llm, prompt)
    return prompt, response


def upsert_result(results, result):
    pk = result["id"]
    for r_ix, r_result in enumerate(results):
        if r_result["id"] != pk:
            continue
        # overwrite
        results[r_ix] = result
        return
    # if we're here we did't update an existing result
    results.append(result)


def run(llm, documents, schema, outfile, continue_from_outfile=False):
    # restore outfile if it exists
    results = []
    if os.path.exists(outfile):
        with open(outfile, "r") as f:
            results = json.load(f)

    already_scraped = set([
        r.get("id") for r in results
    ])
    if already_scraped:
        print("Already scraped", already_scraped)

    for page_data in documents:
        pk = page_data["id"]
        if continue_from_outfile and pk in already_scraped:
            continue

        page_text = page_data["text"]
        if not page_text:
            print("Blank text for ID:", pk, "Skipping...")
            continue

        print("Doc ID:", pk, "Text length:", len(page_text))
        prompt, response = scrape_via_prompt(llm, page_text, schema)

        if response is None:
            print("Skipping page due to blank response")
            continue

        # NOTE: This is the same prefix as our continuation prompt
        try:
            data = json.loads(f"```\n{{{response}".split("```")[1])
        except json.decoder.JSONDecodeError:
            data = None

        result = {
            "id": pk,
            "text": page_text,
            "prompt": prompt,
            "response": response,
            "data": data,
            # save these then we can pass through again and try with larger
            # context sizes and things like that
            "llm_options": dict(
                model_path=llm.model_path,
                CONTEXT_SIZE=CONTEXT_SIZE,
                RESPONSE_TOKENS=RESPONSE_TOKENS
            ),

        }
        upsert_result(results, result)

        print("Saving results to", outfile)
        with open(outfile, "w") as f:
            f.write(json.dumps(results, indent=2))
        print("ID", pk, "complete")


def parse_input_documents(args):
    documents = []
    with open(args.infile, "r") as f:
        input_json = json.load(f)
        assert len(input_json), "Input JSON must not be blank!"
        type_err_msg = "Input JSON must be an array of objects"
        assert isinstance(input_json, list), type_err_msg
        assert isinstance(input_json[0], dict), type_err_msg
        assert args.keydoc in input_json[0], f"--keydoc '{args.keydoc}' not in JSON"
        for doc_data in input_json:
            documents.append({
                "id": doc_data[args.keyid],
                "text": doc_data[args.keydoc]
            })
    return documents


if __name__ == "__main__":
    args = parser.parse_args()

    documents = parse_input_documents(args)

    with open(args.schema_file, "r") as f:
        # make sure it's JSON
        schema = json.dumps(json.load(f))

    llm = load_model(args.model)
    run(llm, documents, schema, args.outfile, continue_from_outfile=args.continue_from_outfile)
