mkdir -p pdfs && find . -path ./pdfs -prune -o -name '*.pdf' -exec mv {} pdfs/ \; && find . -depth -type d -empty -delete
