.PHONY: info
info:
	@echo "- type 'make deb' to build a debian package"
	@echo "- you need the debian packages"
	@echo "  fakeroot python3-setuptools python3-stdeb dh-python"
	@echo


# build a new debian package and create a link in the current directory
.PHONY: deb
deb: distclean
	@# build the deb package
	PYBUILD_DISABLE=test python3 setup.py \
	  --command-packages=stdeb.command \
	  sdist_dsc --compat 10 --package3 nanovnasaver --section electronics \
	  bdist_deb
	@# create a link in the main directory
	-@ln `ls deb_dist/nanovnasaver_*.deb | tail -1` .
	@# and show the result
	@ls -l nanovnasaver_*.deb


# remove all package build artifacts (keep the *.deb)
.PHONY: clean
clean:
	python setup.py clean
	-rm -rf build deb_dist dist *.tar.gz *.egg*


# remove all package build artefacts
.PHONY: distclean
distclean: clean
	-rm *.deb


# build and install a new debian package
.PHONY: debinstall
debinstall: deb
	sudo apt install ./nanovnasaver_*.deb


# uninstall this debian package
.PHONY: debuninstall
debuninstall:
	sudo apt purge nanovnasaver_*.deb

