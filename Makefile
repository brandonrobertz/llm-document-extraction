DECRYPT_DIR = data/decrypted
DECRYPT_PDF_FILES = $(wildcard $(DECRYPT_DIR)/*.pdf)
PAGE_JSON_DIR = data/page_json
PAGE_JSON_FILES = $(patsubst $(DECRYPT_DIR)/%.pdf, $(PAGE_JSON_DIR)/%.jsonl, $(DECRYPT_PDF_FILES))

all: data/pdf data/decrypted $(PAGE_JSON_FILES)

data/pdf:
	curl 'https://www.muckrock.com/foi/new-york-16/untitled-office-of-the-attorney-general-new-york-135508/#files' > data/data_pdf_muckrock.html
	htmlext -i data/data_pdf_muckrock.html -x muckrock_pdfs.hext --compact \
		| jq -cr '.href' \
		| xargs -I{} wget -N '{}' -P $@

$(DECRYPT_DIR):
	mkdir -p $@
	find ./data/pdf/ -iname '*.pdf' -exec basename {} \; \
		| xargs -I{} qpdf --decrypt "data/pdf/{}" "data/decrypted/{}"

$(PAGE_JSON_DIR)/%.jsonl: $(DECRYPT_DIR)/%.pdf
	@mkdir -p data/page_json
	python florence-ocr/process_pdf.py $< | tee $@

data/records:
	mkdir -p $@
	find ./data/text/ -iname '*.txt' -exec basename {} \; \
		| xargs -I{} sh -c 'python splitdoc.py "data/text/{}" "data/records/{}.json"'

data/records_json:
	mkdir -p $@
	find data/records/ -iname '*.json' -exec basename {} \; \
		| xargs -I{} sh -c 'python ./llm_extract.py --continue-from-outfile --model ../llama/models/mistral-7b-v0.1.Q5_K_M.gguf "data/records/{}" "data/records_json/{}.records.json"'
