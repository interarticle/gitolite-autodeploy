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

cwdStack = []

def strbool(string):
	return string and (string.lower() == 'true' or string == '1')

def system(command, capture=False, env=None, cwd=None):
	shell=False
	if type(command) == str:
		shell=True
	sysenv = dict(os.environ)
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

def getGitConfig(name):
	result, value = system(['git','config','--get', name], True)
	if result != 0:
		return None
	else:
		return value.strip()

