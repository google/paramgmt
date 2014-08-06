#!/usr/bin/python

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

"""rcmd: An application that wraps the paramgmt.RemoteCommand function."""

import argparse
import os
import sys

import paramgmt


def main(args):
  hosts = []
  if args.hosts is not None:
    hosts.extend(args.hosts)
  if args.hostfile is not None:
    hosts.extend(paramgmt.ParseFile(args.hostfile))
  if not hosts:
    print 'no hosts specified'
    return 0

  parallel = not args.sequential
  color = not args.no_color
  pmgmt = paramgmt.ParaMgmt(args.user, hosts, parallel, False,
                            color, args.attempts)
  ret = pmgmt.RemoteCommand(args.commands)
  return 0 if paramgmt.AllSuccess(ret) else -1


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


def check_attempts(value):
  ivalue = int(value)
  if ivalue < 1:
    msg = 'attempts must be greater than 0'
    raise argparse.ArgumentTypeError(msg)
  return ivalue


if __name__ == '__main__':
  parser = argparse.ArgumentParser(prog='rcmd', description='remote commands')
  parser.add_argument('-u', '--user', default='root',
                      help='Username for SSH commands')
  parser.add_argument('-m', '--hosts', type=check_hosts,
                      help='A list of hostnames (space separated)')
  parser.add_argument('-f', '--hostfile', type=check_hostfile,
                      help='A file containing hostnames')
  parser.add_argument('-s', '--sequential', action='store_true',
                      help='Run commands sequentially')
  parser.add_argument('-c', '--no_color', action='store_true',
                      help='Disable coloring of output')
  parser.add_argument('-a', '--attempts', type=check_attempts, default=1,
                      help='Maximum number of command attempts')
  parser.add_argument('commands', nargs=argparse.REMAINDER,
                      help='Commands to be run locally')
  sys.exit(main(parser.parse_args()))
