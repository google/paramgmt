# ParaMgmt - Parallel Management

This project is a Python package with accompanying command-line
executable scripts for controlling many remote machines (servers, switches,
etc.) in parallel. It includes error control, automatic retries, and output
coloring. The package supports running local commands, remote commands,
local scripts on remote machines, pushing files, and pulling files. This package
can be used directly at the command line using the provided executables, or in a
Python script by importing the 'paramgmt' package.

This is not an official Google product. This was created by Nic McDonald
(https://github.com/nicmcd) while employed at Google for efficiently interacting
with large numbers of remote machines in a productive way.