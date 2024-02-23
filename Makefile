data/decrypted:
	mkdir -p $@
	find ./data/pdf/ -iname '*.pdf' -exec basename {} \; \
		| xargs -I{} qpdf --decrypt "data/pdf/{}" "data/decrypted/{}"

data/text:
	mkdir -p $@
	find ./data/decrypted/ -iname '*.pdf' -exec basename {} \; \
		| xargs -I{} sh -c 'pdfplumber --format text "data/decrypted/{}" > "data/text/{}.txt"'

data/records:
	mkdir -p $@
	find ./data/text/ -iname '*.txt' -exec basename {} \; \
		| xargs -I{} sh -c 'python splitdoc.py "data/text/{}" "data/records/{}.json"'


data/records_json:
	mkdir -p $@
	find data/records/ -iname '*.json' -exec basename {} \; \
		| xargs -I{} sh -c 'python ./llm_extract.py --continue-from-outfile --model ../llama/models/mistral-7b-v0.1.Q5_K_M.gguf "data/records/{}" "data/records_json/{}.records.json"'
