#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@file
Gitolite Auto Deployment Script
@version 0.1
@author 赵迤晨 (Zhao Yichen) 
@copyright 赵迤晨 (Zhao Yichen) <interarticle@gmail.com>
@license MIT License
"""

import argparse
import subprocess
import os
import sys
import re
import shlex

cwdStack = []
globalEnviron = {}

def strbool(string):
	return string and (string.lower() == 'true' or string == '1')

def system(command, capture=False, env=None, cwd=None, runas=None):
	global cwdStack, globalEnviron
	shell=False

	if runas:
		if type(command) == str:
			command = ['bash', '-c', command]
		command = ['sudo', '-n', '-u', runas] + command

	if type(command) == str:
		shell=True
	sysenv = dict(os.environ)
	sysenv.update(globalEnviron)
	if env:
		sysenv.update(env)

	if len(cwdStack) > 0 and not cwd:
		cwd = cwdStack[len(cwdStack) - 1]


	if not capture:
		p = subprocess.Popen(command, shell=shell , env=sysenv, cwd=cwd)
		return p.wait()
	else:
		p = subprocess.Popen(command, shell=shell, stdout=subprocess.PIPE, env=sysenv, cwd=cwd)
		stdout, stderr = p.communicate()
		return (p.wait(), stdout)

def systemTest(command, **kwargs):
	return (system(command, capture=False, **kwargs) == 0)

def systemQuitOnError(command, **kwargs):
	if not systemTest(command, **kwargs):
		error('Failed')
		exit(1)

def getGitConfig(name, default=None):
	result, value = system(['git','config','--get', name], True)
	if result != 0:
		return default
	else:
		return value.strip()

def gitoliteCheckAccess(repo,user,perm,ref):
	return systemTest(['gitolite', 'access', '-q', repo, user, perm, ref])

def error(string):
	sys.stderr.write("AUTODEPLOY:E: " + string + "\n")

def info(string):
	sys.stderr.write("AUTODEPLOY: " + string + "\n")


def main():
	if not getGitConfig('hooks.autodeploy'):
		exit(0)
	parser = argparse.ArgumentParser(description="Gitolite Auto Deployment Script by Zhao Yichen")
	parser.add_argument('hook', nargs=1, choices=['pre-receive', 'post-receive'])
	parser.add_argument('--tee', dest='tee', default=False, action='store_true', help="Echo stdin back through stdout. Note, all messages are printed from stderr.")

	args = parser.parse_args()

	parser = argparse.ArgumentParser(description="Gitolite Auto Deployment Script by Zhao Yichen [Parsing Git Config Settings]")
	parser.add_argument('deployPath', nargs='+', metavar="PATH")
	parser.add_argument('--source-branch', '-s', dest="sourceBranch", default='master',help='The branch name that upon being pushed to will cause auto deploy')
	parser.add_argument('--push-branch'  , '-p', dest="pushBranch", default='deploy', help='The default branch in the remote repository to push to. Applies only when deploying under "push-reset" mode')
	parser.add_argument('--path-type',   '-pt', dest='pathType', default='automatic', choices=['automatic', 'local', 'remote'], help='The type of the PATH given. Automatic determines remote paths if they contain "@" or "://"; local otherwise. To force a mode, specify local or remote.')
	parser.add_argument('--behavior', '-b', dest='behavior', default='push-reset', choices=['push-reset', 'fetch-reset'], help='Method of deploying to a local repository. Push-reset first pushes the current repository to the deployment repository, then resets the active branch HEAD to the deploy branch. This requires access to the deployment directory by the git user. Fetch-reset instead requires impersonating as another user, switching to the repository in question, fetching from the remote repository, and resetting. This requires configuring two additional parameters: --run-as/-r, and --ssh-key/-k. If left unconfigured, any further push requests will be denied on pre-receive, and an error message will be shown.')
	parser.add_argument('--user', '-u', dest='runAs', default=None, help='The user to impersonate when deploying using fetch-reset. You must have sudo installed, and allow the git user to run git fetch, git reset, and any custom post-deploy command you may have as the target user without requiring a password. See sudoers.')
	parser.add_argument('--local-ssh-key', '-k', dest='sshKey', default=None, help='Path to the ssh key file owned by RUNAS user, with at least u+r, and o-r/g-r perms. This key should at least have R access to SOURCEBRANCH on the current repository.')
	parser.add_argument('--execute', '-e', dest='execute', default=None, help='Command to execute in the deployment directory after a successful deployment, using RUNAS if BEHAVIOR is fetch-reset, or the git user otherwise.')
	settings = parser.parse_args(shlex.split(getGitConfig('hooks.autodeploy', '')))
	glUser = os.environ['GL_USER']
	glRepo = os.environ['GL_REPO']

	if settings.behavior == 'fetch-reset' and (not settings.runAs or not settings.sshKey):
		error("You have not specified RUNAS or SSHKEY required for fetch-reset behavior.")
		exit(1)
	os.umask(022)

	raw = sys.stdin.read()

	changes = map(lambda row: tuple(row.strip().split(' ')), raw.strip().split('\n'))

	def processPostRecv():
		deployDetected = False
		for row in changes:
			if row[2] == ("refs/heads/%s" % (settings.sourceBranch, )):
				deployDetected = True
				break
		if not deployDetected:
			return

		info("Auto Deploy in Progress")

		for target in settings.deployPath:
			target = target.strip()
			pushBranch = settings.pushBranch
			if target.find(' ') > 0:
				target, pushBranch = target.split(' ')[:2] #In case they specified more than two params, and crashed the script
			info("TO %s %s:" % ("LOCAL" if isLocal(target) else 'REMOTE', target))
			if isLocal(target):
				if settings.behavior == "push-reset":
					info(" push %s %s:%s" % (target, settings.sourceBranch, pushBranch))
					systemQuitOnError(['git', 'push', '-f', target, "%s:%s" % (settings.sourceBranch, pushBranch)], env={'GIT_DIR': '.'})
					info(" reset %s" % (pushBranch, ))
					systemQuitOnError(['git', 'reset', '--hard', pushBranch], env={'GIT_DIR': '.git'}, cwd=target)
					info(' SUCCESS')
				else:
					info(" fetch git@localhost:%s.git" % (glRepo, ))
					systemQuitOnError(['ssh-agent', 'bash', '-c', "ssh-add '%s'; git fetch git@localhost:%s.git" % (settings.sshKey, glRepo)], env={'GIT_DIR': '.git'}, runas=settings.runAs, cwd=target)
					info(" reset FETCH_HEAD")
					systemQuitOnError(['git', 'reset', '--hard', 'FETCH_HEAD'], env={'GIT_DIR': '.git'}, runas=settings.runAs, cwd=target)
					info(' SUCCESS')
			else:
				info(" push %s %s:%s" % (target, settings.sourceBranch, pushBranch))
				systemQuitOnError(['git', 'push', '-f', target, "%s:%s" % (settings.sourceBranch, pushBranch)], env={'GIT_DIR': '.'})
				info(' SUCCESS')

			if isLocal(target) and settings.execute:
				info(' execute %s' % (settings.execute, ))
				if settings.behavior == 'push-reset':
					systemQuitOnError(settings.execute, cwd=target, env={'GIT_DIR': '.git'})
				else:
					systemQuitOnError(settings.execute, cwd=target, env={'GIT_DIR': '.git'}, runas=settings.runAs)

				info(' SUCCESS')
		info('Auto Deploy Successful')



	def isLocal(repo):
		if settings.pathType == 'local':
			return True
		elif settings.pathType == 'remote':
			return False
		else:
			# ">0" because they shouldn't be at the front
			if repo.find('://') > 0 or repo.find('@') > 0:
				return False
			else:
				return os.path.isdir(repo)

	if args.hook[0] == 'post-receive':
		processPostRecv()

	#End, if tee, echo input
	if args.tee:
		sys.stdout.write(raw)




if __name__ == '__main__':
	main()
