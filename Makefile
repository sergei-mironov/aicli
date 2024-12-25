.DEFAULT_GOAL = all
VERSION = $(shell python3 setup.py --version 2>/dev/null)
WHEEL = dist/sm_aicli-$(VERSION)-py3-none-any.whl
PY = $(shell find setup.py python -name '*\.py' -or -name 'aicli' | grep -v semver.py | grep -v revision.py)
TEST = sh/runtests.sh

.PHONY: help # Print help
help:
	@echo Build targets:
	@cat Makefile | sed -n 's@^.PHONY: \([a-z]\+\) # \(.*\)@    \1:   \2@p' | column -t -l2

$(WHEEL): $(PY) Makefile .stamp_readme
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
	cat _README.md.in | litrepl \
		--foreground --exception-exitcode=100 --sh-interpreter=- \
		eval-sections >README.md
	touch $@

.PHONY: test # Run tests
test: .stamp_test
.stamp_test: $(PY) $(TEST) Makefile
	$(TEST)
	touch $@

.PHONY: readme # Update code sections in the README.md
readme: .stamp_readme

.PHONY: upload # Upload wheel to Pypi.org (./_token.pypi is required)
upload: $(WHEEL)
	twine upload \
		--username __token__ \
		--password $(shell cat _token.pypi) \
		dist/*

.PHONY: all
all: wheel

