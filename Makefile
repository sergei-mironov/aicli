.DEFAULT_GOAL = all
VERSION = $(shell python3 setup.py --version 2>/dev/null)
WHEEL = dist/gpt4all_cli-$(VERSION)-py3-none-any.whl
PY = $(shell find -name '*\.py' | grep -v semver.py | grep -v revision.py)
TESTS = ./sh/test.sh

# .stamp_test: $(PY) $(VIM) $(TESTS) Makefile python/bin/litrepl
# 	LITREPL_BIN="`pwd`/python/bin" \
# 	LITREPL_ROOT=`pwd` \
# 	sh ./sh/test.sh
# 	touch $@

.PHONY: help # Print help
help:
	@echo Build targets:
	@cat Makefile | sed -n 's@^.PHONY: \([a-z]\+\) # \(.*\)@    \1:   \2@p' | column -t -l2

$(WHEEL): $(PY) Makefile
	test -n "$(VERSION)"
	rm -rf build dist || true
	python3 setup.py sdist bdist_wheel
	test -f $@

.PHONY: wheel # Build Python wheel (the DEFAULT target)
wheel: $(WHEEL)

.PHONY: version # Print the version
version:
	@echo $(VERSION)

.stamp_readme: $(PY)
	cp README.md _README.md.in
	cat _README.md.in | litrepl --foreground --exception-exit=100 eval-sections >README.md
	touch $@

.PHONY: readme # Update code sections in the README.md
readme: .stamp_readme

.PHONY: upload # Upload wheel to Pypi.org (./_token.pypi is required)
upload: $(WHEEL) .stamp_readme
	twine upload \
		--username __token__ \
		--password $(shell cat _token.pypi) \
		dist/*

.PHONY: all
all: wheel

