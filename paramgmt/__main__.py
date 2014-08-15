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

"""main: this is a test suite for paramgmt.

This is not meant to be a good representation of how to use paramgmt. This
file is a cryptic test of paramgmt. Please see the documentation for usage.
"""

import argparse
import os
import subprocess
import sys
import tempfile

import paramgmt


def main(args):
  rounds = args.rounds
  user = args.user
  hosts = []
  if args.hosts is not None:
    hosts.extend(args.hosts)
  if args.hostfile is not None:
    hosts.extend(paramgmt.parse_file(args.hostfile))
  if not hosts:
    print 'no hosts specified'
    return 0

  for round in range(0, rounds):
    print '***********************************************'
    print '*** Starting test {0} of {1}'.format(round+1, rounds)
    print '***********************************************'
    print ''

    tmp = tempfile.mkdtemp()

    ctl = paramgmt.Controller(hosts=hosts, user=user, parallel=True,
                              quiet=False, color=True, attempts=3)

    ctl.attempts = 1
    sts = ctl.local_command(['mkdir', '-p', os.path.join(tmp, '?HOST')])
    assert paramgmt.all_success(sts)
    for host in hosts:
      do('test -d {0}'.format(os.path.join(tmp, host)))

    for num in range(1, 4):
      filepath1 = os.path.join(tmp, 'test{0}.txt'.format(num))
      do('echo "test {0}" > {1}'.format(num, filepath1))
      do('test -f {0}'.format(filepath1))

    for num in range(1, 4):
      filepath1 = os.path.join(tmp, 'test{0}.txt'.format(num))
      filepath2 = os.path.join(tmp, '?HOST', 'test{0}.txt'.format(num))
      ctl.attempts = 1
      sts = ctl.local_command(['cp', filepath1, filepath2])
      assert paramgmt.all_success(sts)
      for host in hosts:
        filepath3 = os.path.join(tmp, host, 'test{0}.txt'.format(num))
        do('test -f {0}'.format(filepath3))

    ctl.attempts = 3
    sts = ctl.remote_command(['rm', '-rf', tmp])
    assert paramgmt.all_success(sts)

    ctl.attempts = 3
    filepath1 = os.path.join(tmp, '?HOST')
    sts = ctl.remote_command(['mkdir', '-p', filepath1])
    assert paramgmt.all_success(sts)

    ctl.attempts = 3
    filepath1 = os.path.join(tmp, '?HOST')
    sts = ctl.remote_command(['test', '-d', filepath1])
    assert paramgmt.all_success(sts)

    ctl.attempts = 3
    filepath1 = os.path.join(tmp, '?HOST', 'test1.txt')
    filepath2 = os.path.join(tmp, '?HOST', 'test2.txt')
    filepath3 = os.path.join(tmp, '?HOST', 'test3.txt')
    filepath4 = os.path.join(tmp, '?HOST')
    sts = ctl.remote_push([filepath1, filepath2], filepath4)
    assert paramgmt.all_success(sts)

    ctl.attempts = 3
    sts = ctl.remote_command(['test', '-f', filepath1])
    assert paramgmt.all_success(sts)

    ctl.attempts = 3
    sts = ctl.remote_command(['test', '-f', filepath2])
    assert paramgmt.all_success(sts)

    ctl.attempts = 3
    sts = ctl.remote_push([filepath3], filepath4)
    assert paramgmt.all_success(sts)

    ctl.attempts = 3
    sts = ctl.remote_command(['test', '-f', filepath3])
    assert paramgmt.all_success(sts)

    ctl.attempts = 1
    filepath5 = os.path.join(tmp, '?HOST', 'pull')
    sts = ctl.local_command(['mkdir', '-p', filepath5])
    assert paramgmt.all_success(sts)
    for host in hosts:
      filepath6 = os.path.join(tmp, host, 'pull')
      do('test -d {0}'.format(filepath6))

    ctl.attempts = 3
    sts = ctl.remote_pull([filepath1, filepath3], filepath5)
    assert paramgmt.all_success(sts)
    for host in hosts:
      filepath6 = os.path.join(tmp, host, 'pull', 'test1.txt')
      filepath7 = os.path.join(tmp, host, 'pull', 'test3.txt')
      do('test -f {0}'.format(filepath6))
      do('test -f {0}'.format(filepath7))

    ctl.attempts = 1
    filepath6 = os.path.join(tmp, '?HOST', 'pull', 'test1.txt')
    filepath7 = os.path.join(tmp, '?HOST', 'pull', 'test2.txt')
    filepath8 = os.path.join(tmp, '?HOST', 'pull', 'test3.txt')
    sts = ctl.local_command(['test', '-f', filepath6])
    assert paramgmt.all_success(sts)

    ctl.attempts = 1
    sts = ctl.local_command(['test', '-f', filepath8])
    assert paramgmt.all_success(sts)

    ctl.attempts = 3
    sts = ctl.remote_pull([filepath2], filepath5)
    assert paramgmt.all_success(sts)
    for host in hosts:
      filepath9 = os.path.join(tmp, host, 'pull', 'test2.txt')
      do('test -f {0}'.format(filepath9))

    ctl.attempts = 1
    sts = ctl.local_command(['test', '-f', filepath7])
    assert paramgmt.all_success(sts)

    for num in range(1, 4):
      scriptfileA = os.path.join(tmp, 'script{0}.sh'.format(num))
      scriptfileB = os.path.join(tmp, '?HOST', 'script{0}.sh'.format(num))
      with open(scriptfileA, 'w') as fd:
        fd.write(get_script(num, tmp))

      ctl.attempts = 1
      sts = ctl.local_command(['cp', scriptfileA, scriptfileB])
      assert paramgmt.all_success(sts)
      for host in hosts:
        scriptfileC = os.path.join(tmp, host, 'script{0}.sh'.format(num))
        do('test -f {0}'.format(scriptfileC))

    ctl.attempts = 3
    script1 = os.path.join(tmp, '?HOST', 'script1.sh')
    script2 = os.path.join(tmp, '?HOST', 'script2.sh')
    script3 = os.path.join(tmp, '?HOST', 'script3.sh')
    sts = ctl.remote_script([script1, script2, script3])
    assert paramgmt.all_success(sts)

    ctl.attempts = 3
    test1 = os.path.join(tmp, '?HOST', 'test1.txt')
    test2 = os.path.join(tmp, '?HOST', 'test2.txt')
    test3 = os.path.join(tmp, '?HOST', 'test3.txt')
    sts = ctl.remote_command(
        ['test ! -f {0} && test -f {1} && test ! -f {2}'
         .format(test1, test2, test3)])
    assert paramgmt.all_success(sts)

    ctl.attempts = 1
    filepath = os.path.join(tmp, '?HOST', 'pull', 'test3.txt')
    sts = ctl.local_command(
        ['cat {0} | grep test && echo ?HOST is awesome'.format(filepath)])
    assert paramgmt.all_success(sts)
    for s in sts:
      assert s.stdout == ('test 3\n' + s.host + ' is awesome')

    ctl.attempts = 1
    sts = ctl.local_command(
        ['echo "This is stderr text" 1>&2 && echo "This is stdout text"'])
    assert paramgmt.all_success(sts)
    for s in sts:
      assert s.stdout == 'This is stdout text'
      assert s.stderr == 'This is stderr text'

    ctl.attempts = 1
    multi = os.path.join(tmp, '?HOST', 'multi')
    sts = ctl.local_command(['rm -f {0} && touch {0}'.format(multi)])
    assert paramgmt.all_success(sts)

    ctl.attempts = 5
    sts = ctl.local_command(
        [('echo -n X >> {0} && test `stat {0} |'
          'grep Size | awk \'{{print $2}}\'` -eq 5')
         .format(multi)])
    assert paramgmt.all_success(sts)
    for s in sts:
      assert s.attempts == 5

    do('rm -rf {0}'.format(tmp))

  return 0


def do(cmd):
  subprocess.check_call(cmd, shell=True)


def get_script(num, tmp):
  test1 = os.path.join(tmp, '?HOST', 'test1.txt')
  test2 = os.path.join(tmp, '?HOST', 'test2.txt')
  test3 = os.path.join(tmp, '?HOST', 'test3.txt')
  if num == 1:
    return ('#!/bin/bash\n' +
            '\n' +
            'test -f {0}\n'.format(test1) +
            'test -f {0}\n'.format(test2) +
            'test -f {0}\n'.format(test3))
  elif num == 2:
    return ('#!/bin/bash\n' +
            '\n' +
            'rm -f {0}\n'.format(test1) +
            'rm -f {0}\n'.format(test3))
  elif num == 3:
    return ('#!/bin/bash\n' +
            '\n' +
            'test ! -f {0}\n'.format(test1) +
            'test -f {0}\n'.format(test2) +
            'test ! -f {0}\n'.format(test3))
  else:
    raise Exception('moron!')


def check_hosts(value):
  return value.split()


def check_hostfile(value):
  if not os.path.isfile(value):
    msg = 'hostfile "{0}" does not exist'.format(value)
    raise argparse.ArgumentTypeError(msg)
  if not os.access(value, os.R_OK):
    msg = 'hostfile "{0}" is not readable'.format(value)
    raise argparse.ArgumentTypeError(msg)
  return value


if __name__ == '__main__':
  parser = argparse.ArgumentParser(prog='rhosts', description='remote hosts')
  parser.add_argument('-u', '--user', default=paramgmt.USER_DEFAULT,
                      help='Username for SSH commands')
  parser.add_argument('-m', '--hosts', type=check_hosts,
                      help='A list of hostnames (space separated)')
  parser.add_argument('-f', '--hostfile', type=check_hostfile,
                      help='A file containing hostnames')
  parser.add_argument('-r', '--rounds', type=int, default=1,
                      help='Number of test rounds')
  sys.exit(main(parser.parse_args()))
