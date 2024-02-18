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

