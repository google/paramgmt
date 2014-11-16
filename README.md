# ParaMgmt - Parallel Management

## Disclaimer

This is not an official Google product. This project was created by
[Nic McDonald](https://www.github.com/nicmcd) at Google.

## Summary

ParaMgmt is a python package designed to ease the burden of interacting with
many remote machines via SSH. The primary focus is on parallelism, good error
handling, automatic connection retries, and nice viewable output. The abilities
of ParaMgmt include running local commands, running remote commands,
transferring files to and from remote machines, and executing local scripts on
remote machines. This package includes command-line executables that wrap the
functionality provided by the Python package.

## Installation

ParaMgmt is compatible with both Python2.7+ and Python3.x. I personally
recommend Python3, so the following installation example will be for that. If
you insist on using Python2, substitute `pip3` with `pip2` and `python3` with
`python2`. If you want ParaMgmt installed in both, install it in Python2 then in
Python3. The command-line executables will then use the latter. The installer
requires the `setuptools` package.

Both installations methods below will install a Python package called `paramgmt`
as well as 6 command-line executables: `rhosts`, `lcmd`, `rcmd`, `rpush`, `rpull`, and
`rscript`.

### Python package manager (PIP)
Install globally:
```bash
sudo pip3 install git+https://github.com/google/paramgmt.git
```
Install locally:
```bash
pip3 install --user git+https://github.com/google/paramgmt.git
```

### Source installation
Install globally:
```bash
sudo python3 setup.py install
```
Install locally:
```bash
python3 setup.py install --user
```

## Usage
TODO(nicmcd)
