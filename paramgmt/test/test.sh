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
ATTEMPTS=3

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

for test_id in $(seq 1 $TESTS); do
  echo "***********************************************"
  echo "*** Starting test $test_id of ${TESTS}"
  echo "***********************************************"
  echo ""

  load_hosts ${HOSTFILE}

  rm -rf /tmp/r

  lcmd --hostfile ${HOSTFILE} --attempts 1 mkdir -p /tmp/r/?HOST
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-d /tmp/r/$host" $LINENO
  done

  echo "test 1" > /tmp/r/test1.txt
  assert "-f /tmp/r/test1.txt" $LINENO
  echo "test 2" > /tmp/r/test2.txt
  assert "-f /tmp/r/test2.txt" $LINENO
  echo "test 3" > /tmp/r/test3.txt
  assert "-f /tmp/r/test3.txt" $LINENO

  lcmd --hostfile ${HOSTFILE} --attempts 1 \
    cp /tmp/r/test1.txt /tmp/r/?HOST/test1.txt
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f /tmp/r/$host/test1.txt" $LINENO
    text=`cat /tmp/r/$host/test1.txt`
    test "$text" = "test 1"
    assert "$? -eq 0" $LINENO
  done

  lcmd --hostfile ${HOSTFILE} --attempts 1 \
    cp /tmp/r/test2.txt /tmp/r/?HOST/test2.txt
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f /tmp/r/$host/test2.txt" $LINENO
    text=`cat /tmp/r/$host/test2.txt`
    test "$text" = "test 2"
    assert "$? -eq 0" $LINENO
  done

  lcmd --hostfile ${HOSTFILE} --attempts 1 \
    cp /tmp/r/test3.txt /tmp/r/?HOST/test3.txt
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f /tmp/r/$host/test3.txt" $LINENO
    text=`cat /tmp/r/$host/test3.txt`
    test "$text" = "test 3"
    assert "$? -eq 0" $LINENO
  done

  rcmd --hostfile ${HOSTFILE} --attempts $ATTEMPTS rm -rf /tmp/r
  assert "$? -eq 0" $LINENO

  rcmd --hostfile ${HOSTFILE} --attempts $ATTEMPTS mkdir -p /tmp/r/?HOST
  assert "$? -eq 0" $LINENO

  rcmd --hostfile ${HOSTFILE} --attempts $ATTEMPTS test -d /tmp/r/?HOST
  assert "$? -eq 0" $LINENO

  rpush --hostfile ${HOSTFILE} --attempts $ATTEMPTS \
    --destination=/tmp/r/?HOST/ \
    /tmp/r/?HOST/test1.txt /tmp/r/?HOST/test2.txt
  assert "$? -eq 0" $LINENO

  rcmd --hostfile ${HOSTFILE} --attempts $ATTEMPTS \
    test -f /tmp/r/?HOST/test1.txt
  assert "$? -eq 0" $LINENO

  rcmd --hostfile ${HOSTFILE} --attempts $ATTEMPTS \
    test -f /tmp/r/?HOST/test2.txt
  assert "$? -eq 0" $LINENO

  rpush --hostfile ${HOSTFILE} --attempts $ATTEMPTS \
    --destination=/tmp/r/?HOST/ /tmp/r/?HOST/test3.txt
  assert "$? -eq 0" $LINENO

  rcmd --hostfile ${HOSTFILE} --attempts $ATTEMPTS \
    test -f /tmp/r/?HOST/test3.txt
  assert "$? -eq 0" $LINENO

  lcmd --hostfile ${HOSTFILE} --attempts 1 mkdir -p /tmp/r/?HOST/pull
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-d /tmp/r/$host/pull" $LINENO
  done

  rpull --hostfile ${HOSTFILE} --attempts $ATTEMPTS \
    --destination=/tmp/r/?HOST/pull/ \
    /tmp/r/?HOST/test1.txt /tmp/r/?HOST/test2.txt
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f /tmp/r/$host/pull/test1.txt" $LINENO
    text=`cat /tmp/r/$host/pull/test1.txt`
    test "$text" = "test 1"
    assert "$? -eq 0" $LINENO

    assert "-f /tmp/r/$host/pull/test2.txt" $LINENO
    text=`cat /tmp/r/$host/pull/test2.txt`
    test "$text" = "test 2"
    assert "$? -eq 0" $LINENO
  done

  rpull --hostfile ${HOSTFILE} --attempts $ATTEMPTS \
    --destination=/tmp/r/?HOST/pull/ /tmp/r/?HOST/test3.txt
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f /tmp/r/$host/pull/test3.txt" $LINENO
    text=`cat /tmp/r/$host/pull/test3.txt`
    test "$text" = "test 3"
    assert "$? -eq 0" $LINENO
  done

  lcmd --hostfile ${HOSTFILE} --attempts 1 cp script1.sh \
    /tmp/r/?HOST/script1.sh
  assert "$? -eq 0" $LINENO
  lcmd --hostfile ${HOSTFILE} --attempts 1 cp script2.sh \
    /tmp/r/?HOST/script2.sh
  assert "$? -eq 0" $LINENO
  lcmd --hostfile ${HOSTFILE} --attempts 1 cp script3.sh \
    /tmp/r/?HOST/script3.sh
  assert "$? -eq 0" $LINENO
  for host in ${hosts[*]}; do
    assert "-f /tmp/r/$host/script1.sh" $LINENO
    assert "-f /tmp/r/$host/script2.sh" $LINENO
    assert "-f /tmp/r/$host/script3.sh" $LINENO
  done

  rscript --hostfile ${HOSTFILE} --attempts $ATTEMPTS \
    /tmp/r/?HOST/script1.sh /tmp/r/?HOST/script2.sh /tmp/r/?HOST/script3.sh
  assert "$? -eq 0" $LINENO

  rcmd --hostfile ${HOSTFILE} --attempts $ATTEMPTS \
    test ! -f /tmp/r/?HOST/test1.txt
  assert "$? -eq 0" $LINENO
  rcmd --hostfile ${HOSTFILE} --attempts $ATTEMPTS \
    test -f /tmp/r/?HOST/test2.txt
  assert "$? -eq 0" $LINENO
  rcmd --hostfile ${HOSTFILE} --attempts $ATTEMPTS \
    test ! -f /tmp/r/?HOST/test3.txt
  assert "$? -eq 0" $LINENO

  lcmd --hostfile ${HOSTFILE} --attempts 1 \
    "cat /tmp/r/?HOST/pull/test3.txt | grep test && echo awesome"
  assert "$? -eq 0" $LINENO

  lcmd --hostfile ${HOSTFILE} --attempts 1 \
    "echo 'This is error text' 1>&2 && echo 'This is normal text'"
  assert "$? -eq 0" $LINENO

done
