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

"""paramgmt: a library for executing commands to a cluster in parallel."""

import subprocess
import sys
import threading

from termcolor import colored


class ParaMgmt(object):
  """This class offers parallel cluster management using SSH and SCP."""

  class MgmtCommand(threading.Thread):
    """A container class for commands given to ParaMgmt."""

    def __init__(self, host, commands, max_attempts, description=None,
                 stdin=None):
      """Constructor for MgmtCommand."""
      threading.Thread.__init__(self)
      self.host = host
      self.commands = commands
      if description is not None:
        self.description = description
      else:
        self.description = self.commands
      self.attempts = 0
      self.max_attempts = max_attempts
      self.process = None
      self.retcode = None
      self.stdin = stdin
      self.stdout = None
      self.stderr = None

    def run(self):
      """Runs the command, called by threading library."""
      while self.attempts < self.max_attempts:
        # attempt to run the process
        self.attempts += 1
        if self.stdin:
          stdin_fd = subprocess.PIPE
        else:
          stdin_fd = None

        self.process = subprocess.Popen(self.commands,
                                        stdin=stdin_fd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

        out, err = self.process.communicate(input=self.stdin)
        self.retcode = self.process.returncode
        self.stdout = out
        self.stderr = err
        self.process = None
        if self.retcode == 0:
          break

    def Status(self, color=True):
      """This displays the result of the command.

      Args:
        color : whether or not to color the output
      """
      if color:
        print '{0}'.format(colored(self.description, 'blue'))
      else:
        print '{0}'.format(self.description)

      if self.stdout:
        if color:
          print 'stdout:\n{0}'.format(colored(self.stdout, 'green'))
        else:
          print 'stdout:\n{0}'.format(self.stdout)

      if self.stderr:
        if color:
          print 'stderr:\n{0}'.format(colored(self.stderr, 'red'))
        else:
          print 'stderr:\n{0}'.format(self.stderr)

      if self.retcode is not 0:
        if color:
          print 'return code: {0}'.format(colored(self.retcode, 'red'))
          print 'attempts:    {0}'.format(colored(self.attempts, 'red'))
        else:
          print 'return code: {0}'.format(self.retcode)
          print 'attempts:    {0}'.format(self.attempts)

  def __init__(self, user, hosts, parallel=True, quiet=False, color=True,
               attempts=1):
    """Constructor for ParaMgmt.

    Args:
      user     : The remote user account.
      hosts    : A list of hostnames.
      parallel : (default=True) Run commands in parallel.
      quiet    : Suppress printing output to stdout.
      color    : (default=True) Color the output.
                 Only enabled if sys.stdout.isatty() is true and not quiet
      attempts : Maximum number of process tries.
    """

    self._user = user
    self._hosts = hosts
    self._parallel = parallel
    self._quiet = quiet
    self._color = color and sys.stdout.isatty()
    self._attempts = attempts
    self._ssh_options = ['-o', 'PasswordAuthentication=no',
                         '-o', 'ConnectTimeout=2',
                         '-o', 'ConnectionAttempts=2']

  def LocalCommand(self, commands):
    """Run local command for all hosts specified.

    Args:
      commands : The local commands.
                 '?HOST' is replaced with actual hostname.

    Returns:
      A list of MgmtCommand objects.
    """

    # create a list of MgmtCommands for _RunCommands()
    mgmt_commands = []
    for host in self._hosts:
      command = []
      for c in commands:
        command.append(c.replace('?HOST', host))
      command = ' '.join(command)
      mgmt_command = ParaMgmt.MgmtCommand(
          host, ['/bin/sh'], self._attempts,
          'lcmd: ({0}) {1}'.format(host, command),
          command)
      mgmt_commands.append(mgmt_command)

    # run all commands
    self._RunCommands(mgmt_commands)
    return mgmt_commands

  def RemoteCommand(self, commands):
    """Run SSH command to all hosts specified.

    Args:
      commands : The remote commands of the SSH command.
                 '?HOST' is replaced with actual hostname.

    Returns:
      A list of MgmtCommand objects.
    """

    # create a list of MgmtCommands for _RunCommands()
    mgmt_commands = []
    for host in self._hosts:
      command = ['ssh']
      command.extend(self._ssh_options)
      desc = 'rcmd: '
      tmp = '{0}@{1}'.format(self._user, host)
      command.append(tmp)
      desc += '({0})'.format(tmp)
      for c in commands:
        tmp = c.replace('?HOST', host)
        command.append(tmp)
        desc += ' {0}'.format(tmp)
      mgmt_command = ParaMgmt.MgmtCommand(host, command, self._attempts, desc)
      mgmt_commands.append(mgmt_command)

    # run all commands
    self._RunCommands(mgmt_commands)
    return mgmt_commands

  def RemotePush(self, local, remote):
    """Push specified documents to all remote hosts via SCP.

    Args:
      local     : A list of local file(s) and/or directory(ies)
                  '?HOST' is replaced with actual hostname.
      remote    : A string specification of the remote destination file(s).
                  '?HOST' is replaced with actual hostname.

    Returns:
      A list of MgmtCommand objects.
    """

    # create a list of MgmtCommands for _RunCommands()
    mgmt_commands = []
    for host in self._hosts:
      command = ['scp', '-r']
      command.extend(self._ssh_options)
      desc = 'rpush: '
      for ll in local:
        tmp = ll.replace('?HOST', host)
        command.append(tmp)
        desc += ' {0}'.format(tmp)
      desc += ' => '
      tmp = '{0}@{1}:{2}'.format(self._user, host,
                                 remote.replace('?HOST', host))
      command.append(tmp)
      desc += tmp
      mgmt_command = ParaMgmt.MgmtCommand(host, command, self._attempts, desc)
      mgmt_commands.append(mgmt_command)

    # run all commands
    self._RunCommands(mgmt_commands)
    return mgmt_commands

  def RemotePull(self, remote, local):
    """Push specified documents to all remote hosts via SCP.

    Args:
      remote    : A list of remote file(s) and/or directory(ies)
                  '?HOST' is replaced with actual hostname.
      local     : A string specification of the local destination file(s).
                  '?HOST' is replaced with actual hostname.

    Returns:
      A list of MgmtCommand objects.
    """

    # create a list of MgmtCommands for _RunCommands()
    mgmt_commands = []
    for host in self._hosts:
      command = ['scp', '-r']
      command.extend(self._ssh_options)
      desc = 'rpull: '
      remote2 = ''
      for idx, rr in enumerate(remote):
        remote2 += rr.replace('?HOST', host)
        if idx < (len(remote) - 1):
          remote2 += ','
      if len(remote) > 1:
        remote2 = '{{{0}}}'.format(remote2)
      tmp = '{0}@{1}:{2}'.format(self._user, host, remote2)
      command.append(tmp)
      desc += tmp
      desc += ' => '
      tmp = local.replace('?HOST', host)
      command.append(tmp)
      desc += tmp
      mgmt_command = ParaMgmt.MgmtCommand(host, command, self._attempts, desc)
      mgmt_commands.append(mgmt_command)

    # run all commands
    self._RunCommands(mgmt_commands)
    return mgmt_commands

  def RemoteScript(self, scripts):
    """Run local scripts on remote hosts via SSH.

    Args:
      scripts  : a list of local scripts to be run on the remote hosts.
                 '?HOST' in script names is replaced with actual hostname.
                 '?HOST' in the script is replaced with actual hostname.

    Returns:
      A list of MgmtCommand objects.
    """

    # create a list of MgmtCommands for _RunCommands()
    mgmt_commands = []
    for host in self._hosts:
      command = ['ssh', '-T']
      command.extend(self._ssh_options)
      desc = 'rscript: '
      tmp = '{0}@{1}'.format(self._user, host)
      command.append(tmp)

      # read in the text of the scripts
      script_names = []
      all_script = ''
      for script in scripts:
        script_name = script.replace('?HOST', host)
        script_names.append(script_name)
        with open(script_name, 'r') as fd:
          all_script += fd.read()
        if all_script[len(all_script)-1] != '\n':
          all_script += '\n'
      if not all_script:
        all_script = ':'

      # format description and command
      desc += '({0}) running {1}'.format(tmp, ' '.join(script_names))
      mgmt_command = ParaMgmt.MgmtCommand(host, command, self._attempts, desc,
                                          all_script.replace('?HOST', host))
      mgmt_commands.append(mgmt_command)

    # run all commands
    self._RunCommands(mgmt_commands)
    return mgmt_commands

  def _RunCommands(self, mgmt_commands):
    """This runs the specified commands.

    Args:
      mgmt_commands  : A list of MgmtCommands

    Returns:
      Nothing, but it completes mgmt_command objects
    """

    # run all commands
    outstanding = []
    failed = []
    for mgmt_command in mgmt_commands:
      mgmt_command.start()
      if self._parallel:
        outstanding.append(mgmt_command)
      else:
        mgmt_command.join()
        if not self._quiet:
          mgmt_command.Status(self._color)
        if mgmt_command.retcode is not 0:
          failed.append(mgmt_command)

    for mgmt_command in outstanding:
      mgmt_command.join()
      if not self._quiet:
        mgmt_command.Status(self._color)
      if mgmt_command.retcode is not 0:
        failed.append(mgmt_command)

    # show stats
    if not self._quiet:
      total = len(mgmt_commands)
      failures = len(failed)
      successes = total - failures
      print ('{0} succeeded, {1} failed, {2} total'
             .format(successes, failures, total))
      if failures > 0:
        print 'Failed hosts:'
        for mgmt_command in failed:
          host = mgmt_command.host
          if self._color:
            host = colored(host, 'red')
          print host


def AllSuccess(mgmt_commands):
  """Determines if all child processes were successful.

  Args:
    mgmt_commands : A list of all MgmtCommand objects

  Returns:
    True if all child processes succeeded
  """

  for mgmt_command in mgmt_commands:
    if mgmt_command.retcode != 0:
      return False
  return True


def ParseFile(filename):
  """This function parses a file to generate a list of lines.

  This function removes comments delimited by '#' and ingores empty
  lines.

  Args:
    filename : The name of the file to be parsed

  Returns:
    A list of lines.
  """

  fd = open(filename, 'r')
  lines = []
  for line in fd:
    idx = line.find('#')
    if idx >= 0:
      line = line[:idx]
    line = line.strip()
    if line:
      lines.append(line.strip())
  fd.close()

  return lines
