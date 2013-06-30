gitolite-autodeploy
===================

Python Gitolite Git Autodeployment Script

## Install ##

Copy `auto-deploy.py` and `post-receive.sh` to `/home/<git-user>/.gitolite/hooks/common/`. chmod to 755, then remane `post-receive.sh` to `post-receive`. Run `gitolite setup`.
