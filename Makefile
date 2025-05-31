images:
	docker compose --profile radio build
.PHONY: clean

clean:
	find . "(" -name build        \
	       -o  -name "*.egg-info" \
	       -o  -name dist         \
	       -o  -name node_modules \
	       -o  -name __pycache__  \
	       -o  -name venv         \
	       ")" -exec rm -rf "{}" +
.PHONY: clean
