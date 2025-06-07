images:
	docker compose --profile radio build
.PHONY: clean

test:
	cd aggregator && $(MAKE) test
.PHONY: test

clean:
	find . "(" -name build        \
	       -o  -name "*.egg-info" \
	       -o  -name dist         \
	       -o  -name node_modules \
	       -o  -name __pycache__  \
	       -o  -name venv         \
	       ")" -exec rm -rf "{}" +
.PHONY: clean
