#!/bin/python3

import argparse
import os
import subprocess
from collections import namedtuple

#
# Argument-handling section
#

# also TODO un-mandatory some flag opts
# TODO ditch logfile requirement, call hg|git log from this code
# ^don't forget to handle commit/changeset and summary/4spacetab format diff.s
# arguments:   hg-log-file    username-to-keep
parser = argparse.ArgumentParser(description='accepts required log info')
parser.add_argument('sourcedir', help='repository-controlled source directory')
parser.add_argument('targetdir', help='desired target directory')
parser.add_argument('--log', dest='logfilename', required=True, help='dump of hg log. assumed in reverse chron order')
parser.add_argument('--user', dest='username', required=True, help='username whose commits to keep')
parser.add_argument('--exclude', dest='excludeargs', nargs='*', metavar='X', required=False, help='list of files or dir.s to exclude from')
parser.add_argument('--type', dest='repotype', help='which version control system. "git" and "hg" are valid options. hg is the default')
# will set args.noinit True if flag set. False otherwise
parser.add_argument('--noinit', action='store_true')

args = parser.parse_args()
#print(args.logfilename)

# convert args relative paths to absolute
sourceDir = os.path.abspath(args.sourcedir)
targetDir = os.path.abspath(args.targetdir)

# check what VCS selected
validVCS = ('git', 'hg')

if args.repotype not in validVCS:
  #raise argparse.ArgumentError()
  parser.error("check argument provided for --type")
# else
repoType = args.repotype

#
# Function-definition section
#

# Nope to namedtuples, dict approach requires fewer throwaway variables
# return a log list of commit dicts in the form (commitName, user, date, descr)
#   lighter than dicts, immutable
def getCommits(logfile):
  logList = []
  #CommitTuple = namedtuple('CommitData', ['name','user','date'])
  commitDict = {}
  # actually go through the file
  for line in logfile:
    lineList = line.split(maxsplit=1)
    # an empty string is false, so skip this instance of forloop
    if not line.strip():
      continue

    label = lineList[0].split(':', maxsplit=1)[0]
    content = lineList[1]
    #label, content = (lambda i: lineList[i].split(':', maxsplit=1))(0,1)
    #print(label,content, sep='...',end='')

    # TODO just use different dicts for different repo formats
    # git compatibility section
    label = label.lower()
    if label == 'commit':
      label = 'changeset'
    if label == 'author':
      label = 'user'
    if line[:4] == '    ':
      content = line
      label = 'summary'

    # a switch-case implementation replacement
    # date string .join is the way it is to cut off timezone offset
    evalLine = {
      'changeset': (content.split(':', maxsplit=1)[0].strip()),
      'user': (content.strip()),
      'date': (' '.join(content.split()[:-1]) ),
      'summary': (content.strip())
    }.get(label)
    
    # e.g. if label=='changeset', this runs:  commitDict['commit'] = content.split
    if evalLine is not None:
      commitDict[label] = evalLine

#    def cdName():
#      commitStr = label.split(':',maxsplit=1)[0]
#    def 
#    commitStr = line.split
    
    # when we have all relevant line content from this commit
    if label == 'summary':
#      # add an unnamed instance of CommitData to the list
#      commitList.add(CommitTuple(commitStr, userStr, dateStr))
      # except we're adding to dict
      logList.append(commitDict)
      commitDict = {}
    #print(line, end='')

  return logList


# will init a git repo unless otherwise indicated when script called
def gitInit():
  if args.noinit:
    return
  # git init in the target dir. first 'cd'
  os.chdir(targetDir)
  subprocess.check_call(['git', 'init'])


# unhandled exception possible (sudo)
def changeDate(dateStr):
  # if this fails/returns nonzero, will raise an exception
  subprocess.check_call(['sudo', 'date', '--set='+dateStr])

# original comdline examples
# rsync --archive /mnt/usb1/docs/multiarb indepproj/
# rsync -rlpgoD --exclude ".hg" ./ ../ha-bak17
def copyDir():
  baseArgs = ['rsync', '-rlptgoD', '--exclude', '.hg', '--exclude', '.git']
  if args.excludeargs is not None:
    for excludeArg in args.excludeargs:
      baseArgs.extend(['--exclude', excludeArg])

  # NOTE the '/' appended to sourceDir wound up being important
  #   otherwise the directory itself was copied into target, increasing depth
  baseArgs.extend([sourceDir+'/', targetDir])
  subprocess.check_call(baseArgs)


def rollBack(commitName):
  setOriginArgs = {
    'git': (['git', 'checkout']),
    'hg': (['hg', 'revert', '-a', '-C', '-r'])
  }[repoType]

  repoArgs = setOriginArgs
  repoArgs.append(commitName)

  # make sure we're in the starting directory
  os.chdir(sourceDir)
  # revert: all, no backup-with-.orig-renaming, specifying which revision
  subprocess.check_call(repoArgs)
  

# commit in the target directory
def reCommit(commitSummary):
  # make sure we're in the destination directory
  os.chdir(targetDir)
  subprocess.check_call(['git', 'add', '*'])
  subprocess.call(['git', 'commit', '-m', commitSummary])


#
# Main routine section
#

logfile = open(args.logfilename, 'r')
logData = getCommits(logfile)
 
# abstracted away init to a function
gitInit()

# checkout starting w initial commit state, copy to target dir, and commit that
logData.reverse()
for commit in logData:
  # where, recall logData is a list of dicts
  rollBack(commit['changeset'])
  changeDate(commit['date'])
  copyDir()
  # TODO generalize to more checks
  if commit['user'] == args.username:
    reCommit(commit['summary'])

# reset time to normal
subprocess.check_call(['sudo', 'hwclock', '-s'])

