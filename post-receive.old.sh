#!/bin/bash
targetRepo=$(git config --get hooks.deploy.path)
targetBranch=$(git config --get hooks.deploy.branch)
targetIsRemote=$(git config --get hooks.deploy.isremote)
sourceBranch=$(git config --get hooks.deploy.frombranch)
pushBranch=$(git config --get hooks.deploy.autopush.to)
autoPush=$(git config --get hooks.deploy.autopush.enable)
deploymentScript=$(git config --get hooks.deploy.script)

if [[ "$targetRepo" == "" ]]; then
        exit 0;
fi;
if [[ "$targetBranch" == "" ]]; then
        targetBranch="deploy"
fi;
if [[ "$sourceBranch" == "" ]]; then
        sourceBranch="deploy"
fi;
if [[ "$autoPush" == "" ]]; then
	autoPush=1
fi;
if [[ "$pushBranch" == "" ]]; then
	pushBranch="master"
fi;
while read oldrev newrev ref
do
        if [[ "$ref" == "refs/heads/$sourceBranch" ]]; then
		if [[ "$autoPush" == "1" ]]; then
			echo Auto pushing to "$pushBranch"
			git push . "$sourceBranch":"$pushBranch"
		fi;
		echo Automatically Deploying to branch "$targetBranch"
		echo
                git push -f "$targetRepo" "$sourceBranch":"$targetBranch"
		result1=$?
		if [[ "$targetIsRemote" != "1" ]]; then
			orig_dir=$(pwd)
			pushd "$targetRepo" 2>&1 > /dev/null
			umask 022
			GIT_DIR=.git git reset --hard "$targetBranch"
			result2=$?
			result3=0
			if (( result1==0 && result2==0 )); then
				if [[ "$deploymentScript" != "" ]]; then
					umask 022
					$deploymentScript
					result3=$?
				fi
			fi
			popd 2>&1 >/dev/null
		fi
		if (( result1==0 && result2==0 && result3==0 )); then
			echo OK: Auto deploy successful
		else
			echo FAIL: See previous message for details
		fi
                break;
        fi;
done
