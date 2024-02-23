# LLM Document Extraction

This is a proof of concept tool for transforming messy text documents into structured data using local large language models (LLMs) and JSON schema.

This only has one requirement: [llama-cpp-py](https://github.com/abetlen/llama-cpp-python)

## Quickstart

You need to install the python dependency: `pip install -r requirements.txt`

Then you need to do a few things:

1. Download a GGUF model you'll use. Perhaps [Mixtral 8x7B](https://huggingface.co/TheBloke/Mixtral-8x7B-v0.1-GGUF)?
2. Split your source text file into individual records. You can use the `splitdoc.py` script to help do that.
3. Create a JSON schema describing the fields you'd like the model to extract from each text record. You can see an example in `schema.json`

Once you've done this, then you simply need to transform each record into a JSON record, using the `llm_extract.py` script.

```
./llm_extract.py --model ../llama/models/mistral-7b-v0.1.Q5_K_M.gguf data/records/document_1.json data/records_json/document_1.records.json
```

This will iterate over each record inside `document_1.json`, ask the LLM to extract a record matching the JSON schema in `schema.json` and write it out to `document_1.records.json`.

You can see a full example pipeline of how I've turned a PDF into structured data in the `Makefile` as well.

## Caveats

This will trim any text records that are longer than the context length specified (via `--n_ctx`). If your documents are too long try a model capable of larger context or manually truncate them yourself. The default strategy will trim from the end, leaving the last 50 tokens.

The prompt is baked into the `llm_extract.py` script and is oriented toward completion models. If you want to use instruct models or models that require a specific format you'll need to change the prompt yourself.

Some models are better at this kind of task than others. If you aren't getting the results you want try something else. You may also get better results by giving an example. The current prompt is one shot learning. An example can help your model learn how to extract details from your specific text, but can also cause errors (e.g., the model starts to repeat the example rather than pull from the document).
