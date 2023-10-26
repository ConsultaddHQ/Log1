#!/bin/sh

env_param=$1
echo "Environment: $env_param"

echo "Reading env conf file"
. deployment/env.conf

if [ "$env_param" = "prod" ]; then
  venv=$prod_venv
  host=$prod_host
  branch=$prod_branch

elif [ "$env_param" = "staging" ]; then
  venv=$staging_venv
  host=$staging_host
  branch=$staging_branch

else
  host=$dev_host
  venv=$dev_venv
  branch=$dev_branch
fi

echo "Connecting to remote server $host"
echo "$env_param $venv $branch"
echo "Connecting to remote server"

job_name=$JOB_NAME | cut -f1 -d "/"
git_url=$(cat '/var/lib/jenkins/jobs/'\"$job_name\"'/config.xml' | sed -ne '/remote/{s/.*<remote>\(.*\)<\/remote>.*/\1/p;q;}')

ssh -o StrictHostKeyChecking=no ubuntu@"$host" 'bash -s' < deployment/remote.sh "$env_param $venv $branch $git_url" && exit
