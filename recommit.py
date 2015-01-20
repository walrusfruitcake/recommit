#!/bin/python3

import argparse
import os
import subprocess
from collections import namedtuple

#
# Argument-handling section
#

# TODO ditch logfile requirement, call hg|git log from this code
# ^don't forget to handle commit/changeset and summary/4spacetab format diff.s
# arguments:   hg-log-file    username-to-keep
parser = argparse.ArgumentParser(description='accepts required log info')
parser.add_argument('sourcedir', help='source repository-controlled directory')
parser.add_argument('targetdir', help='source repository-controlled directory')
parser.add_argument('--log', dest='logfilename', required=True, help='dump of hg log. assumed in reverse chron order')
parser.add_argument('--user', dest='username', required=True, help='username whose commits to keep')
parser.add_argument('--exclude', dest='excludeargs', nargs='*', required=False, help='list of files or dir.s to exclude from')

args = parser.parse_args()
#print(args.logfilename)

# convert args relative paths to absolute
sourceDir = os.path.abspath(args.sourcedir)
targetDir = os.path.abspath(args.targetdir)

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

    # git compatibility section
    if label == 'commit':
      label = 'changeset'
    if line[:4] == '    ':
      content = line
      label = 'summary'

    # a switch-case implementation replacement
    # date string .join is the way it is to cut off timezone offset
    evalLine = {
      'changeset': (content.split(':', maxsplit=1)[0]),
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


# unhandled exception possible (sudo)
def changeDate(dateStr):
  # if this fails/returns nonzero, will raise an exception
  subprocess.check_call(['sudo', 'date', '--set='+dateStr])

# original comdline examples
# rsync --archive /mnt/usb1/docs/multiarb indepproj/
# rsync -rlpgoD --exclude ".hg" ./ ../ha-bak17
def copyDir():
  baseArgs = ['rsync', '-rlptgoD', '--exclude', '".hg"']
  for excludeArg in args.excludeargs:
    if excludeArg is not None:
      baseArgs.extend(['--exclude', excludeArg])

  baseArgs.extend([sourceDir, targetDir])
  subprocess.check_call(baseArgs)

def rollBack(commitName):
  # make sure we're in the starting directory
  os.chdir(sourceDir)
  # revert: all, no backup-with-.orig-renaming, specifying which revision
  subprocess.check_call(['hg', 'revert', '-a', '-C', '-r', commitName])
  
# commit in the target directory
def reCommit(commitSummary):
  # make sure we're in the destination directory
  os.chdir(targetDir)
  subprocess.check_call(['git', 'add', '*'])
  subprocess.check_call(['git', 'commit', '-m', commitSummary])

#
# Main routine section
#

logfile = open(args.logfilename, 'r')
logData = getCommits(logfile)
 
# TODO abstract away init to a function
# git init in the target dir. first 'cd'
os.chdir(targetDir)
subprocess.check_call(['git', 'init'])

# checkout starting w initial commit state, copy to target dir, and commit that
logData.reverse()
for commit in logData:
  # where, recall logData is a list of dicts
  rollBack(commit['changeset'])
  changeDate(commit['date'])
  copyDir()
  reCommit(commit['summary'])

