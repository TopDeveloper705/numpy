#!/usr/bin/env bash

# Exit if a command fails
set -e
set -o pipefail
# Print expanded commands
set -x

sudo apt-get -yq update
sudo apt-get -yq install libatlas-base-dev liblapack-dev gfortran-5
F77=gfortran-5 F90=gfortran-5 \

# Download the proper OpenBLAS x64 precompiled library
OPENBLAS=openblas-v0.3.5-274-g6a8b4269-manylinux1_x86_64.tar.gz
echo getting $OPENBLAS
wget -q https://3f23b170c54c2533c070-1c8a9b3114517dc5fe17b7c3f8c63a43.ssl.cf2.rackcdn.com/$OPENBLAS -O openblas.tar.gz
mkdir -p openblas
(cd openblas; tar -xf ../openblas.tar.gz)
export LD_LIBRARY_PATH=$PWD/openblas/usr/local/lib
export LIB=$PWD/openblas/usr/local/lib
export INCLUDE=$PWD/openblas/usr/local/include

# Use a site.cfg to build with local openblas
cat << EOF > site.cfg
[openblas]
libraries = openblas
library_dirs = $PWD/openblas/usr/local/lib:$LIB
include_dirs = $PWD/openblas/usr/local/lib:$LIB
runtime_library_dirs = $PWD/openblas/usr/local/lib
EOF

echo getting PyPy 3.6 nightly
wget -q http://buildbot.pypy.org/nightly/py3.6/pypy-c-jit-latest-linux64.tar.bz2 -O pypy.tar.bz2
mkdir -p pypy3
(cd pypy3; tar --strip-components=1 -xf ../pypy.tar.bz2)
pypy3/bin/pypy3 -mensurepip
pypy3/bin/pypy3 -m pip install --upgrade pip setuptools
pypy3/bin/pypy3 -m pip install --user cython==0.29.0 pytest pytz --no-warn-script-location

echo
echo pypy3 version 
pypy3/bin/pypy3 -c "import sys; print(sys.version)"
echo

pypy3/bin/pypy3 runtests.py --show-build-log -- -rsx \
      --junitxml=junit/test-results.xml --durations 10

echo Make sure the correct openblas has been linked in

pypy3/bin/pip install .
(cd pypy3; bin/pypy3 -c "$TEST_GET_CONFIG")
