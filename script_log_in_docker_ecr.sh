USER=865897534779
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $USER.dkr.ecr.us-east-1.amazonaws.com