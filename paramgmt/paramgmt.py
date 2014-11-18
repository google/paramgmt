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

# Python 3 compatibility
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import subprocess
import sys
import threading

try:
  from termcolor import colored
  CAN_COLOR = True
except ImportError:
  CAN_COLOR = False

# defaults declared here for uses in binaries
USER_DEFAULT = None
PARALLEL_DEFAULT = True
QUIET_DEFAULT = False
COLOR_DEFAULT = True
ATTEMPTS_DEFAULT = 3

# error message from SSH indicating that it couldn't connect
SSH_ERROR_MSGS = [
    'Connection timed out during banner exchange',
    'ssh_exchange_identification: Connection closed by remote host']


def _should_color(want_to_color):
  """This function turns 'want_to_color' into 'should_color'."""
  return want_to_color and CAN_COLOR and sys.stdout.isatty()


def all_success(mgmt_commands):
  """Determines if all child processes were successful.

  Args:
    mgmt_commands : A list of all Command objects

  Returns:
    True if all child processes succeeded
  """

  for mgmt_command in mgmt_commands:
    if mgmt_command.retcode != 0:
      return False
  return True


def parse_file(filename):
  """This function parses a file to generate a list of lines.

  This function wraps the parse_stream() function by opening
  the specified file first.

  Args:
    filename : The name of the file to be parsed

  Returns:
    A list of lines.
  """

  fd = open(filename, 'r')
  lines = parse_stream(fd)
  fd.close()
  return lines


def parse_stream(stream):
  """This function parses the contents of a stream to generate a list of lines.

  This function removes comments delimited by '#', ingores empty
  lines, and leading and trailing whitespace.

  Args:
    stream : A file that has been open()'d

  Returns:
    A list of lines.
  """

  lines = []
  for line in stream:
    idx = line.find('#')
    if idx >= 0:
      line = line[:idx]
    line = line.strip()
    if line:
      lines.append(line.strip())
  return lines


class Controller(object):
  """This class offers parallel cluster management using SSH and SCP."""

  def __init__(self, hosts, user=USER_DEFAULT, parallel=PARALLEL_DEFAULT,
               quiet=QUIET_DEFAULT, color=COLOR_DEFAULT,
               attempts=ATTEMPTS_DEFAULT):
    """Constructor for Controller.

    Args:
      hosts    : A list of hostnames.
      user     : The remote user account.
      parallel : Run commands in parallel.
      quiet    : Suppress printing output to stdout.
      color    : Color the output. Only enabled if sys.stdout.isatty() is true
                 and not quiet and termcolor was successfully imported.
      attempts : Maximum number of process tries.
    """

    self._user = user
    self._hosts = hosts
    self._parallel = parallel
    self._quiet = quiet
    self._color = _should_color(color)
    self._attempts = int(attempts)
    self._ssh_connect_timeout = 2
    self._ssh_connection_attempts = 3

  @property
  def user(self):
    return self._user

  @user.setter
  def user(self, val):
    self._user = val

  @property
  def parallel(self):
    return self._parallel

  @parallel.setter
  def parallel(self, val):
    self._parallel = val

  @property
  def quiet(self):
    return self._quiet

  @quiet.setter
  def quiet(self, val):
    self._quiet = val

  @property
  def color(self):
    return self._color

  @color.setter
  def color(self, val, force=False):
    if val and force:
      if not CAN_COLOR:
        raise EnvironmentError('package \'termcolor\' does not exist')
      self._color = True
    self._color = _should_color(val)

  @property
  def attempts(self):
    return self._attempts

  @attempts.setter
  def attempts(self, val):
    self._attempts = int(val)

  @property
  def ssh_connect_timeout(self):
    return self._ssh_connect_timeout

  @ssh_connect_timeout.setter
  def ssh_connect_timeout(self, val):
    self._ssh_connect_timeout = int(val)

  @property
  def ssh_connection_attempts(self):
    return self._ssh_connection_attempts

  @ssh_connection_attempts.setter
  def ssh_connection_attempts(self, val):
    self._ssh_connection_attempts = int(val)

  def _ssh_options(self):
    return ['-o', 'PasswordAuthentication=no',
            '-o', 'ConnectTimeout={0}'
            .format(self._ssh_connect_timeout),
            '-o', 'ConnectionAttempts={0}'
            .format(self._ssh_connection_attempts)]

  def _run_commands(self, mgmt_commands):
    """This runs the specified commands.

    Args:
      mgmt_commands  : A list of Commands

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
          print(mgmt_command.status(self._color))
        if mgmt_command.retcode is not 0:
          failed.append(mgmt_command)

    for mgmt_command in outstanding:
      mgmt_command.join()
      if not self._quiet:
        print(mgmt_command.status(self._color))
      if mgmt_command.retcode is not 0:
        failed.append(mgmt_command)

    # show stats
    if not self._quiet:
      total = len(mgmt_commands)
      failures = len(failed)
      successes = total - failures
      print(('{0} succeeded, {1} failed, {2} total\n'
             .format(successes, failures, total)))
      if failures > 0:
        print('Failed hosts:')
        for mgmt_command in failed:
          host = mgmt_command.host
          if self._color:
            host = colored(host, 'red')
          print(host)

  def local_command(self, commands):
    """Run local command for all hosts specified.

    Args:
      commands : The local commands.
                 '?HOST' is replaced with actual hostname.

    Returns:
      A list of Command objects.
    """

    # create a list of Commands for _run_commands()
    mgmt_commands = []
    for host in self._hosts:
      command = []
      for c in commands:
        command.append(c.replace('?HOST', host))
      command = ' '.join(command)
      mgmt_command = Command(
          host, ['/bin/sh'], self._attempts,
          'lcmd [{0}]: {1}'.format(host, command),
          command)
      mgmt_commands.append(mgmt_command)

    # run all commands
    self._run_commands(mgmt_commands)
    return mgmt_commands

  def remote_command(self, commands):
    """Run SSH command to all hosts specified.

    Args:
      commands : The remote commands of the SSH command.
                 '?HOST' is replaced with actual hostname.

    Returns:
      A list of Command objects.
    """

    # create a list of Commands for _run_commands()
    mgmt_commands = []
    for host in self._hosts:
      command = ['ssh']
      command.extend(self._ssh_options())
      if self._user:
        rspec = '{0}@{1}'.format(self._user, host)
      else:
        rspec = '{0}'.format(host)
      desc = 'rcmd [{0}]:'.format(rspec)
      command.append(rspec)
      for c in commands:
        tmp = c.replace('?HOST', host)
        command.append(tmp)
        desc += ' {0}'.format(tmp)
      mgmt_command = Command(host, command, self._attempts, desc)
      mgmt_commands.append(mgmt_command)

    # run all commands
    self._run_commands(mgmt_commands)
    return mgmt_commands

  def remote_push(self, local, remote):
    """Push specified documents to all remote hosts via SCP.

    Args:
      local     : A list of local file(s) and/or directory(ies)
                  '?HOST' is replaced with actual hostname.
      remote    : A string specification of the remote destination file(s).
                  '?HOST' is replaced with actual hostname.

    Returns:
      A list of Command objects.
    """

    # create a list of Commands for _run_commands()
    mgmt_commands = []
    for host in self._hosts:
      command = ['scp', '-r']
      command.extend(self._ssh_options())
      if self._user:
        rspec = '{0}@{1}'.format(self._user, host)
      else:
        rspec = '{0}'.format(host)
      desc = 'rpush [{0}]: '.format(rspec)
      for ll in local:
        tmp = ll.replace('?HOST', host)
        command.append(tmp)
        desc += '{0} '.format(tmp)
      desc += '=> '
      tmp = '{0}:{1}'.format(rspec, remote.replace('?HOST', host))
      command.append(tmp)
      desc += tmp
      mgmt_command = Command(host, command, self._attempts, desc)
      mgmt_commands.append(mgmt_command)

    # run all commands
    self._run_commands(mgmt_commands)
    return mgmt_commands

  def remote_pull(self, remote, local):
    """Push specified documents to all remote hosts via SCP.

    Args:
      remote    : A list of remote file(s) and/or directory(ies)
                  '?HOST' is replaced with actual hostname.
      local     : A string specification of the local destination file(s).
                  '?HOST' is replaced with actual hostname.

    Returns:
      A list of Command objects.
    """

    # create a list of Commands for _run_commands()
    mgmt_commands = []
    for host in self._hosts:
      command = ['scp', '-r']
      command.extend(self._ssh_options())
      if self._user:
        rspec = '{0}@{1}'.format(self._user, host)
      else:
        rspec = '{0}'.format(host)
      desc = 'rpull [{0}]: '.format(rspec)
      remote2 = ''
      for idx, rr in enumerate(remote):
        remote2 += rr.replace('?HOST', host)
        if idx < (len(remote) - 1):
          remote2 += ','
      if len(remote) > 1:
        remote2 = '{{{0}}}'.format(remote2)
      tmp = '{0}:{1}'.format(rspec, remote2)
      command.append(tmp)
      desc += tmp
      desc += ' => '
      tmp = local.replace('?HOST', host)
      command.append(tmp)
      desc += tmp
      mgmt_command = Command(host, command, self._attempts, desc)
      mgmt_commands.append(mgmt_command)

    # run all commands
    self._run_commands(mgmt_commands)
    return mgmt_commands

  def remote_script(self, scripts):
    """Run local scripts on remote hosts via SSH.

    Args:
      scripts  : a list of local scripts to be run on the remote hosts.
                 '?HOST' in script names is replaced with actual hostname.
                 '?HOST' in the script is replaced with actual hostname.

    Returns:
      A list of Command objects.
    """

    # create a list of Commands for _run_commands()
    mgmt_commands = []
    for host in self._hosts:
      command = ['ssh', '-T']
      command.extend(self._ssh_options())
      if self._user:
        rspec = '{0}@{1}'.format(self._user, host)
      else:
        rspec = '{0}'.format(host)
      desc = 'rscript [{0}]: '.format(rspec)
      command.append(rspec)

      # read in the text of the scripts
      script_names = []
      all_script = ''
      for script in scripts:
        script_name = script.replace('?HOST', host)
        script_names.append(script_name)
        with open(script_name, 'r') as fd:
          all_script += fd.read()
        if all_script[-1:] != '\n':
          all_script += '\n'
      if not all_script:
        all_script = ':'

      # format description and command
      desc += 'running {0}'.format(' '.join(script_names))
      mgmt_command = Command(host, command, self._attempts, desc,
                             all_script.replace('?HOST', host))
      mgmt_commands.append(mgmt_command)

    # run all commands
    self._run_commands(mgmt_commands)
    return mgmt_commands


class Command(threading.Thread):
    """A container class for commands given to Controller."""

    def __init__(self, host, commands, max_attempts, description=None,
                 stdin=None):
      """Constructor for Command."""
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
      if stdin:
        self.stdin = stdin.encode('utf-8')
      else:
        self.stdin = None
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
        self.stdout = out.decode('utf-8')
        self.stdout = self.stdout.rstrip('\n')
        self.stderr = err.decode('utf-8')
        self.stderr = self.stderr.rstrip('\n')
        self.process = None
        if self.retcode != 0:
          ssh_error = False
          for msg in SSH_ERROR_MSG:
            if self.stderr.startswith(msg):
              ssh_error = True
              break
          if ssh_error:
            continue
          else:
            break
        else:
          break

    def status(self, color=True):
      """This displays the result of the command.

      Args:
        color : whether or not to color the output
      """

      color = _should_color(color)
      text = []

      if color:
        text.append('{0}'.format(colored(self.description, 'blue')))
      else:
        text.append('{0}'.format(self.description))

      if self.stdout:
        if color:
          text.append('stdout:\n{0}'.format(colored(self.stdout, 'green')))
        else:
          text.append('stdout:\n{0}'.format(self.stdout))

      if self.stderr:
        if color:
          if self.retcode is not 0:
            text.append('stderr:\n{0}'.format(colored(self.stderr, 'red')))
          else:
            text.append('stderr:\n{0}'.format(colored(self.stderr, 'yellow')))
        else:
          text.append('stderr:\n{0}'.format(self.stderr))

      if self.retcode is not 0:
        if color:
          text.append('return code: {0}'.format(colored(self.retcode, 'red')))
          text.append('attempts:    {0}'.format(colored(self.attempts, 'red')))
        else:
          text.append('return code: {0}'.format(self.retcode))
          text.append('attempts:    {0}'.format(self.attempts))
      elif self.attempts is not 1:
        if color:
          text.append('attempts:    {0}'.format(colored(self.attempts,
                                                        'yellow')))
        else:
          text.append('attempts:    {0}'.format(self.attempts))

      return '\n'.join(text)
