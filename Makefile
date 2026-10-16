# ks-kuzuha-alternative
#
#   make dist          build build/ks-kuzuha-alternative-<version>.zip (+ .sha256)
#   make smoke         extract that zip into docker php:7.4-apache, browser check
#   make smoke-full    same, plus reply / delete / search / tag filter / settings
#   make deploy-demo   build with config/demo.json and upload bbs/ to DEPLOY_HOST
#
# `make.local` (gitignored) holds local settings:
#   SRC_FLAGS   = --src ks-sw-api=../ks-sw-api --src ks-kuzuha-ui=../ks-kuzuha-ui
#                 (while the component repos are private: clone from local repos)
#   DEPLOY_HOST = ftp://user@ftp.example.com   (lftp URL; or user@host with DEPLOY_METHOD=rsync)
#   DEPLOY_PATH = public_html/bbs
-include make.local

.PHONY: help dist smoke smoke-full demo deploy-demo clean

PYTHON     ?= python3
# Python + playwright for the browser checks (Chromium: `playwright install chromium`).
PLAYWRIGHT ?= uv run --no-project --with playwright==1.64.0 python
SRC_FLAGS  ?=
VERSION    := $(shell sed -n 's/^version = "\(.*\)"/\1/p' dist/php-min.toml)
ZIP        := build/ks-kuzuha-alternative-$(VERSION).zip
DEMO_ZIP   := build/ks-kuzuha-alternative-$(VERSION)-demo.zip

DEPLOY_HOST   ?=
DEPLOY_PATH   ?=
DEPLOY_METHOD ?= lftp

help:
	@sed -n '3,7p' Makefile

dist:
	$(PYTHON) dist/build.py $(SRC_FLAGS)

$(ZIP):
	$(MAKE) dist

smoke: $(ZIP)
	$(PLAYWRIGHT) tests/smoke/run.py $(ZIP)

smoke-full: $(ZIP)
	$(PLAYWRIGHT) tests/smoke/run.py $(ZIP) --full

demo:
	$(PYTHON) dist/build.py $(SRC_FLAGS) --site-config config/demo.json --suffix demo

DEMO_BBS := build/stage/ks-kuzuha-alternative-$(VERSION)-demo/ks-kuzuha-alternative-$(VERSION)/bbs

# Uploads the demo build's bbs/ to DEPLOY_HOST:DEPLOY_PATH. Server-side
# api/config.php and api/data/ (the database) are never overwritten or
# deleted; config.json (the board settings) is uploaded only when the
# server has none, so edits made on the server are kept.
deploy-demo: demo
	@test -n "$(DEPLOY_HOST)" -a -n "$(DEPLOY_PATH)" || { echo "set DEPLOY_HOST and DEPLOY_PATH in make.local" >&2; exit 2; }
ifeq ($(DEPLOY_METHOD),rsync)
	rsync -rvz --delete --exclude /config.json --exclude /api/config.php --exclude /api/data/ \
		$(DEMO_BBS)/ $(DEPLOY_HOST):$(DEPLOY_PATH)/
	rsync -vz --ignore-existing $(DEMO_BBS)/config.json $(DEPLOY_HOST):$(DEPLOY_PATH)/config.json
else
	lftp -e "set ssl:verify-certificate yes; mirror -R --delete --verbose \
		--exclude-glob config.json --exclude-glob api/config.php --exclude api/data/ \
		$(DEMO_BBS)/ $(DEPLOY_PATH)/; \
		mirror -R --only-missing --verbose --file=$(DEMO_BBS)/config.json --target-directory=$(DEPLOY_PATH)/; quit" \
		$(DEPLOY_HOST)
endif

clean:
	rm -rf build .scratch/smoke
