#!/bin/bash

# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

HOSTFILE=${1:-hosts.txt}
TESTS=${2:-1}  # default to one test

hosts=()
function load_hosts() {
  hosts=( $(rhosts --hostfile=$1) )
  echo "${#hosts[@]} hosts"
  echo "${hosts[*]}"
  echo ""
}

function assert() {
  if [ -z "$2" ]; then
    echo "not enough parameters given to assert()"
    exit -1
  fi
  if [ ! $1 ]; then
    echo "Assertion failure: \"$1\""
    echo "File \"$0\", line \"$2\""
    exit -1
  fi
}

function make_script() {
  num=$1
  dir=$2
  file=$dir/script$num.sh
  if [[ $num -eq 1 ]]; then
    echo "#!/bin/bash" > $file
    echo "test -f $dir/?HOST/test1.txt" >> $file
    echo "test -f $dir/?HOST/test2.txt" >> $file
    echo "test -f $dir/?HOST/test3.txt" >> $file
  elif [[ $num -eq 2 ]]; then
    echo "#!/bin/bash" > $file
    echo "rm -f $dir/?HOST/test1.txt" >> $file
    echo "rm -f $dir/?HOST/test3.txt" >> $file
  elif [[ $num -eq 3 ]]; then
    echo "#!/bin/bash" > $file
    echo "test ! -f $dir/?HOST/test1.txt" >> $file
    echo "test -f $dir/?HOST/test2.txt" >> $file
    echo "test ! -f $dir/?HOST/test3.txt" >> $file
  else
    assert "false" $LINENO
  fi
}

for test_id in $(seq 1 $TESTS); do
  echo "***********************************************"
  echo "*** Starting test $test_id of ${TESTS}"
  echo "***********************************************"
  echo ""

  if ! which rhosts lcmd rcmd rpush rpull rscript > /dev/null; then
    echo "paramgmt executables aren't present, please install"
    exit -1
  fi

  load_hosts ${HOSTFILE}

  tmp=`python -c "import tempfile; print tempfile.mkdtemp()"`

  lcmd -f ${HOSTFILE} -- mkdir -p $tmp/?HOST
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-d $tmp/$host" $LINENO
  done

  echo "test 1" > $tmp/test1.txt
  assert "-f $tmp/test1.txt" $LINENO
  echo "test 2" > $tmp/test2.txt
  assert "-f $tmp/test2.txt" $LINENO
  echo "test 3" > $tmp/test3.txt
  assert "-f $tmp/test3.txt" $LINENO

  lcmd -f ${HOSTFILE} -- cp $tmp/test1.txt $tmp/?HOST/test1.txt
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f $tmp/$host/test1.txt" $LINENO
    text=`cat $tmp/$host/test1.txt`
    test "$text" = "test 1"
    assert "$? -eq 0" $LINENO
  done

  lcmd -f ${HOSTFILE} -- cp $tmp/test2.txt $tmp/?HOST/test2.txt
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f $tmp/$host/test2.txt" $LINENO
    text=`cat $tmp/$host/test2.txt`
    test "$text" = "test 2"
    assert "$? -eq 0" $LINENO
  done

  lcmd -f ${HOSTFILE} -- cp $tmp/test3.txt $tmp/?HOST/test3.txt
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f $tmp/$host/test3.txt" $LINENO
    text=`cat $tmp/$host/test3.txt`
    test "$text" = "test 3"
    assert "$? -eq 0" $LINENO
  done

  rcmd -f ${HOSTFILE} -- rm -rf $tmp
  assert "$? -eq 0" $LINENO

  rcmd -f ${HOSTFILE} -- mkdir -p $tmp/?HOST
  assert "$? -eq 0" $LINENO

  rcmd -f ${HOSTFILE} -- test -d $tmp/?HOST
  assert "$? -eq 0" $LINENO

  rpush -f ${HOSTFILE} -d $tmp/?HOST/ -- \
    $tmp/?HOST/test1.txt $tmp/?HOST/test2.txt
  assert "$? -eq 0" $LINENO

  rcmd -f ${HOSTFILE} -- test -f $tmp/?HOST/test1.txt
  assert "$? -eq 0" $LINENO

  rcmd -f ${HOSTFILE} -- test -f $tmp/?HOST/test2.txt
  assert "$? -eq 0" $LINENO

  rpush -f ${HOSTFILE} -d $tmp/?HOST/ -- $tmp/?HOST/test3.txt
  assert "$? -eq 0" $LINENO

  rcmd -f ${HOSTFILE} -- test -f $tmp/?HOST/test3.txt
  assert "$? -eq 0" $LINENO

  lcmd -f ${HOSTFILE} -- mkdir -p $tmp/?HOST/pull
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-d $tmp/$host/pull" $LINENO
  done

  rpull -f ${HOSTFILE} -d $tmp/?HOST/pull/ -- \
    $tmp/?HOST/test1.txt $tmp/?HOST/test3.txt
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f $tmp/$host/pull/test1.txt" $LINENO
    text=`cat $tmp/$host/pull/test1.txt`
    test "$text" = "test 1"
    assert "$? -eq 0" $LINENO

    assert "-f $tmp/$host/pull/test3.txt" $LINENO
    text=`cat $tmp/$host/pull/test3.txt`
    test "$text" = "test 3"
    assert "$? -eq 0" $LINENO
  done

  rpull -f ${HOSTFILE} -d $tmp/?HOST/pull/ -- $tmp/?HOST/test2.txt
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f $tmp/$host/pull/test2.txt" $LINENO
    text=`cat $tmp/$host/pull/test2.txt`
    test "$text" = "test 2"
    assert "$? -eq 0" $LINENO
  done

  make_script 1 $tmp
  make_script 2 $tmp
  make_script 3 $tmp

  lcmd -f ${HOSTFILE} cp $tmp/script1.sh -- $tmp/?HOST/script1.sh
  assert "$? -eq 0" $LINENO
  lcmd -f ${HOSTFILE} cp $tmp/script2.sh -- $tmp/?HOST/script2.sh
  assert "$? -eq 0" $LINENO
  lcmd -f ${HOSTFILE} cp $tmp/script3.sh -- $tmp/?HOST/script3.sh
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f $tmp/$host/script1.sh" $LINENO
    assert "-f $tmp/$host/script2.sh" $LINENO
    assert "-f $tmp/$host/script3.sh" $LINENO
  done

  rscript -f ${HOSTFILE} -- $tmp/?HOST/script1.sh $tmp/?HOST/script2.sh \
    $tmp/?HOST/script3.sh
  assert "$? -eq 0" $LINENO

  rcmd -f ${HOSTFILE} -- test ! -f $tmp/?HOST/test1.txt
  assert "$? -eq 0" $LINENO
  rcmd -f ${HOSTFILE} -- test -f $tmp/?HOST/test2.txt
  assert "$? -eq 0" $LINENO
  rcmd -f ${HOSTFILE} -- test ! -f $tmp/?HOST/test3.txt
  assert "$? -eq 0" $LINENO

  lcmd -f ${HOSTFILE} -- \
    "cat $tmp/?HOST/pull/test3.txt | grep test && echo awesome"
  assert "$? -eq 0" $LINENO

  lcmd -f ${HOSTFILE} -- \
    "echo 'This is error text' 1>&2 && echo 'This is normal text'"
  assert "$? -eq 0" $LINENO

  rcmd -f ${HOSTFILE} -- rm -rf $tmp
  assert "$? -eq 0" $LINENO

  rm -rf $tmp
done
