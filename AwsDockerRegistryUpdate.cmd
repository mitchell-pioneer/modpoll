aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 338449120570.dkr.ecr.us-east-1.amazonaws.com
docker build -t modpoll .
docker tag modpoll:latest 338449120570.dkr.ecr.us-east-1.amazonaws.com/fractal_ev_power_management:latest
docker push 338449120570.dkr.ecr.us-east-1.amazonaws.com/modpoll:latest
