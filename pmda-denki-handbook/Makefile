all:
	asciidoctor-pdf -a toc -v denki.md
	asciidoctor -b html5 -a toc2 -n denki.md

old: 
	# asciidoc -b html5 -a icons -a toc2 -a theme=flask japan.ascii
	# asciidoc -b xhtml11 -a icons -a toc2 -a theme=flask japan.ascii
	# asciidoc -b xhtml11 -a icons -a toc2 -a theme=flask-chorn -n japan.ascii
	# asciidoc -b html5 -a icons -a toc2 -n denki.md
	asciidoc -b xhtml11 -a icons -a toc2 -a theme=flask-chorn -n denki.md
	# fixing img links
	sed -i 's,img src\(.*\)>,img src\1 loading="lazy" decoding="async">,' denki.html
