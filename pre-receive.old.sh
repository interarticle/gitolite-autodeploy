#!/bin/bash
targetRepo=$(git config --get hooks.deploy.path)
targetBranch=$(git config --get hooks.deploy.branch)
sourceBranch=$(git config --get hooks.deploy.frombranch)
pushBranch=$(git config --get hooks.deploy.autopush.to)
autoPush=$(git config --get hooks.deploy.autopush.enable)
autoPull=$(git config --get hooks.deploy.autopull.enable)
autoPullToBranch=$(git config --get hooks.deploy.autopull.to)

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
if [[ "$autoPull" != "1" ]]; then
	exit 0;
fi
if [[ "$autoPullToBranch" == "" ]]; then
	autoPullToBranch=$sourceBranch
fi
function hasUntracked() {
	if (local u=$(GIT_DIR=.git git ls-files --others --exclude-standard) && test -n "$u"); then
		return 0
	else
		return 1
	fi
}
function isDirty() {
	if ( ! GIT_DIR=.git git diff-index --quiet --cached HEAD || ! GIT_DIR=.git git diff-files --quiet || hasUntracked ); then
		return 0
	else
		return 1
	fi
}
pulled=0
while read oldrev newrev ref
do
        if [[ "$ref" == "refs/heads/$autoPullToBranch" ]]; then
		toPull=0
		currentRepo=`pwd`
		pushd "$targetRepo" 2>&1 > /dev/null
		if isDirty; then
			echo Detected Changes in Deployment Directory, Auto Committing
			umask 033
			GIT_DIR=.git git add .
			GIT_DIR=.git git commit -a -m "Auto committed by Git Script on $(date)"
			ec=$?
			if (( ec==0 )); then
				GIT_DIR=.git git push -f . HEAD:$targetBranch
				toPull=1
			else
				echo *** Auto Commit Error. Report Immediately ***
			fi

		fi
		if ! ( GIT_DIR=.git git rev-list "$targetBranch" | grep --quiet $(GIT_DIR=.git git rev-parse HEAD) ); then
			GIT_DIR=.git git push -f . HEAD:"$targetBranch"
		fi
		popd 2>&1 >/dev/null
		if (( toPull!=1 )); then
			git fetch --quiet "$targetRepo" +refs/heads/"$targetBranch"
			if ! ( git rev-list "$autoPullToBranch" | grep --quiet $(git rev-parse FETCH_HEAD) ); then
				toPull=1
			fi
		fi
		if (( toPull==1 )); then
			echo Auto Pulling
			git fetch "$targetRepo" +refs/heads/"$targetBranch":refs/heads/"$autoPullToBranch"
			if (( autoPush==1 )); then
				echo Auto Pushing to $pushBranch
				git push . $autoPullToBranch:$pushBranch
			fi
			echo Done
			pulled=1
		fi
        fi;
done
if (( pulled==1 )); then 
	echo Changes pulled, push request rejected. Please pull first.
	exit 1
else
	exit 0
fi
